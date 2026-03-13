from __future__ import annotations

import sys
from pathlib import Path

from git_assistant.ai.ollama import generate
from git_assistant.commit.message import (
    SYSTEM_PROMPT,
    build_prompt,
    clean_message,
)
from git_assistant.git.ops import (
    GitError,
    get_changed_files,
    get_repo_root,
    get_status_short,
    get_unstaged_diff,
    git_add_all,
    git_commit,
    is_git_repo,
)


def prompt_user_action() -> str:
    """
    Ask the user what to do with the suggested commit message.
    """
    print("\nWhat do you want to do?")
    print("[1] Commit with this message")
    print("[2] Edit message")
    print("[3] Cancel")

    return input("> ").strip()


def main() -> None:
    cwd = Path.cwd()

    if not is_git_repo(cwd):
        print("Error: not inside a Git repository.", file=sys.stderr)
        sys.exit(1)

    try:
        repo_root = get_repo_root(cwd)
        status = get_status_short(cwd)
        changed_files = get_changed_files(cwd)
    except GitError as exc:
        print(f"Git error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not status.strip():
        print("No changes detected.")
        sys.exit(0)

    print(f"Repository: {repo_root}")
    print("Changed files:")

    for file_path in changed_files:
        print(f"- {file_path}")

    try:
        diff = get_unstaged_diff(cwd)
    except GitError as exc:
        print(f"Git error while reading diff: {exc}", file=sys.stderr)
        sys.exit(1)

    if not diff.strip():
        print("Diff is empty (maybe everything is staged).")
        sys.exit(1)

    user_prompt = build_prompt(changed_files, diff)

    print("\nGenerating commit message with Ollama...\n")

    try:
        raw = generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        suggested_message = clean_message(raw)
    except Exception as exc:
        print(f"Ollama error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Suggested commit message:\n")
    print(suggested_message)

    action = prompt_user_action()

    if action == "1":
        final_message = suggested_message
    elif action == "2":
        edited_message = input("Enter commit message: ").strip()
        if not edited_message:
            print("Empty commit message. Cancelled.")
            sys.exit(1)
        final_message = edited_message
    else:
        print("Cancelled.")
        sys.exit(0)

    try:
        git_add_all(cwd)
        commit_output = git_commit(final_message, cwd)
    except GitError as exc:
        print(f"Git error while creating commit: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\nCommit created successfully.\n")
    print(commit_output)