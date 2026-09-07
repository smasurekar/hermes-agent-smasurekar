"""Turn a Hermes session export into flat events and run metrics.

`hermes sessions export --format jsonl` writes one JSON object per SESSION, each
carrying its full `messages` list. A single eval query produces one root session
plus one session per delegated sub-agent (linked by `parent_session_id`), because
each query runs against its own isolated HERMES_HOME.

Two products come out of here:

* ``flatten_events`` - one record per message across every session, in order, with
  reasoning, tool calls and tool results kept intact. This is the archival trace:
  anything not surfaced in the metrics can be recovered from it later.
* ``compute_metrics`` - the headline numbers (latency, tokens, LLM calls,
  sub-agents, tool calls) plus per-tool and per-session breakdowns.

Nothing here talks to the network or imports Hermes; it only reads exported JSON,
so it can be re-run over an old run directory at any time (see summarize.py).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Session-level columns copied verbatim into the metrics blob. These are Hermes'
# own accounting, kept alongside our derived counts so the two can be compared.
_SESSION_SCALARS = (
    "id", "parent_session_id", "model", "started_at", "ended_at", "end_reason",
    "message_count", "tool_call_count", "api_call_count",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "reasoning_tokens", "estimated_cost_usd", "cost_status", "cost_source",
    "billing_provider", "billing_base_url", "title", "cwd", "profile_name",
)

# Message fields worth keeping in the flattened trace. Dropped: api_content and
# the codex_* mirrors, which duplicate content/reasoning at ~2x the bytes.
_MESSAGE_FIELDS = (
    "id", "role", "content", "reasoning", "reasoning_content", "tool_call_id",
    "tool_name", "tool_calls", "timestamp", "token_count", "finish_reason",
    "effect_disposition", "display_kind",
)


def load_sessions(path: Path) -> List[Dict[str, Any]]:
    """Read a sessions JSONL export. Bad lines are skipped, not fatal."""
    sessions: List[Dict[str, Any]] = []
    if not path.exists():
        return sessions
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                sessions.append(obj)
    return sessions


def _parse_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalise a message's tool_calls into ``[{id, name, arguments}]``.

    The column is JSON-encoded in the export and the provider shape varies
    (``{"function": {...}}`` vs flat), so both are handled. Arguments stay as the
    parsed object when they are valid JSON and as the raw string otherwise -
    a truncated or malformed argument blob is still evidence worth keeping.
    """
    raw = message.get("tool_calls")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []

    parsed: List[Dict[str, Any]] = []
    for call in raw:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else call
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                pass
        parsed.append({
            "id": call.get("id"),
            "name": fn.get("name"),
            "arguments": args,
        })
    return parsed


def _delegated_task_count(tool_calls: Iterable[Dict[str, Any]]) -> int:
    """How many sub-agent tasks a set of tool calls actually requested.

    One ``delegate_task`` call can spawn several children (``tasks`` is a list), so
    counting calls under-reports. Non-spawn actions (list/steer/stop) request no
    children and are excluded.
    """
    total = 0
    for call in tool_calls:
        if call.get("name") != "delegate_task":
            continue
        args = call.get("arguments")
        if not isinstance(args, dict):
            total += 1  # unparseable args: assume the usual single task
            continue
        if args.get("action") not in (None, "", "spawn"):
            continue
        tasks = args.get("tasks")
        total += len(tasks) if isinstance(tasks, list) else 1
    return total


