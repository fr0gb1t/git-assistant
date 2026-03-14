![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success)

# 🚀 git-assistant

**AI-powered Git commit generator with smart file selection.**

`git-assistant` analyzes your Git changes and generates a meaningful commit message using a local AI model (or other providers in the future).

It also lets you **select which files to include in the commit**, making sure the generated message actually matches what you commit.

---

## ✨ Features

* 🤖 Generate commit messages using **AI**
* 🗂 **Interactive file selection**
* 🔢 Support for **ranges and combinations** (`1-4,7,9`)
* ⚡ Fast workflow with `--all-files`
* 🧪 Safe testing with `--dry-run`
* 🧠 Diff analysis with automatic truncation
* ⚙️ Configurable via `.git-assistant.toml`
* 🐞 Debug mode for diagnostics
* 🔌 Extensible AI provider architecture

---

## 📦 Example

Run inside any Git repository:

```bash
git-assistant
```

Example output:

```bash
📦 Repository: /home/user/project

📂 Changed files:
  [0] all
  [1] src/cli.py
  [2] src/service.py
  [3] src/git/ops.py

🗂 Select files to include:
Specify selection using comma-separated numbers, hyphen ranges, or a combination of both
(e.g. 1,2,5-7,9)

> 1,3

✨ Generating commit message...

💬 Suggested commit:
refactor: improve file selection and commit generation workflow

⚙ What do you want to do?
[1] Commit with this message
[2] Edit message
[3] Regenerate message
[4] Cancel
```

---

## ⚡ Quick usage

### Generate a commit interactively

```bash
git-assistant
```

### Skip file selection and include everything

```bash
git-assistant --all-files
```

### Test without committing

```bash
git-assistant --dry-run
```

### Enable debug mode

```bash
git-assistant --debug
```

---

## ⚙️ Configuration

You can configure the AI provider using a `.git-assistant.toml` file.

Example:

```toml
[ai]
provider = "ollama"
model = "qwen2.5:14b"
host = "http://127.0.0.1:11434"
timeout = 120
```

---

## 🧠 AI Providers

Currently supported:

* **Ollama** (local models)

Example model:

```text
qwen2.5:14b
```

The architecture is designed to support additional providers in the future.

---

## 🗂 File selection

You can select files using:

```text
1,2,4
```

Ranges:

```text
1-4
```

Or combinations:

```text
1-4,7,9
```

Special option:

```text
0
```

Includes **all changed files**.

---

## 🧪 Development

Clone the repository and install in editable mode:

```bash
pip install -e .
```

Run the tool:

```bash
git-assistant
```

---

## 🛣 Roadmap

Planned features:

* 📜 Automatic **CHANGELOG generation**
* 🏷 Version management
* 🚀 Tag and release helpers
* 🌐 Additional AI providers
* 🧠 Improved diff context analysis

---

## 📄 License

MIT
