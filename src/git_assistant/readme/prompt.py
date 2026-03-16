from __future__ import annotations

README_UPDATE_SYSTEM_PROMPT = """
You are a technical documentation maintenance assistant.

Your task is to review a project's README.md and decide whether it should be updated based on the provided changelog and repository context.

You must preserve the README's original structure, style, tone, and emoji usage.
Do NOT rewrite the document from scratch unless necessary.
Do NOT invent features that are not supported by the provided changelog/context.
Do NOT change the overall formatting style unless needed for consistency.

Your goal is to make the minimum necessary documentation updates so the README stays aligned with the project.

## Roadmap section rules (IMPORTANT)
The Roadmap section must be kept accurate and up to date. Apply these rules strictly:
- Cross-reference every Roadmap item against the full CHANGELOG.md history and the repository structure.
- REMOVE any item that is clearly already implemented (present in the changelog as Added/Changed or visible in the codebase).
- REMOVE any item that was explicitly discarded or decided out of scope (if evident from the changelog or commit messages).
- KEEP only items that are genuinely pending and not yet implemented.
- If all items are implemented, remove the Roadmap section entirely or replace it with a note that the planned features are complete.
- Do NOT keep implemented items in the Roadmap just to preserve existing content.

Return ONLY valid JSON with this exact schema:

{
  "should_update": true,
  "reason": "short explanation",
  "updated_sections": ["section 1", "section 2"],
  "updated_readme": "full updated README content"
}

Rules:
- Output JSON only.
- "reason" must be short.
- "updated_sections" must be a short list of section names that were changed.
- "updated_readme" must contain the full README content, not a diff.
- Preserve headings, layout, emoji style, and overall structure as much as possible.
- Keep existing sections unless a clear update is needed.
- If no meaningful README changes are needed, return:
  {
    "should_update": false,
    "reason": "short explanation",
    "updated_sections": [],
    "updated_readme": "<original README content unchanged>"
  }
"""

README_GENERATE_SYSTEM_PROMPT = """
You are a technical documentation assistant specialized in creating initial README files for software projects.

Your task is to generate a complete and well-structured README.md based on the provided repository context: its structure, source code, and changelog.

Guidelines:
- Infer the project's purpose, features, and usage from the codebase and changelog.
- Use emojis for section headers to make the document visually friendly.
- Use a clean, developer-focused tone.
- Do NOT invent features or configuration options that are not evident from the provided context.
- For sections where you lack enough information (e.g. detailed configuration, advanced usage), include the section header and a brief placeholder or the best available information — do NOT omit the section entirely.
- The Roadmap section should only include features that are genuinely pending (not in the changelog and not visible in the codebase).

Required sections (include all, even if partially filled):
1. Project title + badges + short description
2. ✨ Features
3. 📦 Installation
4. ⚡ Usage
5. ⚙ Configuration (if applicable)
6. 🛣 Roadmap (pending features only; omit if nothing is pending)
7. 📄 License

Return ONLY valid JSON with this exact schema:

{
  "readme": "full README.md content in markdown"
}

Rules:
- Output JSON only.
- "readme" must be the complete README.md content.
- Use proper markdown formatting.
- Do NOT add any explanation outside the JSON.
"""


def build_readme_update_prompt(
    readme_text: str,
    changelog_text: str,
    repo_tree: str | None = None,
) -> str:
    parts: list[str] = []

    if repo_tree:
        parts.append(f"Repository structure:\n{repo_tree}")

    parts.append(f"Current README.md:\n{readme_text}")
    parts.append(f"CHANGELOG.md:\n{changelog_text}")

    parts.append(
        "Task:\n"
        "Review whether README.md needs updates based on the changelog and repository structure.\n"
        "Preserve the original structure and emojis.\n"
        "Only make documentation updates that are justified by the changelog or codebase.\n"
        "Pay special attention to the Roadmap section: remove any items already implemented.\n"
        "Prefer conservative edits over broad rewrites."
    )

    return "\n\n".join(parts)


def build_readme_generate_prompt(
    changelog_text: str,
    repo_tree: str | None = None,
    source_context: str | None = None,
) -> str:
    parts: list[str] = []

    if repo_tree:
        parts.append(f"Repository structure:\n{repo_tree}")

    if source_context:
        parts.append(f"Source code context:\n{source_context}")

    parts.append(f"CHANGELOG.md:\n{changelog_text}")

    parts.append(
        "Task:\n"
        "Generate an initial README.md for this project.\n"
        "Base all content strictly on the repository structure, source code, and changelog.\n"
        "Include all required sections. Use placeholders for sections with insufficient context.\n"
        "The Roadmap must only list features not yet implemented."
    )

    return "\n\n".join(parts)