# aicontext

A local developer tool that automatically analyses your codebase and maintains a compressed context file to reduce token usage when working with LLMs.

## How it works

```
git commit → post-commit hook → aicontext update
                                      │
                              git diff HEAD~1..HEAD
                                      │
                              read changed files
                                      │
                              call Groq LLM (llama-3.3-70b)
                                      │
                         merge into context.json + context.md
```

Only **changed files** are sent to the LLM on each run — keeping costs low.

---

## Quick start

### 1. Clone and install once (anywhere on your system)

```bash
# Clone to a permanent home — NOT inside a project you want to track
git clone <repo-url> ~/tools/contextai-cli
cd ~/tools/contextai-cli
pip install -e .

# Optional: file-watching support
pip install -e ".[watch]"

# Verify
aicontext --help
```

> `aicontext` is now a global command available in every terminal session, just like `git` or `pip`. The source code stays in `~/tools/contextai-cli` and is never copied into your projects.

### 2. Set up in any project you want to track

```bash
cd /path/to/your-project   # any existing git repo
aicontext init             # creates .aicontext.env + installs post-commit hook
```

Edit `.aicontext.env` and set your key:

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq
```

> `.aicontext.env` is intentionally separate from your project's `.env` so there is no variable clash. It is git-ignored automatically.

### 3. Generate the first context

```bash
aicontext update --scan   # full project scan (first time)
```

After that, every `git commit` triggers an automatic incremental update.

### What gets added to each project

```
your-project/
  .aicontext.env          ← your API key config  (git-ignored)
  .git/hooks/post-commit  ← auto-update hook
  context.json            ← generated context    (commit this)
  context.md              ← generated context    (commit this)

  # all your own code is untouched
```

The aicontext source code (`~/tools/contextai-cli`) is **never copied** into your projects.

---

## Commands

### `aicontext init`
Create `.aicontext.env` from the example file and install the git post-commit hook.

```bash
aicontext init           # safe — skips files that already exist
aicontext init --force   # overwrite existing config and hook
```

### `aicontext update`
Update `context.json` and `context.md` from the latest git changes.

```bash
aicontext update          # incremental — only processes files changed in last commit
aicontext update --scan   # full project scan (use this the first time)
aicontext update -v       # verbose output
```

### `aicontext watch`
Auto-update context whenever a file is saved (requires `watchdog`).

```bash
aicontext watch                # default 20 s debounce
aicontext watch --debounce 5   # re-run at most every 5 s
```

### `aicontext show`
Print the current context to stdout.

```bash
aicontext show               # prints context.md (human-readable)
aicontext show --format json # prints context.json (machine-readable)
```

### `aicontext clean`
Remove generated files (`context.json`, `context.md`) and optionally config + git hook. Source code is untouched.

```bash
aicontext clean          # removes context.json + context.md (asks for confirmation)
aicontext clean -y       # skip confirmation prompt
aicontext clean --all    # also removes .aicontext.env and the git hook
aicontext clean --all -y # non-interactive full cleanup
```

### `aicontext ignore`
Add aicontext's own source files to `.gitignore` so they are excluded from git without being deleted. Useful when you want to keep the tool working locally but not commit its source into your project.

```bash
aicontext ignore   # appends aicontext source entries to .gitignore
```

### `aicontext delete`
Remove all aicontext-added files from the **current project** (generated files + config + git hook). Your project's own code and the aicontext source in `~/tools/contextai-cli` are **never touched**.

```bash
aicontext delete      # shows what will be deleted, asks for confirmation
aicontext delete -y   # non-interactive, no prompt
```

> This command is blocked if you run it inside the aicontext source repo itself.

To also uninstall the CLI globally:

```bash
pip uninstall aicontext
```

---

## Output files

| File | Purpose |
|---|---|
| `context.json` | Machine-readable — paste into LLM system prompts |
| `context.md` | Human-readable — quick project overview |

Both files are updated incrementally — unchanged modules are never re-sent to the LLM.

---

## Using with an LLM

Paste `context.md` at the top of your prompt:

```
<context>
[paste context.md here]
</context>

Now help me add a feature to the auth module...
```

Or use `context.json` programmatically:

```python
import json
ctx = json.load(open("context.json"))
system_prompt = f"Project: {ctx['summary']}\nModules: {json.dumps(ctx['modules'])}"
```

---

## Local LLM (Ollama)

Switch to a local model by editing `.aicontext.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Ollama must be running and the model pulled (`ollama pull llama3`).

---

## Configuration

All settings live in `.aicontext.env`:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` or `ollama` |
| `GROQ_API_KEY` | — | Your Groq Cloud API key (stored in `.aicontext.env`) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `MAX_FILE_SIZE_KB` | `100` | Skip files larger than this |
| `CONTEXT_FILE` | `context.json` | Output JSON path |
| `CONTEXT_MD_FILE` | `context.md` | Output Markdown path |
| `IGNORE_DIRS` | `node_modules,.git,…` | Comma-separated dirs to skip |

---

## Project structure

```
aicontext/
├── cli.py              # Typer commands (init, update, watch, show, clean)
├── orchestrator.py     # Main pipeline logic
├── config.py           # .env loader
├── analyzers/
│   ├── git_diff.py     # git diff / ls-files wrappers
│   └── file_collector.py  # file walker + safe reader
├── llm/
│   ├── prompt_builder.py  # prompt templates
│   └── summarizer.py      # Groq / Ollama callers + JSON parser
└── storage/
    └── context_writer.py  # load / merge / save context files

scripts/
└── update_context.py   # standalone runner (git hooks / CI)
```

---

## License

MIT
