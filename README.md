# ⚡ aicontext

> Keep your codebase in LLM memory — automatically.

Stop pasting your entire codebase into ChatGPT.
**aicontext** continuously maintains a compressed, up-to-date context of your project — so you can work with LLMs efficiently and at low cost.

---

## 🤔 Why aicontext?

Working with LLMs on real projects is painful:

* ❌ Repeatedly copying large chunks of code
* ❌ Hitting token limits
* ❌ Context becoming outdated after every change

**aicontext solves this by:**

* ✅ Maintaining a compressed, always-updated project context
* ✅ Sending only changed files to the LLM
* ✅ Reducing token usage drastically
* ✅ Integrating directly into your git workflow

---

## 🔥 Key Idea

```
git commit → post-commit hook → aicontext update
                                      │
                              git diff HEAD~1..HEAD
                                      │
                              read changed files
                                      │
                              call LLM (Groq / Ollama)
                                      │
                         merge into context.json + context.md
```

🔥 **Only changed files are sent to the LLM — keeping costs extremely low.**

---

## ⚡ Demo

```bash
# Make changes
git commit -m "add auth module"

# aicontext runs automatically
✔ Updated context.md (3 files changed)

# View context
aicontext show
```

---

## 🚀 Quick Start

### 1. Install globally

```bash
git clone <repo-url> ~/tools/aicontext
cd ~/tools/aicontext
pip install -e .

# Optional (file watching)
pip install -e ".[watch]"

# Verify
aicontext --help
```

> `aicontext` is now available globally like `git` or `pip`.

---

### 2. Initialize in any project

```bash
cd /path/to/your-project
aicontext init
```

Edit `.aicontext.env`:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq
```

---

### 3. Generate initial context

```bash
aicontext update --scan
```

After this, every `git commit` triggers automatic updates.

---

## 📁 What gets added to your project

```
your-project/
  .aicontext.env          # API config (git-ignored)
  .git/hooks/post-commit  # automation hook
  context.json            # machine-readable (commit this)
  context.md              # human-readable (commit this)
```

✔ Your project code is untouched
✔ Tool source is never copied into your project

---

## 🧠 Using with LLMs

### Option 1: Manual prompt

```
<context>
[paste context.md here]
</context>

Now help me modify the auth module...
```

---

### Option 2: Programmatic

```python
import json

ctx = json.load(open("context.json"))
system_prompt = f"""
Project: {ctx['summary']}
Modules: {json.dumps(ctx['modules'])}
"""
```

---

## 🧰 Commands

### `aicontext init`

Initialize config + git hook

```bash
aicontext init
aicontext init --force
```

---

### `aicontext update`

Update context

```bash
aicontext update
aicontext update --scan
aicontext update -v
```

---

### `aicontext watch`

Auto-update on file save

```bash
aicontext watch
aicontext watch --debounce 5
```

---

### `aicontext show`

View current context

```bash
aicontext show
aicontext show --format json
```

---

### `aicontext clean`

Remove generated files

```bash
aicontext clean
aicontext clean -y
aicontext clean --all
```

---

### `aicontext delete`

Remove everything from current project

```bash
aicontext delete
aicontext delete -y
```

---

## 🧩 Use Cases

* 🧠 Feed structured context into ChatGPT / Claude
* 🛠 Build AI-powered dev tools
* 🔍 Understand large codebases instantly
* 🤖 Automate code review workflows
* ⚡ Reduce LLM token usage in production systems

---

## 🧠 Local LLM (Ollama)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Make sure Ollama is running:

```bash
ollama pull llama3
```

---

## ⚙️ Configuration

All settings are in `.aicontext.env`:

| Variable         | Default                 | Description   |
| ---------------- | ----------------------- | ------------- |
| LLM_PROVIDER     | groq                    | groq / ollama |
| GROQ_API_KEY     | —                       | API key       |
| GROQ_MODEL       | llama-3.3-70b-versatile | Model         |
| OLLAMA_BASE_URL  | http://localhost:11434  | Local server  |
| OLLAMA_MODEL     | llama3                  | Local model   |
| MAX_FILE_SIZE_KB | 100                     | File limit    |
| CONTEXT_FILE     | context.json            | Output JSON   |
| CONTEXT_MD_FILE  | context.md              | Output MD     |
| IGNORE_DIRS      | node_modules,.git       | Skip dirs     |

---

## 🏗 Project Structure

```
aicontext/
├── cli.py
├── orchestrator.py
├── config.py
├── analyzers/
├── llm/
├── storage/
└── scripts/
```

---

## 🆚 vs Manual LLM Usage

| Approach        | Token Cost | Effort | Accuracy |
| --------------- | ---------- | ------ | -------- |
| Copy-paste code | High       | High   | Medium   |
| aicontext       | Low        | Low    | High     |

---

## 📄 License

MIT
