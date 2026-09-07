#!/usr/bin/env python3
"""Run a DeepSearchQA dataset through Hermes and record every run under hermes-runs/.

One process per query, N in flight at a time. Each experiment writes a timestamped
directory holding everything shared by the run at the top level and one directory
per query underneath.

    hermes-runs/<timestamp>__<dataset>__<experiment>/
      run_config.json     model, base_url, toolsets, skills, arm, git commit, ...
      manifest.json       the exact task list, in order
      skills_snapshot.txt what `hermes skills list` reported at run time
      config.snapshot.yaml the config the agents ran with (secrets redacted)
      run.log             orchestrator log
      summary.json        aggregate metrics + per-task rows
      metrics.csv         one row per query, for spreadsheets/plots
      queries/<task_id>/  see run_query.py for the per-query layout

The three arms live in experiments.yaml. Examples:

    # baseline: pure Hermes, no skills at all
    ./dsqa_runner.py --dataset dsqa90 --experiment no-skill --concurrency 4

    # every query forced through the deep-research skill
    ./dsqa_runner.py --dataset dsqa90 --experiment forced-skill --concurrency 4

    # the agent decides whether to use the skill
    ./dsqa_runner.py --dataset dsqa90 --experiment auto-skill --concurrency 4

    # all three, back to back, into three separate run directories
    ./dsqa_runner.py --dataset dsqa90 --experiment all --concurrency 4

    # smoke test: 2 tasks, print the commands, run nothing
    ./dsqa_runner.py --dataset dsqa90 --experiment no-skill --limit 2 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import trace_utils  # noqa: E402

DEFAULT_DATASET_ROOT = Path("/home/ubuntu/smasurekar/datasets")
SECRET_KEY = re.compile(r"(key|token|secret|password|credential)", re.I)


# --------------------------------------------------------------------------- #
# logging
# --------------------------------------------------------------------------- #

class Log:
    """Line logger writing to stdout and run.log at once, safe across threads."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._handle = path.open("a", encoding="utf-8") if path else None

    def __call__(self, message: str) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')} {message}"
        with self._lock:
            print(line, flush=True)
            if self._handle:
                self._handle.write(line + "\n")
                self._handle.flush()

    def close(self) -> None:
        if self._handle:
            self._handle.close()


# --------------------------------------------------------------------------- #
# dataset
# --------------------------------------------------------------------------- #

def load_tasks(dataset_dir: Path) -> List[Dict[str, Any]]:
    """Read every ``deepsearchqa-*`` task directory, sorted by id.

    A task needs an ``instruction.md``; ``tests/metadata.json`` (expected answer,
    category) and ``task.toml`` (timeouts) are read when present.
    """
    tasks: List[Dict[str, Any]] = []
    for task_dir in sorted(p for p in dataset_dir.iterdir() if p.is_dir()):
        instruction_path = task_dir / "instruction.md"
        if not instruction_path.exists():
            continue
        instruction = instruction_path.read_text(encoding="utf-8").strip()
        if not instruction:
            continue

        metadata: Dict[str, Any] = {}
        metadata_path = task_dir / "tests" / "metadata.json"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}

        agent_timeout = None
        toml_path = task_dir / "task.toml"
        if toml_path.exists():
            try:
                import tomllib

                spec = tomllib.loads(toml_path.read_text(encoding="utf-8"))
                agent_timeout = (spec.get("agent") or {}).get("timeout_sec")
            except Exception:  # noqa: BLE001 - metadata only, never fatal
                pass

        tasks.append({
            "task_id": task_dir.name,
            "task_dir": str(task_dir),
            "instruction": instruction,
            "metadata": metadata,
            "dataset_agent_timeout_sec": agent_timeout,
        })
    return tasks


# --------------------------------------------------------------------------- #
# environment capture
# --------------------------------------------------------------------------- #

