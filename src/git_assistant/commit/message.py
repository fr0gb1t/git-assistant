from __future__ import annotations

import re


SYSTEM_PROMPT = """
You are a Git commit message generator.

Your task is to analyze the provided git diff and produce exactly ONE git commit message.

STRICT OUTPUT RULES:
- Output exactly one single-line commit message.
- Do not explain your reasoning.
- Do not add notes, comments, or analysis.
- Do not use markdown.
- Do not use bullet points.
- Do not wrap the message in quotes or backticks.
- The output must start directly with a Conventional Commit type.

FORMAT RULES:
- Use Conventional Commits format.
- Allowed types: feat, fix, refactor, docs, test, chore.
- Prefer a concise message.
- Maximum 72 characters if possible.

VALID EXAMPLES:
feat(cli): add AI config display to output
refactor(ai): abstract provider factory
docs: update installation instructions

INVALID EXAMPLES:
This change improves the CLI output...
Here is the commit message: feat: improve CLI
- feat: improve CLI
"""


CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|refactor|docs|test|chore)(\([a-zA-Z0-9_\-./]+\))?: .+"
)


def build_prompt(changed_files: list[str], diff: str) -> str:
    """
    Build the user prompt sent to the model.
    """
    files = "\n".join(f"- {f}" for f in changed_files) or "- unknown"

    return f"""
Analyze the following git repository changes and produce exactly ONE commit message.

Changed files:
{files}

Diff context:
{diff}
"""


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