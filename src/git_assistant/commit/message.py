from __future__ import annotations


SYSTEM_PROMPT = """
You are a Git commit message generator.

Your task is to analyze the provided git diff and propose exactly ONE commit message.

Rules:

- Use Conventional Commits format.
- Output ONLY the commit message.
- Do NOT add explanations.
- Do NOT use markdown.
- Keep it concise and specific.
- Prefer these types: feat, fix, refactor, docs, test, chore.
- Maximum 72 characters if possible.
"""


def build_prompt(changed_files: list[str], diff: str) -> str:
    """
    Build the user prompt sent to the model.
    """
    files = "\n".join(f"- {f}" for f in changed_files) or "- unknown"

    return f"""
Analyze the following git changes and propose one commit message.

Changed files:
{files}

Git diff:
{diff}
"""


def clean_message(text: str) -> str:
    """
    Clean model output into a usable commit message.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        raise ValueError("Model returned empty commit message")

    msg = lines[0]
    msg = msg.strip("`").strip('"').strip("'").strip()

    if not msg:
        raise ValueError("Commit message became empty after cleaning")

    return msg