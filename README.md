# 🚀 git-assistant

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success) ![AI
Powered](https://img.shields.io/badge/AI-powered-purple)

**AI‑powered Git commit and release workflow assistant.**

`git-assistant` analyzes your Git changes, generates high‑quality commit
messages using AI, updates your `CHANGELOG.md` automatically, and
suggests when a new release may be appropriate.

It is designed to streamline the **entire commit → changelog → release
suggestion workflow** while staying fast, safe, and developer‑friendly.

------------------------------------------------------------------------

## ✨ Features

- 🤖 **AI commit message generation**
- 🗂 **Interactive file selection**
- 🔢 Range selection support (`1-4,7,9`)
- ⚡ Fast workflow with `--all-files`
- 🧪 Safe testing with `--dry-run`
- 🐞 Detailed diagnostics with `--debug`
- 🧠 Intelligent diff analysis with truncation protection
- 📄 Support for **untracked files**
- 🖼 Binary files included in commits without polluting prompts
- 🧱 Repository structure context improves commit scopes
- 📝 **Automatic `CHANGELOG.md` updates**
- 🚀 **Release suggestions**
  - rule‑based evaluation
    - AI‑based evaluation
- 🏷 Version detection via:
  - latest Git tag
  - changelog fallback
- ⚙ Configurable through `.git-assistant.toml`
- 🔌 Extensible AI provider architecture

------------------------------------------------------------------------

## 📦 Installation

Clone the repository and install in editable mode:

``` bash
pip install -e .
```

Run the tool:

``` bash
git-assistant
```

------------------------------------------------------------------------

## ⚡ Quick Usage

### Interactive commit workflow

``` bash
git-assistant
```

### Include all files automatically

``` bash
git-assistant --all-files
```

### Test workflow without committing

``` bash
git-assistant --dry-run
```

### Enable debug diagnostics

``` bash
git-assistant --debug
```

------------------------------------------------------------------------

## 📂 File Selection

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

Includes **all selectable files**.

------------------------------------------------------------------------

## 📝 CHANGELOG Behavior

`git-assistant` automatically updates `CHANGELOG.md` before creating a
commit.

Key rules:

- the entry is derived from the generated commit message
- `CHANGELOG.md` is **automatically staged**
- the file is **excluded from AI analysis**
- when using `--dry-run`, the changelog is restored afterward

------------------------------------------------------------------------

## 🚀 Release Suggestions

After each successful commit the tool analyzes `CHANGELOG.md` and
suggests whether a release should occur.

Two mechanisms are used:

### Heuristic evaluation

Rules based on changelog structure.

### AI evaluation

An optional AI analysis of the `Unreleased` section.

Version detection priority:

1️⃣ latest Git tag\
2️⃣ latest version in `CHANGELOG.md`\
3️⃣ fallback version

------------------------------------------------------------------------

## ⚙ Configuration

Create a `.git-assistant.toml` file:

``` toml
[ai]
provider = "ollama"
model = "qwen2.5:14b"
host = "http://127.0.0.1:11434"
timeout = 120
```

------------------------------------------------------------------------

## 🧠 AI Providers

Currently supported:

- **Ollama** (local LLMs)

Example model:

  qwen2.5:14b

The architecture is designed to support additional providers in the
future.

------------------------------------------------------------------------

## 🧪 Example Output

``` text
📦 Repository: /home/user/project

📂 Changed files:
  [0] all
  [1] src/cli.py
  [2] src/release/evaluator.py

🗂 Files selected for analysis:
- src/cli.py
- src/release/evaluator.py

✨ Generating commit message...

💬 Suggested commit:
feat(release): add changelog-based release suggestion functionality

⚙ What do you want to do?
[1] Commit with this message
[2] Edit message
[3] Regenerate message
[4] Cancel
```

------------------------------------------------------------------------

## 🛣 Roadmap

Planned features:

- 🏷 Automatic Git tag creation
- 📦 Release workflow execution
- 🔄 Version bump automation
- 🌐 Additional AI providers
- 🧠 Smarter release intelligence
- 📣 GitHub release publishing

------------------------------------------------------------------------

## 📄 License

MIT
