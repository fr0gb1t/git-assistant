from __future__ import annotations

import argparse
import sys
from pathlib import Path

from git_assistant.ai.base import AIConfig
from git_assistant.commit.service import (
    CommitMessageGenerationError,
    CommitMessageResult,
    generate_commit_message,
)
from git_assistant.config.loader import ConfigError, load_app_config
from git_assistant.git.ops import (
    GitError,
    get_changed_files,
    get_repo_root,
    get_status_short,
    git_add_all,
    git_add_files,
    git_commit,
    is_git_repo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="git-assistant",
        description="Generate git commit messages using AI.",
    )

    parser.add_argument(
        "--provider",
        default=None,
        help="AI provider to use (example: ollama)",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Model name to use",
    )

    parser.add_argument(
        "--host",
        default=None,
        help="API host for the provider",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for provider and prompt diagnostics",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full workflow without creating a commit",
    )

    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Include all changed files without prompting for selection",
    )

    return parser.parse_args()


def build_ai_config(args: argparse.Namespace, cwd: Path) -> AIConfig:
    """
    Build the final AI config using:
    CLI args > config file > defaults
    """
    try:
        app_config = load_app_config(cwd)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)

    ai_config = app_config.ai

    if args.provider is not None:
        ai_config.provider = args.provider

    if args.model is not None:
        ai_config.model = args.model

    if args.host is not None:
        ai_config.host = args.host

    if args.timeout is not None:
        ai_config.timeout = args.timeout

    ai_config.debug = args.debug

    return ai_config


def print_ai_config(ai_config: AIConfig) -> None:
    print("🤖 AI configuration:")
    print(f"  - provider: {ai_config.provider}")
    print(f"  - model: {ai_config.model}")
    print(f"  - host: {ai_config.host}")
    print(f"  - timeout: {ai_config.timeout}s")


def print_changed_files(changed_files: list[str]) -> None:
    print("📂 Changed files:")
    for file_path in changed_files:
        print(f"  - {file_path}")


def print_numbered_files(changed_files: list[str]) -> None:
    print("📂 Changed files:")
    print("  [0] all")
    for index, file_path in enumerate(changed_files, start=1):
        print(f"  [{index}] {file_path}")


def print_context_summary(result: CommitMessageResult) -> None:
    print("🧠 Context summary:")
    print(f"  - staged changes: {'yes' if result.staged_included else 'no'}")
    print(f"  - unstaged changes: {'yes' if result.unstaged_included else 'no'}")
    print(f"  - truncated: {'yes' if result.was_truncated else 'no'}")


def parse_file_selection(user_input: str, max_index: int) -> list[int]:
    """
    Parse a comma-separated selection like '0' or '1,2,4'.
    """
    raw_parts = [part.strip() for part in user_input.split(",") if part.strip()]
    if not raw_parts:
        raise ValueError("No file selection provided.")

    indexes: list[int] = []

    for part in raw_parts:
        if not part.isdigit():
            raise ValueError(f"Invalid selection: {part}")

        index = int(part)

        if index == 0:
            if len(raw_parts) > 1:
                raise ValueError("Selection '0' (all) cannot be combined with others.")
            return [0]

        if index < 1 or index > max_index:
            raise ValueError(f"Selection out of range: {index}")

        if index not in indexes:
            indexes.append(index)

    return indexes


def prompt_file_selection(changed_files: list[str]) -> list[str] | None:
    """
    Prompt the user to choose which files to include.

    Returns:
        None -> include all changed files
        list[str] -> include only selected files
    """
    print()
    print("🗂 Select files to include:")
    print("Enter comma-separated numbers (example: 0 or 1,2)")
    print("Press Enter to cancel.")

    user_input = input("> ").strip()

    if not user_input:
        print("No files selected. Cancelled.")
        sys.exit(0)

    try:
        selected_indexes = parse_file_selection(user_input, len(changed_files))
    except ValueError as exc:
        print(f"Invalid selection: {exc}", file=sys.stderr)
        sys.exit(1)

    if selected_indexes == [0]:
        return None

    return [changed_files[index - 1] for index in selected_indexes]


def prompt_user_action() -> str:
    print("\n⚙ What do you want to do?")
    print("[1] Commit with this message")
    print("[2] Edit message")
    print("[3] Cancel")
    return input("> ").strip()


def main() -> None:
    args = parse_args()
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

    ai_config = build_ai_config(args, cwd)

    print(f"📦 Repository: {repo_root}")

    if args.all_files:
        print_changed_files(changed_files)
    else:
        print_numbered_files(changed_files)

    if ai_config.debug:
        print()
        print_ai_config(ai_config)

    print("\n✨ Generating commit message...")

    try:
        result = generate_commit_message(cwd, ai_config=ai_config)
    except CommitMessageGenerationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if ai_config.debug:
        print()
        print_context_summary(result)

    print("\n💬 Suggested commit:")
    print(result.message)

    action = prompt_user_action()

    if action == "1":
        final_message = result.message
    elif action == "2":
        edited_message = input("Enter commit message: ").strip()
        if not edited_message:
            print("Empty commit message. Cancelled.")
            sys.exit(1)
        final_message = edited_message
    else:
        print("Cancelled.")
        sys.exit(0)

    selected_files: list[str] | None

    if args.all_files:
        selected_files = None
    else:
        selected_files = prompt_file_selection(changed_files)

    if args.dry_run:
        print("\n🧪 Dry run enabled.")
        if selected_files is None:
            print("Files to include: all changed files")
        else:
            print("Files to include:")
            for file_path in selected_files:
                print(f"  - {file_path}")
        print("No commit was created.")
        print(f"Suggested final commit message: {final_message}")
        sys.exit(0)

    try:
        if selected_files is None:
            git_add_all(cwd)
        else:
            git_add_files(selected_files, cwd)

        commit_output = git_commit(final_message, cwd)
    except GitError as exc:
        print(f"Git error while creating commit: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n✅ Commit created successfully.\n")
    print(commit_output)


if __name__ == "__main__":
    main()