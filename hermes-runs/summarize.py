#!/usr/bin/env python3
"""Rebuild metrics for finished runs, and compare arms side by side.

Two jobs, neither of which re-runs the agent:

* ``--rebuild`` re-derives metrics.json / result.json["metrics"] from each query's
  stored trace, then rewrites summary.json and metrics.csv. Use it after changing
  trace_utils.py, or to recover a run whose metrics failed to compute at the time.
* the default mode prints one table row per run directory, which is how the three
  arms get compared.

    ./summarize.py hermes-runs/20260907-*__dsqa90__*
    ./summarize.py --rebuild hermes-runs/20260907-163000__dsqa90__no-skill
    ./summarize.py --csv comparison.csv hermes-runs/*__dsqa90__*
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import trace_utils  # noqa: E402

HEADLINE = ["latency_total_seconds", "token_usage_input", "token_usage_output",
            "llm_calls", "subagents_invoked", "tool_calls_total"]


def rebuild_run(run_dir: Path) -> int:
    """Recompute every query's metrics from its stored trace. Returns the count."""
    rebuilt = 0
    for result_path in sorted((run_dir / "queries").glob("*/result.json")):
        query_dir = result_path.parent
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  skip {query_dir.name}: unreadable result.json")
            continue

        usage: Dict[str, Any] = {}
        usage_path = query_dir / "usage.json"
        if usage_path.exists():
            try:
                usage = json.loads(usage_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        sessions = trace_utils.load_sessions(query_dir / "trace" / "sessions.jsonl")
        if not sessions:
            print(f"  skip {query_dir.name}: no session export")
            continue

        root_id = usage.get("session_id")
        metrics = trace_utils.compute_metrics(
            sessions, usage=usage,
            latency_seconds=result.get("latency_total_seconds"), root_id=root_id)
        trace_utils.write_events(
            trace_utils.flatten_events(sessions, root_id), query_dir / "trace" / "events.jsonl")

        result["metrics"] = metrics
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        (query_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        rebuilt += 1
    return rebuilt


def rewrite_summary(run_dir: Path) -> Dict[str, Any]:
    """Regenerate summary.json + metrics.csv using the runner's own aggregator."""
    import dsqa_runner

    config_path = run_dir / "run_config.json"
    run_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    log = dsqa_runner.Log(None)
    return dsqa_runner.summarize(run_dir, run_config, log)


def load_summary(run_dir: Path) -> Optional[Dict[str, Any]]:
    path = run_dir / "summary.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def comparison_rows(run_dirs: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for run_dir in run_dirs:
        summary = load_summary(run_dir)
        if summary is None:
            print(f"  (no summary.json in {run_dir.name} — run with --rebuild)", file=sys.stderr)
            continue
        row: Dict[str, Any] = {
            "run": run_dir.name,
            "experiment": summary.get("experiment"),
            "queries": summary.get("queries_total"),
            "ok": summary.get("queries_ok"),
            "wall_clock_s": summary.get("wall_clock_seconds"),
            "cost_usd": summary.get("estimated_cost_usd_total"),
        }
        for field in HEADLINE:
            stats = (summary.get("headline_metrics") or {}).get(field) or {}
            row[f"{field}__mean"] = stats.get("mean")
            row[f"{field}__total"] = stats.get("total")
        rows.append(row)
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("no runs to compare")
        return
    short = {
        "latency_total_seconds": "latency_s",
        "token_usage_input": "tok_in",
        "token_usage_output": "tok_out",
        "llm_calls": "llm_calls",
        "subagents_invoked": "subagents",
        "tool_calls_total": "tool_calls",
    }
    headers = ["experiment", "ok/n", "wall_s", "cost_usd"] + [f"{s}/q" for s in short.values()]
    table = [headers]
    for row in rows:
        table.append([
            str(row.get("experiment")),
            f"{row.get('ok')}/{row.get('queries')}",
            f"{row.get('wall_clock_s') or 0:.0f}",
            f"{row.get('cost_usd') or 0:.4f}",
        ] + [_fmt(row.get(f"{field}__mean")) for field in short])

    widths = [max(len(str(r[i])) for r in table) for i in range(len(headers))]
    for index, row in enumerate(table):
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
        if index == 0:
            print("  ".join("-" * w for w in widths))


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.1f}" if value < 1000 else f"{value:.0f}"
    return str(value)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="+", type=Path, help="Run directories under hermes-runs/")
    parser.add_argument("--rebuild", action="store_true",
                        help="Recompute metrics from stored traces before summarising")
    parser.add_argument("--csv", type=Path, default=None, help="Also write the comparison table to CSV")
    args = parser.parse_args(argv)

    run_dirs = [d for d in args.run_dirs if d.is_dir()]
    missing = [str(d) for d in args.run_dirs if not d.is_dir()]
    for path in missing:
        print(f"not a directory: {path}", file=sys.stderr)

    for run_dir in run_dirs:
        if args.rebuild:
            print(f"rebuilding {run_dir.name}")
            count = rebuild_run(run_dir)
            summary = rewrite_summary(run_dir)
            print(f"  {count} queries rebuilt, {summary['queries_ok']}/{summary['queries_total']} ok")

    rows = comparison_rows(run_dirs)
    print()
    print_table(rows)

    if args.csv and rows:
        fields = list(rows[0].keys())
        with args.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nwrote {args.csv}")
    return 0 if run_dirs else 1


if __name__ == "__main__":
    raise SystemExit(main())