def redact(value: Any) -> Any:
    """Deep-copy a config tree with anything key-shaped replaced."""
    if isinstance(value, dict):
        return {k: ("<REDACTED>" if SECRET_KEY.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def _run(argv: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 60) -> str:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env={**os.environ, **(env or {})}, cwd=str(REPO))
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return f"<failed: {exc!r}>"


def capture_environment(run_dir: Path, hermes_bin: str, source_home: Path) -> Dict[str, Any]:
    """Snapshot everything needed to explain the run months from now."""
    info: Dict[str, Any] = {
        "hostname": os.uname().nodename,
        "python": sys.version.split()[0],
        "hermes_bin": hermes_bin,
        "hermes_version": _run([hermes_bin, "--version"]).strip()[:200],
        "source_hermes_home": str(source_home),
    }
    info["git"] = {
        "commit": _run(["git", "rev-parse", "HEAD"]).strip()[:40],
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()[:100],
        "dirty": bool(_run(["git", "status", "--porcelain"]).strip()),
    }

    config: Dict[str, Any] = {}
    config_path = source_home / "config.yaml"
    if config_path.exists():
        try:
            import yaml

            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            (run_dir / "config.snapshot.yaml").write_text(
                yaml.safe_dump(redact(config), sort_keys=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            info["config_snapshot_error"] = repr(exc)

    model_cfg = config.get("model") or {}
    info["model_config"] = {
        "provider": model_cfg.get("provider"),
        "default_model": model_cfg.get("default"),
        "base_url": model_cfg.get("base_url"),
        "api_mode": model_cfg.get("api_mode"),
    }
    info["web_backend"] = (config.get("web") or {}).get("backend")

    # Which skills the agent could see. The listing is the honest record of what
    # was available, independent of which arm chose to expose them.
    skills = _run([hermes_bin, "skills", "list"], env={"HERMES_HOME": str(source_home)}, timeout=120)
    (run_dir / "skills_snapshot.txt").write_text(skills, encoding="utf-8")
    info["skills_listed"] = len(re.findall(r"^│ \S", skills, re.M))

    # Presence only - never the values.
    info["env_keys_present"] = sorted(
        k for k in os.environ
        if SECRET_KEY.search(k) and os.environ.get(k, "").strip()
    )
    return info


# --------------------------------------------------------------------------- #
# experiment config
# --------------------------------------------------------------------------- #

def load_experiments(path: Path) -> Dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("experiments"):
        raise SystemExit(f"{path}: no `experiments:` block")
    return data


def resolve_experiment(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    experiments = config["experiments"]
    if name not in experiments:
        raise SystemExit(f"unknown experiment {name!r}; have: {', '.join(sorted(experiments))}")
    defaults = config.get("defaults") or {}
    arm = dict(experiments[name])
    base = list(defaults.get("base_toolsets") or [])
    extra = [t for t in (arm.get("toolsets") or []) if t not in base]
    return {
        "name": name,
        "description": (arm.get("description") or "").strip(),
        "toolsets": base + extra,
        "skills": list(arm.get("skills") or []),
        "prompt_prefix": arm.get("prompt_prefix") or "",
        "max_turns": arm.get("max_turns", defaults.get("max_turns")),
        "run_budget_seconds": arm.get("run_budget_seconds", defaults.get("run_budget_seconds")),
    }


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #

def _mean(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 3) if values else None


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    value = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return round(value, 3)


def summarize(run_dir: Path, run_config: Dict[str, Any], log: Log) -> Dict[str, Any]:
    """Roll every result.json into summary.json and metrics.csv."""
    rows: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    queries_dir = run_dir / "queries"

    for result_path in sorted(queries_dir.glob("*/result.json")):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log(f"WARN unreadable {result_path}")
            continue
        results.append(result)
        metrics = result.get("metrics") or {}
        row = {
            "task_id": result.get("task_id"),
            "experiment": result.get("experiment"),
            "status": result.get("status"),
            "exit_code": result.get("exit_code"),
            "category": result.get("category"),
            "answer_type": result.get("answer_type"),
            "expected_answer": result.get("expected_answer"),
            "answer_chars": result.get("answer_chars"),
        }
        for column in trace_utils.CSV_COLUMNS:
            if column not in row:
                row[column] = metrics.get(column)
        rows.append(row)

    with (run_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=trace_utils.CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    ok = [r for r in results if r.get("status") == "ok"]

    def series(field: str) -> List[float]:
        out = []
        for result in ok:
            value = (result.get("metrics") or {}).get(field)
            if isinstance(value, (int, float)):
                out.append(float(value))
        return out

    headline = {}
    for field in ("latency_total_seconds", "token_usage_input", "token_usage_output",
                  "llm_calls", "subagents_invoked", "tool_calls_total"):
        values = series(field)
        headline[field] = {
            "total": round(sum(values), 3) if values else 0,
            "mean": _mean(values),
            "median": _median(values),
            "min": round(min(values), 3) if values else None,
            "max": round(max(values), 3) if values else None,
            "n": len(values),
        }

    status_counts: Dict[str, int] = {}
    tool_totals: Dict[str, int] = {}
    for result in results:
        status_counts[result.get("status") or "unknown"] = status_counts.get(result.get("status") or "unknown", 0) + 1
        for name, count in ((result.get("metrics") or {}).get("tool_call_counts") or {}).items():
            tool_totals[name] = tool_totals.get(name, 0) + int(count)

    summary = {
        "run_id": run_config.get("run_id"),
        "experiment": run_config.get("experiment", {}).get("name"),
        "dataset": run_config.get("dataset"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "queries_total": len(results),
        "queries_ok": len(ok),
        "status_counts": status_counts,
        "headline_metrics": headline,
        "tool_call_totals": dict(sorted(tool_totals.items(), key=lambda kv: (-kv[1], kv[0]))),
        "estimated_cost_usd_total": round(sum(
            float((r.get("metrics") or {}).get("estimated_cost_usd") or 0) for r in results), 6),
        "wall_clock_seconds": run_config.get("wall_clock_seconds"),
        "rows": rows,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return summary


# --------------------------------------------------------------------------- #
# execution
# --------------------------------------------------------------------------- #

def already_done(query_dir: Path) -> bool:
    """True when a completed result.json is already on disk (for --resume)."""
    result_path = query_dir / "result.json"
    if not result_path.exists():
        return False
    try:
        return json.loads(result_path.read_text(encoding="utf-8")).get("status") == "ok"
    except json.JSONDecodeError:
        return False


def run_experiment(args: argparse.Namespace, experiment: Dict[str, Any],
                   tasks: List[Dict[str, Any]], dataset_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}__{dataset_dir.name}__{experiment['name']}"
    run_dir = Path(args.out).expanduser().resolve() / run_id
    if args.resume_dir:
        run_dir = Path(args.resume_dir).expanduser().resolve()
        run_id = run_dir.name
    (run_dir / "queries").mkdir(parents=True, exist_ok=True)

    log = Log(run_dir / "run.log")
    source_home = Path(args.hermes_home).expanduser()
    log(f"run {run_id}")
    log(f"experiment: {experiment['name']} — {experiment['description']}")
    log(f"toolsets={','.join(experiment['toolsets'])} skills={','.join(experiment['skills']) or '-'} "
        f"prefix={experiment['prompt_prefix']!r}")
    log(f"{len(tasks)} tasks, concurrency {args.concurrency}")

    env_info = capture_environment(run_dir, args.hermes_bin, source_home)
    model = args.model or (env_info.get("model_config") or {}).get("default_model")

    run_config: Dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(dataset_dir),
        "dataset_name": dataset_dir.name,
        "experiment": experiment,
        "concurrency": args.concurrency,
        "model": model,
        "provider": args.provider,
        "reasoning": args.reasoning,
        "timeout_seconds": args.timeout,
        "link_user_skills": not args.no_user_skills,
        "prune_home": args.prune_home,
        "redact_traces": not args.no_redact,
        "task_count": len(tasks),
        "environment": env_info,
        "argv": sys.argv,
    }
    (run_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps([
        {"task_id": t["task_id"], "task_dir": t["task_dir"],
         "category": (t["metadata"] or {}).get("problem_category"),
         "instruction": t["instruction"]}
        for t in tasks], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    specs: List[Dict[str, Any]] = []
    for task in tasks:
        query_dir = run_dir / "queries" / task["task_id"]
        if args.resume and already_done(query_dir):
            log(f"skip {task['task_id']} (already ok)")
            continue
        query_dir.mkdir(parents=True, exist_ok=True)
        spec = {
            "run_id": run_id,
            "task_id": task["task_id"],
            "experiment": experiment["name"],
            "instruction": task["instruction"],
            "task_metadata": task["metadata"],
            "query_dir": str(query_dir),
            "source_hermes_home": str(source_home),
            "hermes_bin": args.hermes_bin,
            "toolsets": experiment["toolsets"],
            "skills": experiment["skills"],
            "prompt_prefix": experiment["prompt_prefix"],
            "model": model,
            "provider": args.provider,
            "base_url": (env_info.get("model_config") or {}).get("base_url"),
            "reasoning": args.reasoning,
            "max_turns": experiment["max_turns"],
            "run_budget_seconds": experiment["run_budget_seconds"],
            "timeout": args.timeout,
            "link_user_skills": not args.no_user_skills,
            "prune_home": args.prune_home,
            "redact_traces": not args.no_redact,
        }
        spec_path = query_dir / "spec.json"
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        specs.append({"spec_path": spec_path, "task_id": task["task_id"]})

    if args.dry_run:
        log("--dry-run: showing the first command, running nothing")
        if specs:
            import run_query

            sample = json.loads(specs[0]["spec_path"].read_text(encoding="utf-8"))
            prompt = sample["prompt_prefix"] + sample["instruction"]
            argv = run_query.build_argv(sample, prompt, Path(sample["query_dir"]) / "usage.json")
            log("  " + " ".join(repr(a) if " " in a else a for a in argv))
        log(f"{len(specs)} queries prepared under {run_dir}")
        log.close()
        return run_dir

    started = time.time()
    done = 0
    worker = [args.python, str(HERE / "run_query.py")]

    def execute(entry: Dict[str, Any]) -> Dict[str, Any]:
        # Separate process per query, exactly as the CLI would be run by hand.
        proc = subprocess.run(
            worker + [str(entry["spec_path"])],
            capture_output=True, text=True,
            # The worker enforces its own per-query timeout; this outer margin only
            # catches a wedged worker (never the agent itself).
            timeout=args.timeout + 900,
        )
        return {"task_id": entry["task_id"], "returncode": proc.returncode,
                "stderr": (proc.stderr or "")[-2000:]}

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(execute, entry): entry for entry in specs}
        for future in as_completed(futures):
            entry = futures[future]
            done += 1
            try:
                outcome = future.result()
            except Exception as exc:  # noqa: BLE001
                log(f"[{done}/{len(specs)}] {entry['task_id']} WORKER FAILED: {exc!r}")
                continue
            status = "ok"
            result_path = Path(json.loads(entry["spec_path"].read_text(encoding="utf-8"))["query_dir"]) / "result.json"
            if result_path.exists():
                try:
                    status = json.loads(result_path.read_text(encoding="utf-8")).get("status", "?")
                except json.JSONDecodeError:
                    status = "unreadable"
            else:
                status = f"no result.json (rc={outcome['returncode']})"
            log(f"[{done}/{len(specs)}] {entry['task_id']}: {status}")
            if outcome["returncode"] != 0 and outcome["stderr"]:
                log(f"    worker stderr tail: {outcome['stderr'].strip().splitlines()[-1][:300]}")

    run_config["wall_clock_seconds"] = round(time.time() - started, 3)
    run_config["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (run_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    summary = summarize(run_dir, run_config, log)
    log(f"done in {run_config['wall_clock_seconds']:.0f}s — "
        f"{summary['queries_ok']}/{summary['queries_total']} ok")
    for field, stats in summary["headline_metrics"].items():
        log(f"  {field:<24} total={stats['total']:<12} mean={stats['mean']}")
    log(f"artifacts: {run_dir}")
    log.close()
    return run_dir


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default="dsqa90",
                        help="Dataset name under the dataset root, or an absolute path (default: dsqa90)")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET_ROOT),
                        help=f"Where named datasets live (default: {DEFAULT_DATASET_ROOT})")
    parser.add_argument("--experiment", "-e", default="no-skill",
                        help="Experiment name from experiments.yaml, or 'all' for every arm in order")
    parser.add_argument("--experiments-file", default=str(HERE / "experiments.yaml"))
    parser.add_argument("--concurrency", "-j", type=int, default=4,
                        help="Queries in flight at once, each its own process (default: 4)")
    parser.add_argument("--limit", type=int, default=None, help="Only the first N tasks")
    parser.add_argument("--tasks", default=None,
                        help="Comma-separated task ids to run instead of the whole dataset")
    parser.add_argument("--out", default=str(HERE), help="Where run directories go (default: hermes-runs/)")
    parser.add_argument("--model", "-m", default=None, help="Model override (default: config.yaml model.default)")
    parser.add_argument("--provider", default=None, help="Provider override (requires --model)")
    parser.add_argument("--reasoning", default=None, help="Reasoning effort override")
    parser.add_argument("--timeout", type=float, default=1800,
                        help="Hard per-query wall-clock timeout in seconds (default: 1800)")
    parser.add_argument("--hermes-bin", default=str(Path.home() / ".hermes/venvs/hermes-dev/bin/hermes"),
                        help="hermes executable to run")
    parser.add_argument("--python", default=sys.executable, help="Interpreter used for the per-query worker")
    parser.add_argument("--hermes-home", default=str(Path.home() / ".hermes"),
                        help="Home the isolated per-query homes are seeded from")
    parser.add_argument("--no-user-skills", action="store_true",
                        help="Do not link ~/.hermes/skills into the isolated homes (builtin skills only)")
    parser.add_argument("--prune-home", action="store_true",
                        help="Delete each query's isolated home after its trace is exported (saves disk)")
    parser.add_argument("--no-redact", action="store_true",
                        help="Skip secret redaction on exported traces (not recommended: runs live in a git repo)")
    parser.add_argument("--resume", action="store_true",
                        help="With --resume-dir: skip queries that already have a successful result.json")
    parser.add_argument("--resume-dir", default=None, help="Reuse an existing run directory instead of a new one")
    parser.add_argument("--dry-run", action="store_true", help="Prepare specs and print a command; run nothing")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    dataset_dir = Path(args.dataset)
    if not dataset_dir.is_absolute():
        dataset_dir = Path(args.dataset_root) / args.dataset
    dataset_dir = dataset_dir.expanduser().resolve()
    if not dataset_dir.is_dir():
        raise SystemExit(f"dataset not found: {dataset_dir}")

    if not Path(args.hermes_bin).exists() and not shutil.which(args.hermes_bin):
        raise SystemExit(f"hermes executable not found: {args.hermes_bin}")

    tasks = load_tasks(dataset_dir)
    if not tasks:
        raise SystemExit(f"no tasks with instruction.md under {dataset_dir}")
    if args.tasks:
        wanted = {t.strip() for t in args.tasks.split(",") if t.strip()}
        tasks = [t for t in tasks if t["task_id"] in wanted]
        missing = wanted - {t["task_id"] for t in tasks}
        if missing:
            raise SystemExit(f"unknown task ids: {', '.join(sorted(missing))}")
    if args.limit:
        tasks = tasks[: args.limit]

    config = load_experiments(Path(args.experiments_file))
    names = list(config["experiments"]) if args.experiment == "all" else [args.experiment]
    if args.resume_dir and len(names) > 1:
        raise SystemExit("--resume-dir works with a single --experiment")

    for name in names:
        experiment = resolve_experiment(config, name)
        run_dir = run_experiment(args, experiment, tasks, dataset_dir)
        print(f"\n==> {name}: {run_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