def _sorted_messages(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Messages in wire order: by row id, falling back to timestamp."""
    messages = [m for m in (session.get("messages") or []) if isinstance(m, dict)]

    def key(message: Dict[str, Any]):
        raw_id = message.get("id")
        try:
            return (0, float(raw_id))
        except (TypeError, ValueError):
            return (1, float(message.get("timestamp") or 0))

    return sorted(messages, key=key)


def _order_sessions(sessions: List[Dict[str, Any]], root_id: Optional[str]) -> List[Dict[str, Any]]:
    """Root session first, then sub-agents oldest-first."""
    root = [s for s in sessions if s.get("id") == root_id] if root_id else []
    if not root:
        root = [s for s in sessions if not s.get("parent_session_id")][:1]
    root_ids = {s.get("id") for s in root}
    rest = sorted(
        (s for s in sessions if s.get("id") not in root_ids),
        key=lambda s: (s.get("started_at") or 0, str(s.get("id"))),
    )
    return root + rest


def flatten_events(sessions: List[Dict[str, Any]], root_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """One record per message across all sessions, root first then sub-agents."""
    events: List[Dict[str, Any]] = []
    seq = 0
    for session in _order_sessions(sessions, root_id):
        session_id = session.get("id")
        is_sub = bool(session.get("parent_session_id"))
        for index, message in enumerate(_sorted_messages(session)):
            record = {
                "seq": seq,
                "session_id": session_id,
                "parent_session_id": session.get("parent_session_id"),
                "is_subagent": is_sub,
                "message_index": index,
            }
            for field in _MESSAGE_FIELDS:
                if field == "tool_calls":
                    continue
                record[field] = message.get(field)
            record["tool_calls"] = _parse_tool_calls(message)
            events.append(record)
            seq += 1
    return events


def write_events(events: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def final_answer(sessions: List[Dict[str, Any]], root_id: Optional[str] = None) -> str:
    """Last assistant message with text and no pending tool calls, from the root session."""
    ordered = _order_sessions(sessions, root_id)
    if not ordered:
        return ""
    for message in reversed(_sorted_messages(ordered[0])):
        if message.get("role") != "assistant":
            continue
        if _parse_tool_calls(message):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
    return ""


def compute_metrics(
    sessions: List[Dict[str, Any]],
    *,
    usage: Optional[Dict[str, Any]] = None,
    latency_seconds: Optional[float] = None,
    root_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Headline metrics plus breakdowns.

    Headline token and LLM-call figures cover the root agent AND every sub-agent,
    summed from the session rows - the only source that sees the children. The
    ``hermes -z --usage-file`` report (``usage``) covers the root alone; it is kept
    as the ``*_root`` series and used as the fallback when no session rows exist.
    """
    usage = usage or {}
    ordered = _order_sessions(sessions, root_id or usage.get("session_id"))
    root = ordered[0] if ordered else {}
    subagent_sessions = ordered[1:]

    tool_counter: Counter = Counter()
    tool_failures: Counter = Counter()
    total_tool_calls = 0
    root_tool_calls = 0
    subagent_tool_calls = 0
    delegated_tasks = 0
    delegate_calls = 0
    assistant_turns = 0
    turns_with_reasoning = 0

    for session in ordered:
        is_sub = session.get("id") != root.get("id")
        for message in _sorted_messages(session):
            role = message.get("role")
            if role == "assistant":
                assistant_turns += 1
                if (message.get("reasoning") or message.get("reasoning_content")):
                    turns_with_reasoning += 1
                calls = _parse_tool_calls(message)
                for call in calls:
                    name = call.get("name") or "<unknown>"
                    tool_counter[name] += 1
                    if name == "delegate_task":
                        delegate_calls += 1
                total_tool_calls += len(calls)
                if is_sub:
                    subagent_tool_calls += len(calls)
                else:
                    root_tool_calls += len(calls)
                delegated_tasks += _delegated_task_count(calls)
            elif role == "tool":
                # Tool results carry the outcome; a leading "Error" is Hermes'
                # convention for a failed call across every tool.
                content = message.get("content")
                if isinstance(content, str) and content.lstrip().lower().startswith("error"):
                    tool_failures[message.get("tool_name") or "<unknown>"] += 1

    def _sum(field: str) -> int:
        return sum(int(s.get(field) or 0) for s in ordered)

    def _usage_int(field: str) -> Optional[int]:
        value = usage.get(field)
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    # Root-only figures, straight from the provider usage report. Verified to match
    # the root session row exactly, which is what licenses summing the rows below.
    root_input = _usage_int("input_tokens")
    root_output = _usage_int("output_tokens")
    root_llm_calls = _usage_int("api_calls")

    # HEADLINE figures cover the whole query: root agent AND every sub-agent it
    # spawned. Sub-agent tokens are real spend on real LLM calls, so reporting the
    # root alone would understate a fanned-out run several-fold and make the
    # skill arms look far cheaper than they are. Session rows are the only source
    # that sees the children, so they win here; the usage report is the fallback
    # for a run whose export failed, and is kept as the *_root series regardless.
    session_input, session_output = _sum("input_tokens"), _sum("output_tokens")
    session_llm_calls = _sum("api_call_count")
    have_rows = bool(ordered)

    metrics: Dict[str, Any] = {
        # --- the six requested headline metrics (root + sub-agents) -----------
        "latency_total_seconds": round(latency_seconds, 3) if latency_seconds is not None else None,
        "token_usage_input": session_input if have_rows else (root_input or 0),
        "token_usage_output": session_output if have_rows else (root_output or 0),
        "llm_calls": session_llm_calls if have_rows else (root_llm_calls or 0),
        "subagents_invoked": len(subagent_sessions),
        "tool_calls_total": total_tool_calls,
        # --- same figures for the root agent alone ----------------------------
        "token_usage_input_root": root_input if root_input is not None else int(root.get("input_tokens") or 0),
        "token_usage_output_root": root_output if root_output is not None else int(root.get("output_tokens") or 0),
        "llm_calls_root": root_llm_calls if root_llm_calls is not None else int(root.get("api_call_count") or 0),
        # --- provenance -------------------------------------------------------
        "token_source": "session_rows" if have_rows else "usage_file",
        "usage_file_present": bool(usage),
        # --- breakdowns -------------------------------------------------------
        "subagent_tasks_requested": delegated_tasks,
        "delegate_task_calls": delegate_calls,
        "tool_calls_root": root_tool_calls,
        "tool_calls_subagents": subagent_tool_calls,
        "tool_call_counts": dict(sorted(tool_counter.items(), key=lambda kv: (-kv[1], kv[0]))),
        "tool_error_counts": dict(sorted(tool_failures.items(), key=lambda kv: (-kv[1], kv[0]))),
        "assistant_turns": assistant_turns,
        "turns_with_reasoning": turns_with_reasoning,
        "sessions_total": len(ordered),
        # --- token/cost detail (root + sub-agents) ----------------------------
        "cache_read_tokens": _sum("cache_read_tokens") if have_rows else (_usage_int("cache_read_tokens") or 0),
        "cache_write_tokens": _sum("cache_write_tokens") if have_rows else (_usage_int("cache_write_tokens") or 0),
        "reasoning_tokens": _sum("reasoning_tokens") if have_rows else (_usage_int("reasoning_tokens") or 0),
        "total_tokens": (session_input + session_output) if have_rows else (_usage_int("total_tokens") or 0),
        "estimated_cost_usd": round(sum(float(s.get("estimated_cost_usd") or 0) for s in ordered), 6)
                              if have_rows else usage.get("estimated_cost_usd"),
        "estimated_cost_usd_root": usage.get("estimated_cost_usd"),
        "cost_status": usage.get("cost_status") or root.get("cost_status"),
        # --- identity ---------------------------------------------------------
        "model": usage.get("model") or root.get("model"),
        "provider": usage.get("provider") or root.get("billing_provider"),
        "root_session_id": root.get("id") or usage.get("session_id"),
        "end_reason": root.get("end_reason"),
        "completed": usage.get("completed"),
        "failed": usage.get("failed"),
    }
    metrics["sessions"] = [
        {key: session.get(key) for key in _SESSION_SCALARS} for session in ordered
    ]
    return metrics


# Column order for metrics.csv. Kept explicit so the file stays diffable and
# comparable across arms even as the metrics blob grows.
CSV_COLUMNS = [
    "task_id", "experiment", "status", "exit_code",
    # The six headline metrics, covering the root agent AND its sub-agents.
    "latency_total_seconds", "token_usage_input", "token_usage_output",
    "llm_calls", "subagents_invoked", "tool_calls_total",
    # The same, for the root agent alone.
    "token_usage_input_root", "token_usage_output_root", "llm_calls_root",
    "subagent_tasks_requested", "delegate_task_calls",
    "tool_calls_root", "tool_calls_subagents",
    "assistant_turns", "turns_with_reasoning", "sessions_total",
    "cache_read_tokens", "reasoning_tokens", "total_tokens", "estimated_cost_usd",
    "model", "provider", "root_session_id", "end_reason",
    "category", "answer_type", "expected_answer", "answer_chars",
]
