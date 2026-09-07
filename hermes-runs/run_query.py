#!/usr/bin/env python3
"""Run ONE dataset query as its own Hermes process and record everything about it.

Invoked by dsqa_runner.py as ``python run_query.py <spec.json>``; runnable by hand
against a spec file to reproduce or debug a single item.

Isolation
---------
Each query gets a private ``HERMES_HOME`` seeded from the real one (config.yaml
copied and patched, .env and skills symlinked). That buys three things at once:
its own ``state.db`` so N concurrent queries never contend on SQLite, a session
export containing this query's root session and its sub-agents and nothing else,
and no memory or session bleed from one eval item into the next.

The secret file is SYMLINKED, never copied - no run directory ever holds a
plaintext key.

Layout produced under the query directory
-----------------------------------------
  prompt.txt            exact text sent to the agent (with the arm's prefix)
  answer.md             the agent's final answer
  result.json           consolidated record: answer, metrics, config, artifacts
  metrics.json          metrics only (as embedded in result.json)
  usage.json            raw `hermes --usage-file` provider usage report
  task.json             dataset metadata (expected answer, category, ...)
  cmd.json              argv, env overrides and timings for the hermes process
  stdout.txt/stderr.txt raw process output
  trace/sessions.jsonl  full session export (root + every sub-agent)
  trace/events.jsonl    flattened per-message trace: reasoning, tool args, results
  trace/trace.jsonl     Claude Code trace format (HF Agent Trace Viewer)
  agent_cwd/            working directory the agent ran in (files it created)
  research_artifacts/   files the agent wrote under ~/.hermes/research (e.g. plan.md)
  hermes_home/          the isolated home, incl. logs/ and state.db (unless pruned)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import trace_utils  # noqa: E402

# Config overrides written into every isolated home. Auto-title and the skill
# curator both make their own LLM calls in the background; left on they would
# inflate the LLM-call and token counts with work the query never asked for.
_CONFIG_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "auxiliary": {"title_generation": {"enabled": False}},
    "curator": {"enabled": False},
}


def _log(message: str) -> None:
    print(f"[run_query] {message}", file=sys.stderr, flush=True)


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def seed_hermes_home(home: Path, source_home: Path, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build the isolated home. Returns a record of what was seeded."""
    home.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"path": str(home), "source": str(source_home)}

    src_config = source_home / "config.yaml"
    dst_config = home / "config.yaml"
    if src_config.exists():
        shutil.copy2(src_config, dst_config)
        record["config"] = "copied"
    else:
        record["config"] = "missing"

    # Patch the copy: run budget, turn cap, and the background-LLM shutoffs.
    overrides = dict(_CONFIG_OVERRIDES)
    agent_overrides: Dict[str, Any] = {}
    if spec.get("max_turns"):
        agent_overrides["max_turns"] = int(spec["max_turns"])
    if spec.get("run_budget_seconds"):
        agent_overrides["run_budget_seconds"] = float(spec["run_budget_seconds"])
    if agent_overrides:
        overrides = {**overrides, "agent": agent_overrides}

    if dst_config.exists():
        try:
            import yaml

            config = yaml.safe_load(dst_config.read_text(encoding="utf-8")) or {}
            if not isinstance(config, dict):
                config = {}
            _deep_merge(config, overrides)
            dst_config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
            record["config_overrides"] = overrides
        except Exception as exc:  # noqa: BLE001 - a patch failure must not kill the run
            record["config_patch_error"] = repr(exc)
            _log(f"config patch failed ({exc!r}); running with the unpatched copy")

    # Secrets: link, never copy. Also keeps `hermes` reading the live credentials.
    src_env = source_home / ".env"
    if src_env.exists():
        try:
            (home / ".env").symlink_to(src_env)
            record["env"] = "symlinked"
        except OSError as exc:
            record["env"] = f"symlink failed: {exc}"

    if spec.get("link_user_skills", True):
        src_skills = source_home / "skills"
        if src_skills.exists():
            try:
                (home / "skills").symlink_to(src_skills, target_is_directory=True)
                record["skills"] = "symlinked"
            except OSError as exc:
                record["skills"] = f"symlink failed: {exc}"
    else:
        record["skills"] = "not linked (builtin skills only)"

    # Provider/model catalogues, so N processes don't each re-fetch them.
    for cache in ("models_dev_cache.json", "provider_models_cache.json", "ollama_cloud_models_cache.json"):
        src_cache = source_home / cache
        if src_cache.exists():
            try:
                shutil.copy2(src_cache, home / cache)
            except OSError:
                pass
    return record


