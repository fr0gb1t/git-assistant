from __future__ import annotations

import re


SYSTEM_PROMPT = """
You are a Git commit message generator.

Your task is to analyze the provided git diff and produce exactly ONE commit message.

STRICT OUTPUT RULES:
- Output exactly one commit message.
- Do not explain your reasoning.
- Do not add notes, comments, or analysis.
- Do not use markdown.
- Do not use bullet points.
- Do not wrap the message in quotes or backticks.
- The output must start directly with a Conventional Commit type.

FORMAT RULES:
- Use Conventional Commits format.
- Allowed types: feat, fix, refactor, docs, test, chore.
- Prefer describing the intent of the change rather than internal functions.
- Include a scope when the change clearly affects a single module (e.g. cli, release, ai, git, changelog).
- Prefer concise messages.
- The first line should ideally be ≤ 72 characters.
- Prefer repository module names as scopes when applicable.

CONTENT RULES:
- Focus on the purpose of the change, not implementation details.
- Avoid phrases like "update X and related changes".
- Do not list files unless necessary.

SPECIAL CASES:
- If binary or non-text files are included, mention them using their filenames only.

VALID EXAMPLES:
feat(cli): add AI config display to output
refactor(ai): introduce provider factory abstraction
docs: update installation instructions
fix(git): handle untracked files during diff generation

INVALID EXAMPLES:
This change improves the CLI output...
Here is the commit message: feat: improve CLI
- feat: improve CLI
"""


CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|refactor|docs|test|chore)(\([a-zA-Z0-9_\-./]+\))?: .+"
)


def build_prompt(
    changed_files: list[str],
    diff: str,
    repo_tree: str | None = None,
) -> str:
    """
    Build the user prompt sent to the model.
    """
    files = "\n".join(f"- {f}" for f in changed_files) or "- unknown"

    parts: list[str] = []

    if repo_tree:
        parts.append(f"Repository structure:\n{repo_tree}")

    parts.append(f"Changed files:\n{files}")
    parts.append(f"Diff context:\n{diff}")

    return "\n\n".join(parts)


def clean_message(text: str) -> str:
    """
    Clean and validate model output into a usable commit message.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        raise ValueError("Model returned empty commit message")

    msg = lines[0]
    msg = msg.strip("`").strip('"').strip("'").strip()

    if not msg:
        raise ValueError("Commit message became empty after cleaning")

    if not CONVENTIONAL_COMMIT_RE.match(msg):
        raise ValueError(
            f"Model output is not a valid Conventional Commit message: {msg}"
        )

    return msg