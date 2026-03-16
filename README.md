# 🚀 git-assistant

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success) ![AI Powered](https://img.shields.io/badge/AI-powered-purple)

**AI‑powered Git commit and release workflow assistant.**

`git-assistant` analyzes your Git changes, generates high‑quality commit messages using AI, updates your `CHANGELOG.md` automatically, suggests when a new release may be appropriate, and pushes releases to remote repositories.

It is designed to streamline the **entire commit → changelog → release workflow** while staying fast, safe, and developer-friendly.
------------------------------------------------------------------------
## ✨ Features
- 🤖 **AI commit message generation**
- 🔢 Range selection support (`1-4,7,9`)
- ⚡ Fast workflow with `--all-files`
- 🧪 Safe testing with `--dry-run`
- 📝 **Automatic `CHANGELOG.md` updates**
  - The entry is derived from the generated commit message.
  - `CHANGELOG.md` is **automatically staged**.
  - When using `--dry-run`, the changelog is restored afterward.
- 💥 **AI-driven README updates in CLI workflow**
- 🏷 Version detection via:
  - Latest Git tag
  - Changelog fallback
- 🔌 Extensible AI provider architecture
- 📦 Release workflow execution
- 🚀 Automatic release creation and pushing to remote repositories
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
`git-assistant` automatically updates `CHANGELOG.md` before creating a commit. Key rules:
- The entry is derived from the generated commit message.
- `CHANGELOG.md` is **automatically staged**.
- When using `--dry-run`, the changelog is restored afterward.
- Pushes releases to remote repositories automatically after successful commits.
------------------------------------------------------------------------
## 🚀 Release Suggestions
After each successful commit, the tool analyzes `CHANGELOG.md` and suggests whether a release should occur. The tool also supports pushing releases to remote repositories automatically.
Two mechanisms are used:
### Heuristic evaluation
Rules based on changelog structure.
### AI evaluation
An optional AI analysis of the `Unreleased` section in `CHANGELOG.md`.
Version detection priority:
1️⃣ Latest Git tag
2️⃣ Latest version in `CHANGELOG.md`
3️⃣ Fallback version
------------------------------------------------------------------------
## 🛣 Roadmap
Planned features:
- 📦 Release workflow execution
- 🔄 Version bump automation
- 🌐 Additional AI providers
- 🧠 Smarter release intelligence
- 📣 GitHub release publishing
------------------------------------------------------------------------
## 📄 License
MIT