def build_argv(spec: Dict[str, Any], prompt: str, usage_path: Path) -> List[str]:
    argv = [spec["hermes_bin"], "-z", prompt, "--usage-file", str(usage_path)]
    toolsets = spec.get("toolsets") or []
    if toolsets:
        argv += ["-t", ",".join(toolsets)]
    skills = spec.get("skills") or []
    if skills:
        argv += ["-s", ",".join(skills)]
    if spec.get("model"):
        argv += ["-m", spec["model"]]
    if spec.get("provider"):
        argv += ["--provider", spec["provider"]]
    if spec.get("reasoning"):
        argv += ["--reasoning", spec["reasoning"]]
    return argv


def export_sessions(spec: Dict[str, Any], home: Path, trace_dir: Path) -> Dict[str, Any]:
    """Export every session in the isolated home, in raw and trace-viewer form."""
    trace_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "HERMES_HOME": str(home)}
    results: Dict[str, Any] = {}
    for fmt, filename in (("jsonl", "sessions.jsonl"), ("trace", "trace.jsonl")):
        target = trace_dir / filename
        argv = [spec["hermes_bin"], "sessions", "export", str(target), "--format", fmt]
        if spec.get("redact_traces", True):
            argv.append("--redact")
        try:
            proc = subprocess.run(
                argv, env=env, capture_output=True, text=True,
                timeout=spec.get("export_timeout", 300), cwd=str(trace_dir),
            )
            results[fmt] = {
                "exit_code": proc.returncode,
                "bytes": target.stat().st_size if target.exists() else 0,
            }
            if proc.returncode != 0:
                results[fmt]["stderr"] = (proc.stderr or "")[-2000:]
        except (subprocess.TimeoutExpired, OSError) as exc:
            results[fmt] = {"error": repr(exc)}
    return results


def collect_research_artifacts(query_dir: Path, source_home: Path, task_id: str,
                               started: float) -> Dict[str, Any]:
    """Recover working files the agent wrote outside the run directory.

    The deep-research skill points its plan at ``~/.hermes/research/...``, and ``~``
    expands to the real HOME regardless of HERMES_HOME - so the plan lands in the
    user's live Hermes home instead of this query's directory, and would otherwise
    be lost from the run record. Anything under that tree touched during this
    query's window and carrying this task's id is copied back in.

    Best-effort and non-destructive: the originals are left alone, and a failure
    here never affects the run's status.
    """
    record: Dict[str, Any] = {"copied": [], "source_root": str(source_home / "research")}
    research_root = source_home / "research"
    if not research_root.is_dir():
        return record
    destination = query_dir / "research_artifacts"
    try:
        for path in research_root.rglob("*"):
            if not path.is_file():
                continue
            if task_id not in str(path):
                continue
            try:
                if path.stat().st_mtime < started - 5:
                    continue
            except OSError:
                continue
            relative = path.relative_to(research_root)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            record["copied"].append(str(relative))
    except Exception as exc:  # noqa: BLE001
        record["error"] = repr(exc)
        _log(f"research artifact capture failed: {exc!r}")
    return record


