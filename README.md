# 🚀 git-assistant

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success) ![AI Powered](https://img.shields.io/badge/AI-powered-purple)

## AI‑powered Git workflow assistant for commit, changelog, README, and release management.

git-assistant analyzes your Git changes, generates commit messages with AI, updates `CHANGELOG.md`, evaluates README changes, suggests releases, and can publish commits or releases to the remote repository. It is designed to streamline the **commit → changelog → README → release** workflow while keeping Git operations explicit and recoverable.

------------------------------------------------------------------------
## ✅ What It Promises
- Generate Conventional Commit messages from the current Git diff
- Keep `CHANGELOG.md` aligned with the commit workflow
- Evaluate whether `README.md` should change and let you preview/edit it
- Suggest normal semantic-version releases and support a manual release mode
- Offer a safe `--dry-run` mode that simulates the workflow and restores managed files afterward

## ⚠️ What It Does Not Promise
- It does not replace Git knowledge or resolve merge conflicts for you
- It does not auto-publish `1.0.0` unless you explicitly choose that path
- It still depends on the configured AI provider being available and responsive
- Interactive mode remains the default; automation requires explicit flags

------------------------------------------------------------------------

## ⚡ Quick Usage
### Standard Workflow:
``` bash
    git-assistant
```

### Include All Files Automatically:
``` bash
    git-assistant --all-files
```

### Test Workflow Without Committing:
``` bash
    git-assistant --dry-run
```

### Enable Debug Diagnostics:
``` bash
    git-assistant --debug
```

### Manual Release Option for Specifying Version Directly:
``` bash
    git-assistant --release 1.0.0
```
or
``` bash
    git-assistant --release v1.0.0
```

### Non-Interactive Automation Mode:
``` bash
    git-assistant --non-interactive

------------------------------------------------------------------------
## ✨ Features
### Additional Enhancements:
- **First Stable Release Hint:** Provides a hint in the CLI for the first stable release.
- **Upstream Sync & Push Prompts:** Supports prompting for upstream synchronization and push operations.
- **Non-Interactive Mode:** Enables non-interactive mode for automation.
- **Repository Initialization Capability:** Adds capability to initialize repositories with necessary configurations.

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
### Runtime requirements
- Python 3.10+
- Git available in `PATH`
- An AI provider supported by the configured backend
- For the default setup: Ollama running locally and reachable at `http://127.0.0.1:11434`

### Development dependencies
``` bash
pip install -e ".[dev]"
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

### Automation strategy
By default, `git-assistant` is interactive and asks for confirmation before applying higher-impact workflow steps.

If you want a non-interactive run, use:
``` bash
git-assistant --non-interactive
```
In `--non-interactive` mode the tool uses automatic defaults:
- all selectable files are included
- the suggested commit message is accepted
- README updates are applied automatically
- a normal release is applied only when there is a clear consensus release candidate
- the first stable `1.0.0` hint remains a human decision and is not auto-applied
- the resulting commit is pushed automatically if no release is applied

------------------------------------------------------------------------
## 🛣️ Roadmap
Planned features:
- 🌐 Additional AI providers

------------------------------------------------------------------------
## 📜 LICENSE
MIT
