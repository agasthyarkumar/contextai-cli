# aicontext — User Manual

> Version 0.1.0

---

## Table of Contents

1. [What is aicontext?](#1-what-is-aicontext)
2. [How it works](#2-how-it-works)
3. [Requirements](#3-requirements)
4. [Installation](#4-installation)
5. [First-time setup](#5-first-time-setup)
6. [Configuration reference](#6-configuration-reference)
7. [Commands](#7-commands)
   - [init](#71-aicontext-init)
   - [update](#72-aicontext-update)
   - [watch](#73-aicontext-watch)
   - [show](#74-aicontext-show)
   - [clean](#75-aicontext-clean)
8. [Output files](#8-output-files)
9. [Using context with an LLM](#9-using-context-with-an-llm)
10. [LLM providers](#10-llm-providers)
11. [What gets indexed](#11-what-gets-indexed)
12. [Incremental vs full scan](#12-incremental-vs-full-scan)
13. [Git hook](#13-git-hook)
14. [Troubleshooting](#14-troubleshooting)
15. [Project file reference](#15-project-file-reference)

---

## 1. What is aicontext?

`aicontext` is a local CLI tool that reads your codebase, summarises it using an LLM, and writes two context files — `context.json` and `context.md` — that you can paste directly into any LLM chat to give it instant knowledge of your project.

**The problem it solves:** Every time you open a new chat with an LLM, you have to re-explain your project. Pasting raw source files wastes tokens and hits context limits. `aicontext` keeps a compressed, always-up-to-date summary that fits in a fraction of the tokens.

**Key properties:**
- Only sends **changed files** to the LLM on each run — not the whole codebase.
- Updates context **incrementally**, preserving summaries for unchanged modules.
- Runs **automatically** after every `git commit` via a post-commit hook.
- Works with **Groq Cloud** (default) or a **local Ollama** instance.

---

## 2. How it works

```
git commit
    │
    ▼
post-commit hook
    │
    ▼
aicontext update
    │
    ├─ git diff HEAD~1..HEAD  →  list of changed files
    │
    ├─ read changed files (up to MAX_FILE_SIZE_KB each)
    │
    ├─ load existing context.json
    │
    ├─ build prompt  (existing context + changed file content + diff)
    │
    ├─ call LLM  (Groq or Ollama)
    │
    ├─ parse JSON response
    │
    ├─ merge into existing context  (unchanged modules kept as-is)
    │
    ├─ write context.json  (atomic write)
    │
    └─ write context.md    (rendered Markdown)
```

On the very first run (`--scan`), all project files are collected instead of just the diff.

---

## 3. Requirements

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.9 | 3.11+ recommended |
| Git | any | must be in `PATH` |
| Groq API key | — | free tier available at console.groq.com |
| Ollama | any | only if using local LLM mode |

Python packages installed automatically:

| Package | Purpose |
|---|---|
| `typer` | CLI framework |
| `python-dotenv` | loads `.aicontext.env` |
| `groq` | Groq Cloud client |
| `watchdog` | file-watching for `aicontext watch` (optional) |

---

## 4. Installation

### Option A — editable install (recommended for development)

```bash
git clone <repo-url>
cd contextai-cli
pip install -e .
```

With file-watching support:

```bash
pip install -e ".[watch]"
```

### Option B — install directly from the folder

```bash
pip install /path/to/contextai-cli
```

### Verify the install

```bash
aicontext --help
```

You should see the list of commands printed to the terminal.

---

## 5. First-time setup

Run these steps once per project you want to track.

### Step 1 — Navigate to your project

```bash
cd /path/to/your/project
```

The project must be a git repository (`git init` if it is not).

### Step 2 — Run init

```bash
aicontext init
```

This does two things:

1. Copies `.aicontext.env.example` → `.aicontext.env` in the current directory.
2. Installs a `post-commit` hook at `.git/hooks/post-commit`.

### Step 3 — Add your API key

Open `.aicontext.env` in any editor:

```bash
nano .aicontext.env   # or code .aicontext.env, vim, etc.
```

Set your Groq API key:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

Get a free key at **console.groq.com → API Keys**.

### Step 4 — Generate the first context

```bash
aicontext update --scan
```

This scans up to 30 files across the project and writes `context.json` and `context.md`.

```
Updating context…
✓ Full scan complete. Indexed 12 module(s).
```

### Step 5 — Done

From this point on, every `git commit` automatically triggers `aicontext update` and keeps the context files fresh.

---

## 6. Configuration reference

All configuration lives in `.aicontext.env` in your project root. This file is **separate from your project's own `.env`** to avoid variable name clashes and is automatically git-ignored.

```env
# ── LLM Provider ─────────────────────────────────────────
LLM_PROVIDER=groq          # groq | ollama

# ── Groq (default) ───────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# ── Ollama (local) ────────────────────────────────────────
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3

# ── File handling ─────────────────────────────────────────
MAX_FILE_SIZE_KB=100
CONTEXT_FILE=context.json
CONTEXT_MD_FILE=context.md
IGNORE_DIRS=node_modules,.git,build,dist,__pycache__,.venv,venv,.next,.nuxt
IGNORE_EXTENSIONS=.pyc,.pyo,.so,.dll,.jpg,.png,.gif,.mp4,.zip,.tar,.gz,.lock
```

### All variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Which LLM backend to use: `groq` or `ollama` |
| `GROQ_API_KEY` | _(required)_ | Your Groq Cloud API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Any model available on your Groq account |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL of your running Ollama instance |
| `OLLAMA_MODEL` | `llama3` | Ollama model name (must be pulled first) |
| `MAX_FILE_SIZE_KB` | `100` | Files larger than this are skipped |
| `CONTEXT_FILE` | `context.json` | Path for the JSON output (relative to project root) |
| `CONTEXT_MD_FILE` | `context.md` | Path for the Markdown output |
| `IGNORE_DIRS` | see above | Comma-separated directory names to skip |
| `IGNORE_EXTENSIONS` | see above | Comma-separated file extensions to skip |

> Variables already set in your shell environment take precedence over `.aicontext.env` — `aicontext` never overwrites live environment variables.

---

## 7. Commands

### 7.1 `aicontext init`

**Purpose:** One-time setup for a project.

```
Usage: aicontext init [OPTIONS]

Options:
  -f, --force   Overwrite existing .aicontext.env and git hook
  --help
```

**What it does:**

| Step | Action |
|---|---|
| 1 | Copies `.aicontext.env.example` → `.aicontext.env` (skips if file exists) |
| 2 | Creates `.git/hooks/post-commit` and makes it executable (skips if exists) |

**Examples:**

```bash
# Standard first-time setup
aicontext init

# Re-run and overwrite everything (e.g. after changing the hook script)
aicontext init --force
```

**Notes:**
- Safe to run multiple times without `--force` — it will not overwrite existing files.
- If `.aicontext.env.example` is missing, `.aicontext.env` creation is skipped; you can create the file manually.
- If the directory is not a git repository, the hook step is skipped with a warning.

---

### 7.2 `aicontext update`

**Purpose:** Run the context update pipeline manually.

```
Usage: aicontext update [OPTIONS]

Options:
  -s, --scan      Full project scan instead of diff-only
  -v, --verbose   Print progress details
  --help
```

**Default behaviour (no flags):**

1. Runs `git diff HEAD~1..HEAD` to find changed files.
2. Reads only those files (up to `MAX_FILE_SIZE_KB` each).
3. Sends existing context + changed content to the LLM.
4. Merges the LLM response into `context.json` and rewrites `context.md`.

**With `--scan`:**

Skips the git diff and instead walks the entire project tree, collecting up to 30 code files. Use this on first run or after large refactors.

**Examples:**

```bash
# Incremental update after a commit
aicontext update

# First-time full scan
aicontext update --scan

# See exactly what files are being processed
aicontext update --scan --verbose
aicontext update --verbose
```

**When to use `--scan`:**

| Situation | Use |
|---|---|
| First time running on a project | `--scan` |
| After a normal commit | _(automatic via hook, or manual `update`)_ |
| After a large refactor touching many files | `--scan` |
| After renaming or moving many files | `--scan` |
| Routine incremental updates | `update` (no flags) |

**Exit codes:**

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (missing API key, not a git repo, LLM parse failure, etc.) |

---

### 7.3 `aicontext watch`

**Purpose:** Auto-update context whenever any file is saved (continuous mode).

```
Usage: aicontext watch [OPTIONS]

Options:
  -d, --debounce INTEGER   Seconds to wait before re-running after a change [default: 20]
  --help
```

Requires the `watchdog` package:

```bash
pip install watchdog
# or
pip install -e ".[watch]"
```

**How it works:**

- Watches the entire current directory recursively.
- When any file changes, waits `--debounce` seconds (to avoid firing on every keystroke during a save).
- Ignores changes to `context.json` and `context.md` themselves (prevents infinite loops).
- Calls `aicontext update` (incremental diff mode) on each trigger.

**Examples:**

```bash
# Start watching with default 20 s debounce
aicontext watch

# More responsive — re-run at most every 5 s
aicontext watch --debounce 5

# Slower — useful on large projects where LLM calls are expensive
aicontext watch --debounce 60
```

**Stopping:** Press `Ctrl+C`.

**Note:** `watch` mode runs `aicontext update` (diff mode), not `--scan`. If you want a full scan on each save, use a shell loop instead:

```bash
# Manual alternative using entr
find . -name "*.py" | entr -r aicontext update --scan
```

---

### 7.4 `aicontext show`

**Purpose:** Print the current context to stdout without opening a file.

```
Usage: aicontext show [OPTIONS]

Options:
  -f, --format TEXT   md or json  [default: md]
  --help
```

**Examples:**

```bash
# Print the human-readable Markdown context
aicontext show

# Print the raw JSON context
aicontext show --format json

# Copy context.md to clipboard (macOS)
aicontext show | pbcopy

# Copy context.md to clipboard (Linux with xclip)
aicontext show | xclip -selection clipboard

# Pipe JSON into jq for inspection
aicontext show --format json | jq '.modules | keys'

# Save a snapshot with a timestamp
aicontext show > "context_snapshot_$(date +%Y%m%d).md"
```

**Error:** Exits with code `1` if the context file does not exist yet. Run `aicontext update --scan` first.

---

### 7.5 `aicontext clean`

**Purpose:** Remove files created by aicontext.

```
Usage: aicontext clean [OPTIONS]

Options:
  -y, --yes    Skip the confirmation prompt
  -a, --all    Also remove .aicontext.env and the git post-commit hook
  --help
```

**Default behaviour (no flags):**

Lists and then removes:
- `context.json`
- `context.md`

You are shown what will be deleted and asked to confirm before anything is removed.

**With `--all`:**

Also removes:
- `.aicontext.env`
- `.git/hooks/post-commit`

**Examples:**

```bash
# Interactive cleanup of context files
aicontext clean

# Non-interactive cleanup of context files (useful in scripts)
aicontext clean -y

# Full teardown — remove everything aicontext created
aicontext clean --all

# Full teardown, no prompts (e.g. CI cleanup step)
aicontext clean --all -y
```

**Safety notes:**
- The command always lists files before deleting them.
- Without `-y`, you must explicitly type `y` to proceed.
- If no aicontext files are found, the command exits immediately without prompting.
- `--all` removes `.aicontext.env` which contains your API key. Re-run `aicontext init` to recreate it.

---

## 8. Output files

### `context.json`

Machine-readable JSON. Updated atomically (written to a `.tmp` file then renamed) to prevent corruption if the process is interrupted.

```json
{
  "version": "1.0",
  "last_updated": "2026-04-28T10:32:00+00:00",
  "project_name": "my-api",
  "summary": "A REST API built with FastAPI that handles user auth and order management.",
  "modules": {
    "app/main.py": {
      "summary": "Application entry point; mounts routers and configures middleware.",
      "functions": ["create_app", "lifespan"],
      "classes": [],
      "exports": ["app"],
      "dependencies": ["app/routers/auth.py", "app/routers/orders.py"]
    },
    "app/routers/auth.py": {
      "summary": "JWT-based authentication endpoints (login, refresh, logout).",
      "functions": ["login", "refresh_token", "logout"],
      "classes": ["AuthRouter"],
      "exports": ["router"],
      "dependencies": ["app/models/user.py", "app/services/token.py"]
    }
  },
  "recent_changes": [
    {
      "timestamp": "2026-04-28T10:32:00+00:00",
      "files": ["app/routers/auth.py"],
      "description": "Added refresh token endpoint and updated JWT expiry to 15 minutes."
    }
  ]
}
```

### `context.md`

Human-readable Markdown. Rendered from `context.json` after every update.

```markdown
# my-api — AI Context

> Last updated: `2026-04-28T10:32:00+00:00`

## Summary

A REST API built with FastAPI that handles user auth and order management.

## Modules

### `app/main.py`
Application entry point; mounts routers and configures middleware.
- **Exports:** app
- **Depends on:** app/routers/auth.py, app/routers/orders.py

### `app/routers/auth.py`
JWT-based authentication endpoints (login, refresh, logout).
- **Classes:** AuthRouter
- **Functions:** login, refresh_token, logout
- **Exports:** router
- **Depends on:** app/models/user.py, app/services/token.py

## Recent Changes

- **2026-04-28** — Added refresh token endpoint and updated JWT expiry to 15 minutes.
  - Files: `app/routers/auth.py`
```

### Committing context files

Both files are **not git-ignored** by default so you can commit them alongside your code, giving your whole team (and any LLM integration) access to the latest context.

If you prefer not to commit them, add to your project's `.gitignore`:

```gitignore
context.json
context.md
```

---

## 9. Using context with an LLM

### Paste into a chat (quickest)

```bash
aicontext show | pbcopy     # macOS
aicontext show | xclip -selection clipboard  # Linux
```

Then start your prompt with:

```
<project_context>
[paste here]
</project_context>

Now help me implement X...
```

### Use in a system prompt (API / programmatic)

```python
import json

with open("context.json") as f:
    ctx = json.load(f)

system_prompt = f"""You are an expert on the {ctx['project_name']} codebase.

Project summary: {ctx['summary']}

Modules:
{json.dumps(ctx['modules'], indent=2)}
"""
```

### Use with Claude Code

```bash
# Show context and let Claude Code read it
aicontext show > /tmp/project_context.md
# Then reference it in your Claude Code session
```

### Tips for getting the best results

- Always run `aicontext update --scan` after a large refactor before starting a new LLM session.
- `context.md` is better for human-facing chats; `context.json` is better for programmatic use.
- Prepend context at the **start** of the conversation, not mid-thread.
- You can append the `recent_changes` section to your prompt to highlight what you just changed:

```bash
aicontext show --format json | jq -r '
  .recent_changes[:3][] |
  "- \(.timestamp[:10]): \(.description)"
'
```

---

## 10. LLM providers

### Groq (default)

Fast cloud inference. Free tier is generous for development use.

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```

Get an API key at **console.groq.com**.

Other available models (set as `GROQ_MODEL`):

| Model | Notes |
|---|---|
| `llama-3.3-70b-versatile` | Default — best quality |
| `llama-3.1-8b-instant` | Faster, lower cost |
| `mixtral-8x7b-32768` | Larger context window |
| `gemma2-9b-it` | Google Gemma 2 |

Check **console.groq.com/docs/models** for the current list.

### Ollama (local, no API key required)

Run models entirely on your machine — no data leaves your network.

**Setup:**

```bash
# 1. Install Ollama from ollama.com
# 2. Pull a model
ollama pull llama3
# 3. Switch provider in .aicontext.env
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

**Tested models:**

| Model | Pull command | Notes |
|---|---|---|
| `llama3` | `ollama pull llama3` | Good general quality |
| `mistral` | `ollama pull mistral` | Fast, good JSON adherence |
| `codellama` | `ollama pull codellama` | Code-focused |
| `phi3` | `ollama pull phi3` | Lightweight, runs on CPU |

**Notes:**
- Ollama must be running before `aicontext update` is called (`ollama serve`).
- Local models are slower than Groq but free and private.
- JSON output quality varies by model — `mistral` tends to be most reliable.

---

## 11. What gets indexed

### Included file types

```
Python    .py
JS/TS     .js  .ts  .jsx  .tsx
Go        .go
Rust      .rs
Java      .java
C/C++     .c  .cpp  .h
Ruby      .rb
PHP       .php
Swift     .swift
Kotlin    .kt
C#        .cs
Shell     .sh  .bash  .zsh
Config    .yaml  .yml  .toml  .ini  .cfg  .conf
Data      .json  .sql
Docs      .md
Web       .html  .css  .scss
```

### Excluded by default

**Directories:**
`node_modules`, `.git`, `build`, `dist`, `__pycache__`, `.venv`, `venv`, `env`, `.tox`, `.cache`, `tmp`, `temp`, `.next`, `.nuxt`, `coverage`, `.nyc_output`

**Extensions:**
`.pyc`, `.pyo`, `.pyd`, `.so`, `.dylib`, `.dll`, `.exe`, `.bin`, images, audio, video, archives, lock files

**Size limit:** Files larger than `MAX_FILE_SIZE_KB` (default 100 KB) are skipped. Files exactly at the limit are truncated with a `[file truncated]` notice so the LLM is aware.

### Customising what gets indexed

Edit `IGNORE_DIRS` and `IGNORE_EXTENSIONS` in `.aicontext.env`:

```env
# Add your own build output folders
IGNORE_DIRS=node_modules,.git,build,dist,__pycache__,.venv,venv,my_generated_folder

# Ignore additional extensions
IGNORE_EXTENSIONS=.pyc,.lock,.sum,.snap
```

---

## 12. Incremental vs full scan

| | `aicontext update` | `aicontext update --scan` |
|---|---|---|
| **Files processed** | Only files changed in last commit | Up to 30 files across the whole project |
| **LLM calls** | 1 (small prompt) | 1 (larger prompt) |
| **Speed** | Fast | Slower |
| **Token cost** | Low | Higher |
| **When to use** | Every commit | First run, after large refactors |
| **Existing modules** | Preserved (only updated ones change) | Replaced by fresh scan |

**Incremental mode** is the default because it is cheap and fast. The `merge_context` function in `storage/context_writer.py` ensures that unchanged modules are never touched — only the modules corresponding to changed files are overwritten.

---

## 13. Git hook

`aicontext init` writes the following script to `.git/hooks/post-commit`:

```sh
#!/bin/sh
# Installed by aicontext — updates LLM context after every commit.
aicontext update
```

The hook runs **after** every successful `git commit`. Failed commits (e.g. pre-commit hook rejections) do not trigger it.

### Checking if the hook is installed

```bash
cat .git/hooks/post-commit
```

### Removing the hook without removing other aicontext files

```bash
rm .git/hooks/post-commit
```

Or use:

```bash
aicontext clean --all   # removes hook + .aicontext.env + context files
```

### Disabling the hook temporarily

```bash
# Skip hook for one commit
git commit --no-verify -m "wip"

# Disable hook file without deleting it
chmod -x .git/hooks/post-commit

# Re-enable
chmod +x .git/hooks/post-commit
```

### If the hook is too slow

The LLM call adds 2–5 seconds to each commit. If that is too much:

1. Remove the hook: `rm .git/hooks/post-commit`
2. Run `aicontext update` manually when you want to refresh context.
3. Or use `aicontext watch` in a separate terminal during active development.

---

## 14. Troubleshooting

### "GROQ_API_KEY is not set"

```
Error: GROQ_API_KEY is not set.
Run 'aicontext init' and fill in your key in .aicontext.env
```

**Fix:** Open `.aicontext.env` and set `GROQ_API_KEY=gsk_...`. Make sure the file is in the directory where you run `aicontext`.

---

### "Not a git repository"

```
Error: Not a git repository. Run 'git init' first.
```

**Fix:** Initialise git in your project:

```bash
git init
git add .
git commit -m "initial commit"
```

Then run `aicontext init` again.

---

### "No changes detected in the last commit"

This is not an error — it means the last commit had no files that aicontext can index (e.g. only binary files or files in ignored dirs). If you want to force an update anyway:

```bash
aicontext update --scan
```

---

### "Could not parse JSON from LLM response"

The LLM returned something that could not be parsed as JSON. This is rare but can happen with weaker models.

**Fixes:**
1. Try again — LLM output is non-deterministic, it may succeed next time.
2. Switch to a stronger model: `GROQ_MODEL=llama-3.3-70b-versatile`
3. If using Ollama, try `mistral` which tends to produce cleaner JSON.

---

### "Ollama request failed"

```
Error: Ollama request failed: <urlopen error [Errno 111] Connection refused>
```

**Fix:** Ollama is not running. Start it:

```bash
ollama serve
```

---

### Context file looks outdated

The incremental update only processes files from the latest commit. If you made many changes across multiple commits since the last `--scan`, run:

```bash
aicontext update --scan
```

---

### Hook runs but context is not updating

Check whether `aicontext` is in the `PATH` available to git hooks. Git hooks run in a minimal shell environment.

**Fix:** Use the full path in the hook script:

```bash
# Find the full path
which aicontext

# Edit the hook
nano .git/hooks/post-commit
```

Replace `aicontext update` with the full path, e.g.:

```sh
#!/bin/sh
/home/yourname/.local/bin/aicontext update
```

---

### Running in CI

Use the standalone script to avoid needing the CLI installed:

```bash
python scripts/update_context.py --scan
```

Or pass the API key as an environment variable in your CI config:

```yaml
# GitHub Actions example
- name: Update aicontext
  env:
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
  run: python scripts/update_context.py
```

---

## 15. Project file reference

```
contextai-cli/
│
├── aicontext/                   Python package
│   ├── __init__.py              Package version
│   ├── cli.py                   All CLI commands (init/update/watch/show/clean)
│   ├── orchestrator.py          Pipeline logic (run_update, run_full_scan)
│   ├── config.py                Loads .aicontext.env into a config dict
│   │
│   ├── analyzers/
│   │   ├── git_diff.py          git diff / ls-files / rev-parse wrappers
│   │   └── file_collector.py    Project file walker + safe file reader
│   │
│   ├── llm/
│   │   ├── prompt_builder.py    Prompt templates (init-scan & incremental)
│   │   └── summarizer.py        Groq + Ollama callers, JSON fence stripper
│   │
│   └── storage/
│       └── context_writer.py    load / merge / save context.json + context.md
│
├── scripts/
│   └── update_context.py        Standalone runner for git hooks and CI
│
├── .aicontext.env.example       Template for user configuration
├── .gitignore                   Ignores .aicontext.env (has secrets)
├── requirements.txt             Pinned dependencies
├── setup.py                     Package install + entry point
├── README.md                    Quick-start reference
└── USER_MANUAL.md               This file
```

---

*Generated for aicontext v0.1.0*
