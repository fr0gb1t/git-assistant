# 🚀 git-assistant

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success) ![AI Powered](https://img.shields.io/badge/AI-powered-purple)

## AI‑powered Git commit and release workflow assistant.

`git-assistant` analyzes your Git changes, generates high‑quality commit messages using AI, updates your `CHANGELOG.md` automatically, suggests when a new release may be appropriate, and pushes releases to remote repositories. It is designed to streamline the **entire commit → changelog → release workflow** while staying fast, safe, and developer-friendly.

------------------------------------------------------------------------
## ✨ Features
- 🤖 **AI commit message generation**
  - Readline support for interactive editing
  - AI-generated first stable release hint in CLI
- 🔢 Range selection support (`1-4,7,9`)
- ⚡ Fast workflow with `--all-files`
- 🧪 Safe testing with `--dry-run`
- 👀 Preview pair functionality for concurrent file viewing
- 📝 **First stable release hint** in CLI
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

### Manual release option for specifying version directly
``` bash
git-assistant --release 1.0.0
```
or
``` bash
git-assistant --release v1.0.0
```

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
## 📂 File Selection
You can select files using:
```text
    1,2,4
```
```text
Ranges:
    1-4
```
or combinations:
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

`git-assistant` automatically updates `CHANGELOG.md` before creating a commit. Key rules:
- The entry is derived from the generated commit message.
- `CHANGELOG.md` is **automatically staged**.
- When using `--dry-run`, the changelog is restored afterward.
- Synchronizes version numbers across `pyproject.toml` and package init file.
------------------------------------------------------------------------
## 🚀 Release Suggestions
After each successful commit, the tool analyzes `CHANGELOG.md` and suggests whether a release should occur. The tool also supports pushing releases to remote repositories automatically. Two mechanisms are used:

### Heuristic evaluation
Rules based on changelog structure.

### AI evaluation
An optional AI analysis of the `Unreleased` section in `CHANGELOG.md`.

Version detection priority:
- 1️⃣ Latest Git tag
- 2️⃣ Latest version in `CHANGELOG.md`
- 3️⃣ Fallback version
------------------------------------------------------------------------
## 🛣️ Roadmap
Planned features:
- 🌐 Additional AI providers
------------------------------------------------------------------------
## 📜 LICENSE
MIT
