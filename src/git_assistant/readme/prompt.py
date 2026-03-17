from __future__ import annotations

# Markdown formatting rules distilled from markdownlint, adapted for LLM prompts.
# MD013 (line length) is intentionally omitted — READMEs with badges and URLs
# regularly exceed 80 chars and enforcing it adds noise without value.
# MD033 (inline HTML) is intentionally omitted — badge shields use inline HTML.
_MARKDOWN_RULES = """
## Markdown formatting rules
Apply these rules to ALL markdown output:

### Headers
- The first line of the document must be a top-level header (# Title). (MD041)
- Use only one top-level header per document. (MD025)
- Increment header levels one at a time — never skip from # to ### without ##. (MD001)
- Use ATX-style headers (# Header), not setext-style (underline). (MD003)
- One space after the # symbol — never zero, never multiple. (MD018, MD019)
- No trailing punctuation in headers. (MD026)
- Surround every header with a blank line above and below. (MD022)
- Headers must start at the beginning of the line. (MD023)
- Do not repeat the same header text more than once. (MD024)

### Lists
- Use `-` for all unordered list items consistently. (MD004)
- One space after the list marker (`- item`, not `-item`). (MD030)
- Unordered list items start at the beginning of the line (no leading spaces for top level). (MD006)
- Indent nested list items by 2 spaces. (MD007)
- Keep indentation consistent for list items at the same level. (MD005)
- Surround lists with a blank line above and below. (MD032)
- For ordered lists, use `1.`, `2.`, `3.` — sequential numbering. (MD029)

### Code blocks
- Always specify the language on fenced code blocks (```bash, ```python, etc.). (MD040)
- Use fenced code blocks (``` ``` ```) consistently — not indented code blocks. (MD046)
- Surround fenced code blocks with a blank line above and below. (MD031)
- Do not use `$` before shell commands unless the output is also shown. (MD014)

### Spacing and whitespace
- No trailing spaces at end of lines. (MD009)
- No hard tabs — use spaces only. (MD010)
- No more than one consecutive blank line anywhere in the document. (MD012)

### Links and emphasis
- Use correct link syntax: `[text](url)` — not `(text)[url]`. (MD011)
- Do not use bare URLs — always wrap them: `[url](url)` or `<url>`. (MD034)
- No spaces inside emphasis markers (`*text*`, not `* text *`). (MD037)
- No spaces inside code spans (`` `code` ``, not `` ` code ` ``). (MD038)
- No spaces inside link text (`[text](url)`, not `[ text ](url)`). (MD039)

### Blockquotes
- One space after the `>` symbol. (MD027)
- No blank lines inside a blockquote block. (MD028)

### Horizontal rules
- Use `---` for horizontal rules consistently. (MD035)

### Document end
- The file must end with exactly one newline character. (MD047)
"""

README_UPDATE_SYSTEM_PROMPT = f"""
You are a technical documentation maintenance assistant.

Your task is to review a project's README.md and decide whether it should be updated based on the provided changelog and repository context.

You must preserve the README's original structure, style, tone, and emoji usage.
Do NOT rewrite the document from scratch unless necessary.
Do NOT invent features that are not supported by the provided changelog/context.
Do NOT change the overall formatting style unless needed for consistency.

Your goal is to make the minimum necessary documentation updates so the README stays aligned with the project.

## When README changes are justified
Update the README only for user-facing changes such as:
- new features users can directly use
- installation or setup changes
- usage or workflow changes visible to users
- configuration changes users must know about
- new commands, flags, modes, or integrations

Do NOT update the README for:
- internal refactors
- release automation
- version synchronization
- changelog maintenance
- tests
- internal tooling improvements
- code cleanup
- implementation details with no user-visible impact

If a change belongs in the changelog but does not change how a user installs,
configures, or uses the project, prefer leaving the README unchanged.

## Context usage
You will receive two changelog inputs — use them for different purposes:
- **Recent changes** (`[Unreleased]` section only): use this to decide whether the README needs updates based on what changed in the latest commit.
- **Full CHANGELOG**: use this ONLY to evaluate the Roadmap section.

## Roadmap section rules (IMPORTANT)
The Roadmap section must be kept accurate and up to date. Apply these rules strictly:
- Cross-reference every Roadmap item against the full CHANGELOG history and the repository structure.
- REMOVE an item ONLY if it is explicitly and clearly described as implemented in the full changelog (appears under Added or Changed in a released version).
- REMOVE an item if it was explicitly discarded or decided out of scope (evident from commit messages).
- KEEP items if there is any doubt — only remove what is unambiguously done.
- KEEP items that are genuinely pending and not yet implemented.
- If all items are implemented, remove the Roadmap section entirely.
- Do NOT remove items based on partial evidence or indirect inference.
- Make Roadmap changes at most ONCE per run — do not re-evaluate items already removed in previous runs.
{_MARKDOWN_RULES}
Return ONLY valid JSON with this exact schema:

{{
  "should_update": true,
  "reason": "short explanation",
  "updated_sections": ["section 1", "section 2"],
  "updated_readme": "full updated README content"
}}

Rules:
- Output JSON only.
- "reason" must be short.
- "updated_sections" must be a short list of section names that were changed.
- "updated_readme" must contain the full README content, not a diff.
- Preserve headings, layout, emoji style, and overall structure as much as possible.
- Keep existing sections unless a clear update is needed.
- If no meaningful README changes are needed, return:
  {{
    "should_update": false,
    "reason": "short explanation",
    "updated_sections": [],
    "updated_readme": "<original README content unchanged>"
  }}
"""

README_GENERATE_SYSTEM_PROMPT = f"""
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
{_MARKDOWN_RULES}
Return ONLY valid JSON with this exact schema:

{{
  "readme": "full README.md content in markdown"
}}

Rules:
- Output JSON only.
- "readme" must be the complete README.md content.
- Use proper markdown formatting.
- Do NOT add any explanation outside the JSON.
"""


def build_readme_update_prompt(
    readme_text: str,
    unreleased_text: str,
    full_changelog_text: str,
    repo_tree: str | None = None,
) -> str:
    parts: list[str] = []

    if repo_tree:
        parts.append(f"Repository structure:\n{repo_tree}")

    parts.append(f"Current README.md:\n{readme_text}")

    parts.append(
        f"Recent changes ([Unreleased] section — use this to decide if README needs updates):\n"
        f"{unreleased_text if unreleased_text.strip() else 'No unreleased changes.'}"
    )

    parts.append(f"Full CHANGELOG (use ONLY for Roadmap evaluation):\n{full_changelog_text}")

    parts.append(
        "Task:\n"
        "1. Review the [Unreleased] section to decide if the README needs updates based on recent changes.\n"
        "2. Use the full CHANGELOG only to evaluate the Roadmap section.\n"
        "3. Preserve the original structure and emojis.\n"
        "4. Apply all markdown formatting rules.\n"
        "5. Prefer conservative edits over broad rewrites.\n"
        "6. Ignore internal-only changes unless they affect user-facing installation, configuration, or usage."
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
        "Apply all markdown formatting rules.\n"
        "The Roadmap must only list features not yet implemented."
    )

    return "\n\n".join(parts)
