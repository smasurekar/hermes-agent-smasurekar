# hermes-runs — DeepSearchQA experiment harness

Runs a DeepSearchQA dataset through the Hermes agent, one process per query, and
records the answer, the full agent trace and the run metrics under a timestamped
directory here.

Built to compare three arms:

| arm | skills toolset | `-s` preload | prompt prefix |
|---|---|---|---|
| `no-skill` | off | — | — |
| `forced-skill` | on | `deep-research` | `/deep-research ` |
| `auto-skill` | on | — | — |

`no-skill` is the pure agent: dropping the `skills` toolset removes the skill
tools *and* the skills index from the system prompt, so there is nothing to
discover. `forced-skill` puts the skill body in the prompt and marks every query.
`auto-skill` leaves the skill discoverable and lets the agent choose. Everything
else — model, toolsets (including `delegation`), turn caps, budgets — is held
identical across arms, so a difference in the numbers is attributable to the skill.

## Quick start

```bash
PY=~/.hermes/venvs/hermes-dev/bin/python

# see the exact commands without running anything
$PY dsqa_runner.py --dataset dsqa2 --experiment all --dry-run

# smoke test: 2 tasks, all three arms (~8 min)
$PY dsqa_runner.py --dataset dsqa2 --experiment all --concurrency 2

# the real thing
$PY dsqa_runner.py --dataset dsqa90 --experiment no-skill     --concurrency 6
$PY dsqa_runner.py --dataset dsqa90 --experiment forced-skill --concurrency 6
$PY dsqa_runner.py --dataset dsqa90 --experiment auto-skill   --concurrency 6

# compare finished runs
$PY summarize.py 20260907-*__dsqa90__* --csv comparison.csv
```

Use `--concurrency` to set how many queries run at once; each is its own OS
process with its own Hermes home, so they do not contend. `--limit N` and
`--tasks id1,id2` narrow the task list; `--resume-dir DIR --resume` re-runs only
the queries that have not yet succeeded.

## Files

| file | role |
|---|---|
| `dsqa_runner.py` | orchestrator: loads the dataset, spawns workers, aggregates |
| `run_query.py` | one query, one process — isolation, run, export, metrics |
| `trace_utils.py` | session export → flat events + metrics (no network, no Hermes import) |
| `summarize.py` | rebuild metrics from stored traces; compare arms |
| `experiments.yaml` | the three arm definitions |

## Output layout

```
hermes-runs/<timestamp>__<dataset>__<arm>/
  run_config.json        model, base_url, toolsets, skills, git commit, env
  manifest.json          the exact task list
  config.snapshot.yaml   config the agents ran with, secrets redacted
  skills_snapshot.txt    what `hermes skills list` reported at run time
  run.log                orchestrator log
  summary.json           aggregates + per-task rows
  metrics.csv            one row per query
  queries/<task_id>/
    answer.md            final answer
    result.json          answer + metrics + config + artifact index, in one file
    metrics.json         metrics alone
    usage.json           provider usage report from `hermes --usage-file`
    prompt.txt           exact text sent (with the arm's prefix)
    task.json            dataset metadata, incl. the expected answer
    stdout.txt/stderr.txt
    trace/sessions.jsonl full session export: root agent + every sub-agent
    trace/events.jsonl   flattened per-message trace: reasoning, tool args, results
    trace/trace.jsonl    Claude Code format, for the HF Agent Trace Viewer
    agent_cwd/           working directory the agent ran in
    research_artifacts/  files the agent wrote under ~/.hermes/research (plan.md)
    hermes_home/         isolated home: logs/ tracked, state.db not (see .gitignore)
```

## Metrics

The six headline metrics, in `metrics.csv` and `summary.json`:

`latency_total_seconds`, `token_usage_input`, `token_usage_output`, `llm_calls`,
`subagents_invoked`, `tool_calls_total`.

**These cover the root agent *and* every sub-agent it spawned.** Sub-agent tokens
are real spend on real LLM calls, and a fanned-out run makes several times as many
as the root reports — the `forced-skill` arm spawns 5 children per query, so
root-only accounting would understate it roughly 3x. The `hermes --usage-file`
report sees only the root; it is preserved as `*_root` (`token_usage_input_root`,
`llm_calls_root`, ...) and used as a fallback when no session rows exist.
`token_source` records which was used.

Also recorded: per-tool call counts and error counts, root/sub-agent tool splits,
`subagent_tasks_requested` (a single `delegate_task` can spawn several children),
assistant turns, turns with reasoning, cache and reasoning tokens, cost, and the
full per-session row for every session.

Anything not surfaced as a metric can be recovered from `trace/events.jsonl`,
which keeps every message with its reasoning, tool arguments and tool results.
`summarize.py --rebuild` recomputes metrics from those traces without re-running.

## How isolation works

Each query gets a private `HERMES_HOME` under its own directory, seeded from the
real one: `config.yaml` copied and patched, `.env` and `skills/` symlinked. That
gives each query its own `state.db` (no SQLite contention at any concurrency), a
session export containing this query's root and sub-agents and nothing else, and
no memory or session bleed between eval items.

The config patch sets the arm's `max_turns` and `run_budget_seconds`, and turns
off `auxiliary.title_generation` and the skill `curator` — both make background
LLM calls that would otherwise inflate the token and call counts with work the
query never asked for.

**Secrets are never copied.** `.env` is symlinked, and the `api_key` in the
copied config is a `${ENV}` reference, not a literal.

## Notes and limits

- **Disk.** Roughly 1.1 MB tracked per query, plus ~6 MB of untracked
  `hermes_home/`. A full 90-task run across three arms is ~300 MB tracked. Pass
  `--prune-home` to delete each isolated home once its trace is exported.
- **Cost is not populated** for the Inference Hub provider — it has no pricing
  data in Hermes, so `estimated_cost_usd` reads 0. Use the token counts instead.
- **No grader.** The harness records answers and the expected answer from
  `tests/metadata.json`; it does not score them. The datasets ship a verifier
  (`tests/verifier.py`) that needs `GEMINI_API_KEY`, which is a separate step.
- `/deep-research` is not a slash command in `-z` mode — it is sent as literal
  text. The real enforcement in the `forced-skill` arm is `-s deep-research`,
  which preloads the skill body into the system prompt; the prefix is a marker
  on top of that.
