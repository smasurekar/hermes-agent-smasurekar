---
name: deep-research
description: Run a planned, fanned-out, cited deep research pass.
version: 0.1.0
author: smasurekar
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Web, Citations, Delegation]
    requires_toolsets: [web, delegation]
---

# Deep Research Skill

Answer a research question from live sources. Decide whether a plan is needed, send the
research out to parallel sub-agents, then write one cited answer.

Working directory for this run: `~/.hermes/research/${HERMES_SESSION_ID}/`. Create it before
writing anything into it.

## When to Use

- The user says "research", "deep dive", "compare", "write a report on", "what's the latest on".
- The answer needs several sources, or facts newer than your training data.
- Do **not** use it for a single lookup, or anything already in this chat or in local files —
  call `web_search` directly instead.

## Prerequisites

The `web` and `delegation` toolsets must both be enabled — check with `hermes doctor`, or pass
`-t web,skills,delegation`. A web search backend must be configured (`web.backend` in
`config.yaml`).

## Quick Reference

| Step | Call |
|---|---|
| Save the plan | `write_file(path="~/.hermes/research/${HERMES_SESSION_ID}/plan.md", ...)` |
| Fan out research | `delegate_task(tasks=[...])` — **at most 5 at a time** |
| Search / read yourself | `web_search(query=...)` / `web_extract(urls=[...])` |

## Procedure

### 1. Decide: plan or no plan

Write a plan first if **any one** of these is true:

- The request has three or more separate deliverables.
- The answer's shape must be fixed before researching (sectioned report, comparison table, briefing).
- The list of candidates is **open** — no single source gives you the list, so you must build it.
- The question narrows in **stages** — a later part needs an answer the earlier part produces.

Skip the plan when you can already write every question you need to ask; go to step 3.
Never plan after research has started — a late plan cannot account for what you already found.

### 2. Plan (only if step 1 said yes)

Delegate **one** sub-agent. Give it the user's request verbatim and tell it to write
`~/.hermes/research/${HERMES_SESSION_ID}/plan.md` containing:

- **Goal** — one line.
- **Components** — the 3–6 things the answer must cover.
- **Constraints** — output shape, language, what is out of scope.
- **Queries** — up to 5 standalone search questions, each marked `low`, `medium`, or `high`
  depth and tied to a component.

Wait for it, then read the file. If the plan comes back thin, write the queries yourself and
move on — do not delegate the plan twice.

### 3. Research (fan out, max 5)

Send one `delegate_task` entry per query, up to 5 in a single call. Each `goal` must stand on
its own — the child cannot see this conversation. Put the plan path in `context` if there is one.

Tell every researcher to:

- Search first, then open the best pages with `web_extract`. A search snippet is not evidence
  for a number, date, or quote.
- Spend about 1 search on a `low` query, 3 on `medium`, 6 on `high`, then stop.
- Return its findings, the exact URL behind each one, and anything it could not find.
- Never answer from memory.

With no plan, write your own queries (still max 5) and fan out the same way. Independent
questions go out together; a question that depends on another waits for it.

### 4. Check the gaps

Read every result and list what the answer still needs. If you cannot name what is missing,
stop. Do at most one more round, aimed only at the gaps.

### 5. Write the answer

- Cite every fact as `[1]`, `[2]`, using only URLs the researchers actually returned.
- Narrow question → lead with the direct answer, then the support. Broad question → a short
  report with headings.
- State plainly what you could not verify. Never fill a gap from memory.
- End with `## Sources`: one line per citation, full URL.

## Pitfalls

- Children know nothing about this chat — repeat every needed detail in each task.
- A child's summary is a self-report. Trust a URL you can open, not a claim.
- A query that came back thin means the target was wrong, not the wording. Change the target.
- Never point two tasks at the same unresolved fact.
- More than 5 parallel children burns tokens for little gain; the runtime cap is separate
  (`delegation.max_concurrent_children`).

## Verification

Every claim maps to a URL listed in `## Sources`, no more than 5 researchers ran at once, and
unresolved gaps are stated rather than guessed.