def run(spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    query_dir = Path(spec["query_dir"])
    query_dir.mkdir(parents=True, exist_ok=True)

    source_home = Path(spec["source_hermes_home"]).expanduser()
    home = query_dir / "hermes_home"
    agent_cwd = query_dir / "agent_cwd"
    agent_cwd.mkdir(parents=True, exist_ok=True)
    trace_dir = query_dir / "trace"
    usage_path = query_dir / "usage.json"

    prompt = (spec.get("prompt_prefix") or "") + spec["instruction"]
    (query_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (query_dir / "task.json").write_text(
        json.dumps(spec.get("task_metadata") or {}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    seed_record = seed_hermes_home(home, source_home, spec)
    argv = build_argv(spec, prompt, usage_path)

    env = {**os.environ, "HERMES_HOME": str(home)}
    # Non-interactive by construction: no TTY, no approval prompts, no pager.
    env.update({"HERMES_YOLO_MODE": "1", "HERMES_ACCEPT_HOOKS": "1", "TERM": "dumb", "NO_COLOR": "1"})
    for key, value in (spec.get("env") or {}).items():
        env[str(key)] = str(value)

    timeout = float(spec.get("timeout", 1800))
    started = time.time()
    status = "ok"
    error: Optional[str] = None
    exit_code: Optional[int] = None
    stdout = stderr = ""

    try:
        proc = subprocess.run(
            argv, cwd=str(agent_cwd), env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        exit_code, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
        if exit_code != 0:
            status = "failed"
            error = f"hermes exited {exit_code}"
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        error = f"exceeded {timeout}s"
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except OSError as exc:
        status = "error"
        error = repr(exc)

    latency = time.time() - started

    (query_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (query_dir / "stderr.txt").write_text(stderr, encoding="utf-8")

    usage: Dict[str, Any] = {}
    if usage_path.exists():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # The export runs even on timeout/failure: a partial trace is the most
    # useful artifact there is when a query goes wrong.
    research_record = collect_research_artifacts(query_dir, source_home, spec["task_id"], started)
    export_record = export_sessions(spec, home, trace_dir)
    sessions = trace_utils.load_sessions(trace_dir / "sessions.jsonl")
    root_id = usage.get("session_id")

    try:
        events = trace_utils.flatten_events(sessions, root_id)
        trace_utils.write_events(events, trace_dir / "events.jsonl")
    except Exception as exc:  # noqa: BLE001
        events = []
        _log(f"event flattening failed: {exc!r}")

    # `-z` prints only the final response, so stdout IS the answer. The trace is
    # the fallback for a run that produced an answer but died before printing it.
    answer = stdout.strip() or trace_utils.final_answer(sessions, root_id)
    (query_dir / "answer.md").write_text(answer + "\n" if answer else "", encoding="utf-8")

    try:
        metrics = trace_utils.compute_metrics(
            sessions, usage=usage, latency_seconds=latency, root_id=root_id
        )
    except Exception as exc:  # noqa: BLE001
        metrics = {"error": repr(exc), "latency_total_seconds": round(latency, 3)}
        _log(f"metric computation failed: {exc!r}")

    if status == "ok" and not answer:
        status = "empty_answer"
        error = error or "hermes exited 0 but produced no answer text"

    task_meta = spec.get("task_metadata") or {}
    result = {
        "task_id": spec["task_id"],
        "experiment": spec.get("experiment"),
        "run_id": spec.get("run_id"),
        "status": status,
        "error": error,
        "exit_code": exit_code,
        "started_at": started,
        "finished_at": started + latency,
        "latency_total_seconds": round(latency, 3),
        "prompt": prompt,
        "prompt_prefix": spec.get("prompt_prefix") or "",
        "instruction": spec["instruction"],
        "answer": answer,
        "answer_chars": len(answer),
        "expected_answer": task_meta.get("answer"),
        "answer_type": task_meta.get("answer_type"),
        "category": task_meta.get("problem_category") or task_meta.get("category"),
        "metrics": metrics,
        "config": {
            "model": spec.get("model"),
            "provider": spec.get("provider"),
            "base_url": spec.get("base_url"),
            "reasoning": spec.get("reasoning"),
            "toolsets": spec.get("toolsets"),
            "skills_preloaded": spec.get("skills"),
            "skills_toolset_enabled": "skills" in (spec.get("toolsets") or []),
            "max_turns": spec.get("max_turns"),
            "run_budget_seconds": spec.get("run_budget_seconds"),
            "timeout": timeout,
            "argv": argv,
            "hermes_home": seed_record,
        },
        "artifacts": {
            "answer": "answer.md",
            "prompt": "prompt.txt",
            "task_metadata": "task.json",
            "usage": "usage.json",
            "metrics": "metrics.json",
            "stdout": "stdout.txt",
            "stderr": "stderr.txt",
            "sessions_export": "trace/sessions.jsonl",
            "flattened_events": "trace/events.jsonl",
            "claude_code_trace": "trace/trace.jsonl",
            "agent_cwd": "agent_cwd/",
            "hermes_home": "hermes_home/",
            "research_artifacts": "research_artifacts/",
        },
        "export": export_record,
        "research_artifacts": research_record,
        "event_count": len(events),
        "agent_cwd_files": sorted(
            str(p.relative_to(agent_cwd)) for p in agent_cwd.rglob("*") if p.is_file()
        )[:500],
    }

    (query_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    (query_dir / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    if spec.get("prune_home"):
        # state.db and logs are the only parts worth keeping once the trace is out.
        shutil.rmtree(home, ignore_errors=True)

    _log(f"{spec['task_id']}: {status} in {latency:.1f}s")
    return 0 if status == "ok" else 1


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <spec.json>", file=sys.stderr)
        return 2
    try:
        return run(Path(sys.argv[1]))
    except Exception as exc:  # noqa: BLE001 - a worker crash must not be silent
        import traceback

        traceback.print_exc()
        print(f"[run_query] fatal: {exc!r}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
