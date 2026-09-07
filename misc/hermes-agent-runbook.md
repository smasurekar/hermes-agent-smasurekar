# Hermes Agent Runbook — Nemotron 3 Ultra (Inference Hub) + Web Search + Custom Skills

Operator runbook for three tasks:

1. [Run Hermes with web search enabled and Nemotron 3 Ultra served from the NVIDIA Inference Hub OpenAI-compatible endpoint](#1-run-hermes-with-web-search--nemotron-3-ultra-inference-hub)
2. [Prepare a custom skill](#2-prepare-a-custom-skill)
3. [Run that same setup with your custom skills loaded](#3-run-with-web-search--nemotron-3-ultra--custom-skills)

Endpoint used throughout:

| Field | Value |
|---|---|
| Base URL | `https://inference-api.nvidia.com/v1` |
| Model id | `nvidia/nvidia/nemotron-3-ultra` |
| API key | `sk-...` (yours) |
| Wire protocol | OpenAI-compatible Chat Completions |

> The bundled `nvidia` provider profile (`plugins/model-providers/nvidia/__init__.py`) points at
> **NVIDIA NIM** (`https://integrate.api.nvidia.com/v1`, key `NVIDIA_API_KEY`) — a *different*
> service from Inference Hub. Do **not** reuse the `nvidia` provider name for this endpoint; a
> config entry whose name collides with a built-in provider is shadowed by the built-in
> (`hermes_cli/runtime_provider_custom.py::_shadowed_by_builtin`). This runbook registers Inference
> Hub as a **custom OpenAI-compatible provider** named `inference-hub`.

---

## 0. Prerequisites

### 0.1 Installed Hermes (normal operation)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc          # or ~/.zshrc
hermes --version
```

Windows (PowerShell): `iex (irm https://hermes-agent.nousresearch.com/install.ps1)`

### 0.2 Running from this source checkout (development)

Every `hermes <cmd>` below maps to `python -m hermes_cli.main <cmd>` from the repo root.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/.hermes/venvs/hermes-dev --python 3.12   # keep the venv OUTSIDE the checkout
source ~/.hermes/venvs/hermes-dev/bin/activate

uv pip install -e .            # enough for CLI + web search + skills
# uv pip install -e ".[all,dev]"   # adds messaging platforms, voice, and the test suite

hermes --version               # the venv installs the `hermes` entry point
```

The base install pulls the core deps (`openai`, `prompt_toolkit`, `httpx`, ...). Provider-specific
packages are lazy-installed on first use (`tools/lazy_deps.py`); the Tavily backend needs none — it
calls the API over raw `httpx`.

### 0.3 Files you will touch

| Path | Holds |
|---|---|
| `~/.hermes/.env` | Secrets only (API keys, tokens). Printed by `hermes config env-path`. |
| `~/.hermes/config.yaml` | Everything non-secret: model, providers, web backend, toolsets. Printed by `hermes config path`. |
| `~/.hermes/skills/<category>/<name>/SKILL.md` | Your skills. |

`config.yaml` string values expand `${VAR}` / `${env:VAR}` against the environment and `.env`
(`hermes_cli/config.py::_expand_env_vars`), so keys stay in `.env` and the YAML only references them.

If `HERMES_HOME` is set, substitute it for `~/.hermes` everywhere below.

---

## 1. Run Hermes with web search + Nemotron 3 Ultra (Inference Hub)

### Step 1.1 — Verify the endpoint before wiring anything

```bash
export IH_KEY='sk-...'
curl -sS https://inference-api.nvidia.com/v1/models \
  -H "Authorization: Bearer $IH_KEY" | head -c 2000
```

Confirm the exact model id appears in the catalog. Use the id exactly as returned — the double
`nvidia/nvidia/` prefix in `nvidia/nvidia/nemotron-3-ultra` is intentional if that is what the
catalog shows; if it differs, use the catalog value in every step below.

### Step 1.2 — Store the API key in `.env`

```bash
cat >> ~/.hermes/.env <<'EOF'
# NVIDIA Inference Hub (OpenAI-compatible)
HERMES_CUSTOM_INFERENCE_API_NVIDIA_COM_API_KEY=sk-...
EOF
chmod 600 ~/.hermes/.env
```

The `HERMES_CUSTOM_<HOST>_API_KEY` name is the convention the setup wizard itself uses
(`hermes_cli/config.py::custom_endpoint_key_env`) — any valid env var name works, as long as
`key_env` in the next step matches it.

### Step 1.3 — Register the provider and select the model

Two equivalent routes. **A** is interactive and does the probing for you; **B** is scriptable.

#### Route A — interactive wizard

```bash
hermes model
```

1. Choose **Custom endpoint (direct URL)** from the provider menu.
2. API base URL: `https://inference-api.nvidia.com/v1`
3. API key: paste `sk-...` (masked input; written to `.env`, not to `config.yaml`).
4. Hermes probes `/models` and prints how many models are visible — a failed probe is a warning, not a hard stop.
5. API mode: choose **chat_completions**.
6. Pick `nvidia/nvidia/nemotron-3-ultra` from the detected list (or type it).
7. Context length: leave blank to auto-detect, or enter e.g. `128k`.
8. Display name: `inference-hub`.

The wizard writes the `model:` section and saves the endpoint so it shows up as a named provider on
later runs.

#### Route B — edit `config.yaml` directly

Add a `providers:` entry and point `model:` at it:

```yaml
# ~/.hermes/config.yaml

providers:
  inference-hub:
    name: inference-hub
    api: https://inference-api.nvidia.com/v1
    key_env: HERMES_CUSTOM_INFERENCE_API_NVIDIA_COM_API_KEY
    transport: chat_completions          # `api_mode:` is accepted as a synonym
    default_model: nvidia/nvidia/nemotron-3-ultra
    discover_models: true                # false = show only the `models:` list in the picker
    models:
      nvidia/nvidia/nemotron-3-ultra:
        context_length: 131072           # set only if you know the served window

model:
  provider: inference-hub
  default: nvidia/nvidia/nemotron-3-ultra
  base_url: https://inference-api.nvidia.com/v1
  api_key: ${HERMES_CUSTOM_INFERENCE_API_NVIDIA_COM_API_KEY}
  api_mode: chat_completions
```

Field notes (`hermes_cli/runtime_provider_custom.py`):

- The entry URL key may be `api`, `url`, or `base_url` — `api` is the current form.
- `key_env` (an env var name) is preferred over an inline `api_key`; both are supported.
- Optional per-entry knobs: `extra_headers` (proxy/Cloudflare auth, never logged), `extra_body`,
  `capabilities`, `enabled: false` to keep an entry but hide it.
- **Do not name the entry `nvidia`** — see the note at the top.

Scalar values can also be set from the shell:

```bash
hermes config set model.provider inference-hub
hermes config set model.default nvidia/nvidia/nemotron-3-ultra
hermes config get model
```

### Step 1.4 — Enable web search

`web_search` / `web_extract` are in the default CLI toolset (`toolsets.py::_HERMES_CORE_TOOLS`), so
usually nothing is needed. Confirm and, if necessary, enable:

```bash
hermes tools list --platform cli | grep -i web
hermes tools enable web --platform cli     # only if `web` was disabled
```

Then pick a backend. **Recommended for this runbook: Tavily** — it serves both `web_search` and
`web_extract` from one key, so no second provider is needed.

```bash
cat >> ~/.hermes/.env <<'ENVEOF'
# Web search + extract
TAVILY_API_KEY=tvly-...
ENVEOF
chmod 600 ~/.hermes/.env

hermes config set web.backend tavily
hermes config get web
```

Equivalent YAML:

```yaml
# ~/.hermes/config.yaml
web:
  backend: tavily             # shared default for search + extract
  # search_backend: searxng   # optional per-capability override (wins over `backend`)
  # extract_backend: tavily
```

Interactive alternative (prompts for the key and writes both files for you):

```bash
hermes tools    # → "Web Search & Extract" → pick a provider; it prompts for the key/URL
```

**Is a key required?** No. With no web credentials at all, both tools still work through a keyless
free-tier rotation (Exa → Parallel → Firecrawl → Keenable, retrying the next vendor on a
rate-limit). That tier is throttled, last-resort, and never overrides a configured backend — fine
for a smoke test, not for repeated or unattended runs. Any keyed backend always wins. Turn the
keyless tier off entirely with `web.keyless_fallback: false`.

Valid backend ids (from `plugins/web/*/provider.py`): `firecrawl`, `searxng`, `brave-free`,
`ddgs`, `exa`, `parallel`, `tavily`, `perplexity`, `keenable`, `xai`.

| Backend | Key (in `~/.hermes/.env`) | Search | Extract |
|---|---|---|---|
| `firecrawl` (default) | `FIRECRAWL_API_KEY` (optional; `FIRECRAWL_API_URL` for self-hosted) | ✔ | ✔ |
| `searxng` | `SEARXNG_URL` (self-hosted, free) | ✔ | — |
| `brave-free` | `BRAVE_SEARCH_API_KEY` | ✔ | — |
| `ddgs` | none (`pip install ddgs`) | ✔ | — |
| `exa` | `EXA_API_KEY` (optional) | ✔ | ✔ |
| `parallel` | `PARALLEL_API_KEY` (optional) | ✔ | ✔ |
| `tavily` | `TAVILY_API_KEY` (optional) | ✔ | ✔ |
| `perplexity` | `PERPLEXITY_API_KEY` | ✔ | ✔ (snippets) |
| `keenable` | `KEENABLE_API_KEY` (optional) | ✔ | ✔ |
| `xai` | `XAI_API_KEY` or `hermes auth add xai-oauth` | ✔ | — |

Search-only backends must be paired with an extract-capable one via `web.extract_backend`.

Resolution order per capability: `web.search_backend` / `web.extract_backend` → `web.backend` →
auto-detect from env vars (only if no selection was ever written).

### Step 1.5 — Run

```bash
hermes doctor          # provider reachability + config sanity
hermes                 # interactive session
```

Inside the session:

```
/model                                     # confirm the active model
Search the web for the latest Nemotron 3 release notes and summarize with sources.
```

Expect a `web_search` tool call in the transcript.

One-shot / scripted (prints only the final answer):

```bash
hermes -z "Search the web for today's top AI infrastructure news and cite the sources."

# Per-invocation overrides, no config changes:
hermes --provider inference-hub -m nvidia/nvidia/nemotron-3-ultra -t web \
  -z "What changed in NVIDIA Nemotron this month? Cite URLs."
```

`--provider` accepts a built-in provider **or** any key from `providers:` in `config.yaml`
(`hermes_cli/_parser.py`). `-t/--toolsets` takes a comma-separated list; `web` yields
`web_search` + `web_extract`, `search` yields `web_search` only.

Environment-variable equivalents for CI: `HERMES_INFERENCE_PROVIDER`, `HERMES_INFERENCE_MODEL`.

### Step 1.6 — Verify

- `hermes config get model` shows provider `inference-hub` and the Nemotron model id.
- `hermes tools list --platform cli` shows `web` enabled.
- A web question triggers a visible `web_search` call and returns URLs.
- `hermes doctor` reports no provider/credential errors.

---

## 2. Prepare a custom skill

A skill is a markdown instruction document the agent loads on demand — no agent code changes. Make
it a skill when the capability is instructions + shell + existing tools; make it a tool when it
needs bespoke Python, auth flows, or binary/streaming handling.

### 2.1 Where it goes

```
~/.hermes/skills/<category>/<skill-name>/
├── SKILL.md          # required
├── references/       # optional: docs loaded on demand via skill_view(name, path)
├── scripts/          # optional: helper scripts the skill tells the agent to run
├── templates/        # optional
└── assets/           # optional
```

`~/.hermes/skills/` is the source of truth for a running Hermes: bundled, hub-installed, and
agent-created skills all live there. Skills committed to this repo under `skills/<category>/` or
`optional-skills/<category>/` are the *shipped* copies, seeded into `~/.hermes/skills/` on install
and `hermes update` — edit those only when you intend to contribute the skill upstream.

Extra directories can be scanned alongside:

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
    - ${SKILLS_REPO}/skills
```

### 2.2 Create the skill

```bash
mkdir -p ~/.hermes/skills/research/nemotron-web-brief/{scripts,references}
$EDITOR ~/.hermes/skills/research/nemotron-web-brief/SKILL.md
```

Example `SKILL.md` — a web-research skill scoped to the setup in Part 1:

```markdown
---
name: nemotron-web-brief
description: Build a cited web brief on a topic from live sources.
version: 0.1.0
author: Your Name (github-handle)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Web, Briefing, Citations]
    related_skills: [grounded-citations]
    requires_toolsets: [web]
---

# Nemotron Web Brief

Produce a short, source-cited brief on a topic using live web search and extraction.

## When to Use

- The user asks for "the latest", "what's new", or a briefing on a named topic.
- The answer depends on information newer than the model's training data.
- Do not use for questions answerable from the current conversation or local files.

## Quick Reference

| Step | Call |
|---|---|
| Find sources | `web_search(query="<topic> <year>", limit=8)` |
| Read a source | `web_extract(urls=["https://..."])` |
| Render the brief | `bash ${HERMES_SKILL_DIR}/scripts/render_brief.sh <title>` |

## Procedure

1. Run `web_search` with 2–3 differently-phrased queries; keep results from distinct domains.
2. `web_extract` the 3–5 most authoritative URLs. Prefer primary sources over aggregators.
3. Write the brief: one-line summary, 3–6 bullet findings, then a `Sources` list of full URLs.
4. Mark any claim carried by a single source as `(single source)`.

## Pitfalls

- Search results are ranked, not verified — never state a claim no extracted page supports.
- `web_extract` truncates long pages (default 15 000 chars, `web.extract_char_limit`); the footer
  names the on-disk file and the `read_file` call for the omitted middle.
- Search-only backends (`ddgs`, `brave-free`, `searxng`, `xai`) cannot extract — pair one with an
  extract-capable backend via `web.extract_backend`.

## Verification

Every bullet maps to at least one URL in `Sources`, and each URL was actually extracted.
```

### 2.3 Frontmatter rules that are actually enforced

Validator: `tools/skill_manager_tool.py::_validate_frontmatter`.

- File must **start** with `---` (no leading blank line, no BOM issues) and close with `---`.
- Frontmatter must parse as a YAML mapping.
- `name` and `description` are required. `name`: lowercase, hyphens/underscores, ≤ 64 chars.
- `description` ≤ 1024 chars hard limit — but new skills created through `skill_manage` are
  rejected above **60** chars (`agent/skill_utils.py::SKILL_PROMPT_DESC_LIMIT`), because the
  system-prompt skill index truncates at 57 chars + `...`. Write one ≤60-char sentence ending in a
  period; if it contains a `:`, quote it.
- Body after the closing `---` must be non-empty. Whole file ≤ 100 000 chars — split overflow into
  `references/`.

Optional, all under `metadata.hermes`:

| Field | Effect |
|---|---|
| `tags`, `related_skills` | Discovery / search ranking |
| `requires_toolsets`, `requires_tools` | Hidden unless those are available |
| `fallback_for_toolsets`, `fallback_for_tools` | Hidden **when** those are available |
| `config: [{key, description, default, prompt}]` | Non-secret settings under `skills.config.*` in `config.yaml`, injected into the skill message on load |
| `blueprint: {schedule, deliver, prompt}` | Marks the skill a runnable automation; installing it files a `/suggestions` entry rather than scheduling anything |

Top-level extras: `platforms: [linux, macos, windows]` (hides the skill on other OSes),
`required_environment_variables: [{name, prompt, help, required_for}]` (prompted securely on load,
never shown to the model, auto-passed through to `terminal`/`execute_code` sandboxes), and
`required_credential_files: [{path, description}]` for OAuth token files (paths relative to
`~/.hermes/`, mounted into Docker/Modal sandboxes).

### 2.4 Body conventions

- Standard section order: **When to Use → Quick Reference → Procedure → Pitfalls → Verification**.
  `When to Use` is the routing signal — write real trigger phrases.
- Progressive disclosure: the agent sees `{name, description}` first (~3k tokens for the whole
  index), loads the body only via `skill_view(name)`, and a `references/` file only via
  `skill_view(name, path)`. Keep `SKILL.md` lean and push depth into `references/`.
- `${HERMES_SKILL_DIR}` is substituted with the skill's absolute directory at load time (and
  `${HERMES_SESSION_ID}` with the session id) — use it to reference bundled scripts so the agent can
  run them without path math. Disable globally with `skills.template_vars: false`.
- Inline shell snippets `` !`cmd` `` in the body are **off by default** (they execute on the host
  without approval). Enable only for sources you trust: `skills.inline_shell: true`
  (`skills.inline_shell_timeout`, default 10s).
- Prefer stdlib Python / `curl` / existing Hermes tools over new dependencies; ship parsers in
  `scripts/` rather than expecting the model to rewrite them inline.
- Emit `[[as_document]]` in a response when produced images must arrive as files instead of
  recompressed image previews.

### 2.5 Alternatives to hand-authoring

| Route | Use it when |
|---|---|
| `/learn <source>` in a session | Turn a doc URL, local SDK, a book, or the workflow you just walked through into a skill. Large sources become a lean `SKILL.md` + one `references/` file per topic. |
| `skill_manage(action='create', name=..., category=..., content=...)` | The agent writes the skill itself. Targets `~/.hermes/skills/` only — never the repo tree. Skill writes always stage through the approval gate. |
| `hermes skills install <owner/repo/skill>` | Install from a registry (`hermes skills search`, `hermes skills browse --source ...`). |
| `write_file` + `git add` under `skills/<category>/` | Contributing the skill to this repo. Also read `skills/software-development/hermes-agent-skill-authoring/SKILL.md` and the "Skill authoring standards (HARDLINE)" section of `AGENTS.md`. |

### 2.6 Validate and test

```bash
hermes skills list --source local          # your skill should appear
hermes skills list --enabled-only

# Frontmatter check without leaving the shell:
python3 - <<'PY'   # run from the repo root (or with the Hermes venv active)
import pathlib, sys
sys.path.insert(0, ".")
from tools.skill_manager_tool import _validate_frontmatter
p = pathlib.Path.home() / ".hermes/skills/research/nemotron-web-brief/SKILL.md"
print(_validate_frontmatter(p.read_text(), new_skill=True) or "OK")
PY

# End-to-end:
hermes chat --toolsets skills,web -q "Use the nemotron-web-brief skill on 'NVIDIA Nemotron 3'"
```

Enable/disable individual skills interactively with `hermes skills config`.

---

## 3. Run with web search + Nemotron 3 Ultra + custom skills

Parts 1 and 2 must be complete. Nothing about the provider or web setup changes — only how skills
reach the session.

### 3.1 Confirm the pieces

```bash
hermes config get model                    # provider: inference-hub, default: nvidia/nvidia/nemotron-3-ultra
hermes config get web                      # backend selection
hermes tools list --platform cli | egrep -i "web|skills"
hermes skills list --source local
```

The `skills` toolset (`skills_list`, `skill_view`, `skill_manage`) and `web` are both in the default
CLI bundle. If either was disabled: `hermes tools enable skills web --platform cli`.

### 3.2 Interactive — every skill available on demand

```bash
hermes
```

The agent sees the skill index and loads what it needs. To drive it explicitly:

```
/nemotron-web-brief NVIDIA Nemotron 3 Ultra availability
/nemotron-web-brief /grounded-citations summarize this week's releases
```

Every installed skill is a slash command. Up to 5 leading `/skill` tokens are loaded in one message;
parsing stops at the first token that isn't an installed skill, so path-like arguments are safe.

### 3.3 Preloaded — skill in context from turn one

```bash
hermes -s nemotron-web-brief
hermes -s nemotron-web-brief,grounded-citations
hermes chat -s nemotron-web-brief -q "Brief me on NVIDIA Nemotron 3 Ultra."
```

`-s/--skills` repeats or comma-separates. Preloading costs the skill's tokens up front but removes
the discovery round-trip — worth it when you know the session is about that workflow.

### 3.4 Scripted / unattended

```bash
hermes --provider inference-hub \
       -m nvidia/nvidia/nemotron-3-ultra \
       -t web,skills,file \
       -s nemotron-web-brief \
       -z "Brief me on NVIDIA Nemotron 3 Ultra availability. Cite every claim." \
       --usage-file /tmp/hermes-usage.json

cat /tmp/hermes-usage.json    # cost, token counts, model, api_calls
```

`-z/--oneshot` prints only the final response — no banner, spinner, tool previews, or session line —
and auto-bypasses approvals. Memory, rules, and a CWD `AGENTS.md` still load; add `--ignore-rules`
to suppress that, or `--safe-mode` to disable all customizations.

From this source checkout, replace `hermes` with `python -m hermes_cli.main`.

### 3.5 Verify the whole path

A single successful run should show, in order:

1. The skill loading (`skill_view` call, or the preload notice with `-s`).
2. `web_search` and/or `web_extract` calls against the configured backend.
3. A final answer following the skill's Procedure, with a `Sources` section.
4. `hermes doctor` clean, and `/tmp/hermes-usage.json` naming `nvidia/nvidia/nemotron-3-ultra`.

---

## 4. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Requests hit `integrate.api.nvidia.com` | The provider entry is named `nvidia`, so the built-in NIM profile shadows it. Rename the entry (`inference-hub`) and update `model.provider`. |
| `auth_unavailable` / no credential | `key_env` in `providers:` doesn't match the var in `~/.hermes/.env`, or `.env` wasn't reloaded. Check with `hermes config env-path` and re-run. |
| Model missing from the picker | Live `/models` probe failed. Set `discover_models: false` and list the id under `models:`, or type it manually in `hermes model`. |
| 400 on unknown fields / reasoning params | Force `transport: chat_completions` on the entry; drop any `extra_body` the endpoint doesn't accept. |
| `web_search` errors or returns nothing | Backend selected but keyless/unkeyed. Check `hermes config get web`, set the matching key in `.env`, and remember `searxng`/`ddgs`/`brave-free`/`xai` cannot extract. |
| Search works, extract doesn't | Search-only backend. Set `web.extract_backend` to `firecrawl`/`tavily`/`exa`/`parallel`/`keenable`/`perplexity`. |
| Skill never loads | `description` over 60 chars (index truncation kills the routing signal), a `requires_toolsets` entry not enabled, a `platforms` mismatch, or the skill is disabled — check `hermes skills list --enabled-only` and `hermes skills config`. |
| Skill loads but its script isn't found | Reference it as `${HERMES_SKILL_DIR}/scripts/<file>`; confirm `skills.template_vars` isn't `false`. |
| Stale web results | `web.cache_ttl_minutes` (default 20) or `web.cache_enabled: false`; add staging hosts to `web.cache_exempt_hosts`. |
| Something in your config is suspect | `hermes chat --safe-mode` to isolate Hermes from your customizations; `hermes doctor` for a full check. |
| `hermes doctor`: "model.default ... is vendor-prefixed but model.provider is 'inference-hub'" | **Expected false positive.** That heuristic assumes `vendor/model` slugs belong to aggregators like OpenRouter, but Inference Hub ids genuinely carry the `nvidia/nvidia/` prefix. Ignore it — do not "fix" it by dropping the prefix or switching provider. |
| `hermes doctor`: "No API key found in ~/.hermes/.env" | Also expected. Doctor scans for *known* provider key names; a custom endpoint's `HERMES_CUSTOM_*_API_KEY` isn't one of them. The `✓ web search` / `✓ web extract` lines and a successful run are the real signal. |
| `hermes doctor`: "Config version outdated (v0 → vNN)" | A hand-written `config.yaml` has no version stamp. `hermes config migrate` adds the current defaults; it is not required for the runs above. |
| Usage report shows `"provider": "custom"` | Correct. Named custom endpoints resolve to the bare provider `custom` at runtime; the entry name is recovered separately (`canonical_custom_identity`). Check `"model"` in the report to confirm routing. |

## 5. Reference

| Topic | In-repo source |
|---|---|
| Provider profiles & registry | `providers/README.md`, `plugins/model-providers/README.md` |
| Custom-provider resolution | `hermes_cli/runtime_provider_custom.py` |
| Custom-endpoint setup wizard | `hermes_cli/model_setup_flows_custom.py` |
| Toolset definitions | `toolsets.py` |
| Web search backends | `plugins/web/*/provider.py`, `agent/web_search_registry.py` |
| Skill validation | `tools/skill_manager_tool.py`, `agent/skill_utils.py` |
| Skill authoring standards | `skills/software-development/hermes-agent-skill-authoring/SKILL.md`, `AGENTS.md` |
| Docs (published) | `website/docs/user-guide/configuring-models.md`, `website/docs/user-guide/features/web-search.md`, `website/docs/user-guide/features/skills.md`, `website/docs/developer-guide/creating-skills.md` |


---

## 6. Verified run (2026-09-07)

Part 1 was executed end-to-end on this checkout. What was actually run and observed:

| Step | Result |
|---|---|
| `curl https://inference-api.nvidia.com/v1/models` | HTTP 200; `nvidia/nvidia/nemotron-3-ultra` present in the catalog, exactly as written (the `nvidia/nvidia/` double prefix is real) |
| `uv venv ~/.hermes/venvs/hermes-dev --python 3.12` + `uv pip install -e .` | CPython 3.12.14, OpenAI SDK 2.24.0, `hermes` entry point on PATH |
| `~/.hermes/.env` | `HERMES_CUSTOM_INFERENCE_API_NVIDIA_COM_API_KEY`, `TAVILY_API_KEY`, mode `600` |
| `~/.hermes/config.yaml` | `providers.inference-hub` + `model:` + `web.backend: tavily` as in Step 1.3 Route B / Step 1.4 |
| `hermes config get model` | `provider: inference-hub`, `default: nvidia/nvidia/nemotron-3-ultra` (the `${...}` api_key ref expanded correctly) |
| `hermes tools list --platform cli` | `✓ enabled web`, `✓ enabled skills` |
| `hermes doctor` | `✓ web search (tavily)`, `✓ web extract (tavily)`; the 4 warnings it reports are the benign ones in the troubleshooting table |
| `hermes -z "Use web_search to find what NVIDIA Nemotron 3 Ultra is..."` | Answer returned with three cited URLs (developer.nvidia.com, huggingface.co, research.nvidia.com) |
| `hermes -z ... --usage-file /tmp/hermes-usage.json` | `"model": "nvidia/nvidia/nemotron-3-ultra"`, `"provider": "custom"`, `"api_calls": 2`, `"completed": true` |

Not exercised: the interactive TUI (`hermes` with no args) and the `hermes model` wizard — both
need a TTY. Route B (config file) covers the same ground non-interactively.
