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

    return ai_config


def print_header(title: str) -> None:
    print(f"\n=== {title} ===")


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


def print_context_summary(result: CommitMessageResult) -> None:
    print("🧠 Context sent to AI provider:")
    print(f"  - staged changes: {'yes' if result.staged_included else 'no'}")
    print(f"  - unstaged changes: {'yes' if result.unstaged_included else 'no'}")
    print(f"  - truncated: {'yes' if result.was_truncated else 'no'}")


def prompt_user_action() -> str:
    print("\n⚙️ What do you want to do?")
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

    print_header("Repository")
    print(f"📦 {repo_root}")

    print_header("Changes")
    print_changed_files(changed_files)

    ai_config = build_ai_config(args, cwd)

    print_header("AI Setup")
    print_ai_config(ai_config)

    print_header("Generation")
    print(f"✨ Generating commit message using {ai_config.provider}...")

    try:
        result = generate_commit_message(cwd, ai_config=ai_config)
    except CommitMessageGenerationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print()
    print_context_summary(result)

    print_header("Suggested Commit")
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

    try:
        git_add_all(cwd)
        commit_output = git_commit(final_message, cwd)
    except GitError as exc:
        print(f"Git error while creating commit: {exc}", file=sys.stderr)
        sys.exit(1)

    print_header("Result")
    print("✅ Commit created successfully.\n")
    print(commit_output)