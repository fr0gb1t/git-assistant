from __future__ import annotations

import argparse
import sys
from pathlib import Path

from git_assistant.ai.base import AIConfig, AIProviderError
from git_assistant.changelog.entry import build_changelog_entry
from git_assistant.changelog.writer import append_to_unreleased, get_changelog_path
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
    git_add_files,
    git_commit,
    is_git_repo,
)
from git_assistant.release.ai_evaluator import evaluate_release_with_ai
from git_assistant.release.decision import decide_auto_release
from git_assistant.release.evaluator import evaluate_release
from git_assistant.release.executor import create_release_tag, prepare_release_changelog


CHANGELOG_FILE = "CHANGELOG.md"
AUTO_INCLUDED_FILES = [CHANGELOG_FILE]


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


def snapshot_auto_included_files(cwd: Path) -> dict[str, str | None]:
    """
    Snapshot the current state of auto-included files.

    Returns:
        dict[path, content_or_none]
        - None means the file did not exist.
    """
    snapshot: dict[str, str | None] = {}

    for file_path in AUTO_INCLUDED_FILES:
        abs_path = cwd / file_path
        if abs_path.exists():
            snapshot[file_path] = abs_path.read_text(encoding="utf-8")
        else:
            snapshot[file_path] = None

    return snapshot


def restore_auto_included_files(cwd: Path, snapshot: dict[str, str | None]) -> None:
    """
    Restore auto-included files to their original state.
    """
    for file_path, original_content in snapshot.items():
        abs_path = cwd / file_path

        if original_content is None:
            if abs_path.exists():
                abs_path.unlink()
        else:
            abs_path.write_text(original_content, encoding="utf-8")


def filter_selectable_files(changed_files: list[str]) -> list[str]:
    """
    Return only files that should be visible/selectable to the user.
    """
    auto_files = set(AUTO_INCLUDED_FILES)
    return [file_path for file_path in changed_files if file_path not in auto_files]


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
    print(f"  - untracked files: {'yes' if result.untracked_included else 'no'}")
    print(f"  - truncated: {'yes' if result.was_truncated else 'no'}")


def parse_file_selection(user_input: str, max_index: int) -> list[int]:
    """
    Parse a selection string like:
    - '0'
    - '1,2,4'
    - '1-4'
    - '1-4,7,9-11'

    Returns a sorted list of unique indexes.
    """
    raw_parts = [part.strip() for part in user_input.split(",") if part.strip()]
    if not raw_parts:
        raise ValueError("No file selection provided.")

    selected: set[int] = set()

    for part in raw_parts:
        if part == "0":
            if len(raw_parts) > 1:
                raise ValueError("Selection '0' (all) cannot be combined with others.")
            return [0]

        if "-" in part:
            range_parts = [p.strip() for p in part.split("-", 1)]

            if (
                len(range_parts) != 2
                or not range_parts[0].isdigit()
                or not range_parts[1].isdigit()
            ):
                raise ValueError(f"Invalid range selection: {part}")

            start = int(range_parts[0])
            end = int(range_parts[1])

            if start > end:
                raise ValueError(f"Invalid range (start > end): {part}")

            if start < 1 or end > max_index:
                raise ValueError(f"Range out of bounds: {part}")

            for index in range(start, end + 1):
                selected.add(index)

        else:
            if not part.isdigit():
                raise ValueError(f"Invalid selection: {part}")

            index = int(part)

            if index < 1 or index > max_index:
                raise ValueError(f"Selection out of range: {index}")

            selected.add(index)

    return sorted(selected)


def prompt_file_selection(changed_files: list[str]) -> list[str] | None:
    """
    Prompt the user to choose which files to include.

    Returns:
        None -> include all changed files
        list[str] -> include only selected files
    """
    print()
    print("🗂 Select files to include:")
    print(
        "Specify selection using comma-separated numbers, hyphen ranges, or a combination (e.g. 1,2,5-7,9)"
    )
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


def print_selected_files(selected_files: list[str]) -> None:
    print("🗂 Files selected for analysis:")
    for file_path in selected_files:
        print(f"  - {file_path}")


def prompt_user_action() -> str:
    print("\n⚙ What do you want to do?")
    print("[1] Commit with this message")
    print("[2] Edit message")
    print("[3] Regenerate message")
    print("[4] Cancel")
    return input("> ").strip()


def prompt_auto_release(version: str, reason: str) -> bool:
    print(f"\n🏷 Release candidate detected: v{version}")
    print(reason)
    print("Apply release now?")
    print("[1] Yes")
    print("[2] No")

    choice = input("> ").strip()
    return choice == "1"


def generate_and_display_commit_message(
    cwd: Path,
    ai_config: AIConfig,
    selected_files: list[str] | None,
) -> CommitMessageResult:
    print("\n✨ Generating commit message...")

    try:
        result = generate_commit_message(
            cwd,
            ai_config=ai_config,
            selected_files=selected_files,
        )
    except CommitMessageGenerationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if ai_config.debug:
        print()
        print_context_summary(result)

    print("\n💬 Suggested commit:")
    print(result.message)

    return result


def update_changelog(cwd: Path, commit_message: str) -> None:
    """
    Update CHANGELOG.md in the [Unreleased] section before committing.
    """
    try:
        entry = build_changelog_entry(commit_message)
        changelog_path = append_to_unreleased(cwd, entry)
    except ValueError as exc:
        print(f"Warning: changelog not updated: {exc}", file=sys.stderr)
        return
    except OSError as exc:
        print(f"Warning: failed to update CHANGELOG.md: {exc}", file=sys.stderr)
        return

    print(f"📝 CHANGELOG updated: {changelog_path.name}")


def get_auto_release_decision(
    cwd: Path,
    ai_config: AIConfig,
):
    changelog_path = get_changelog_path(cwd)
    heuristic = evaluate_release(cwd, changelog_path)

    try:
        ai = evaluate_release_with_ai(changelog_path, ai_config)
    except (AIProviderError, ValueError) as exc:
        if ai_config.debug:
            print(f"\n[DEBUG] AI release evaluation failed during auto-release check: {exc}")
        ai = None

    return heuristic, ai, decide_auto_release(heuristic, ai)

def print_release_evaluation_summary(
    heuristic_suggestion,
    ai_suggestion,
    release_decision,
) -> None:
    """
    Print a compact summary of release evaluation results.
    """
    heuristic_type = (
        heuristic_suggestion.release_type
        if heuristic_suggestion.should_release and heuristic_suggestion.release_type
        else "none"
    )

    if ai_suggestion is None:
        ai_type = "unavailable"
    else:
        ai_type = (
            ai_suggestion.release_type
            if ai_suggestion.should_release and ai_suggestion.release_type
            else "none"
        )

    consensus = "release candidate" if release_decision.should_apply else "no automatic release"

    print("\n📊 Release evaluation summary:")
    print(f"- heuristic: {heuristic_type}")
    print(f"- AI: {ai_type}")
    print(f"- consensus: {consensus}")

def print_heuristic_release_suggestion_from_result(suggestion, debug: bool = False) -> None:
    """
    Print a previously computed heuristic release suggestion.
    """
    if not debug and not suggestion.should_release:
        return

    if debug:
        print("\n🚀 Release suggestion:")
        print(f"  - should release: {'yes' if suggestion.should_release else 'no'}")
        if suggestion.release_type is not None:
            print(f"  - type: {suggestion.release_type}")
        if suggestion.next_version is not None:
            print(f"  - next version: {suggestion.next_version}")
        print(f"  - reason: {suggestion.reason}")
        return

    print(
        f"\n🚀 Suggested release: {suggestion.release_type} → {suggestion.next_version}"
    )
    print(f"Reason: {suggestion.reason}")


def print_ai_release_suggestion_from_result(suggestion, debug: bool = False) -> None:
    """
    Print a previously computed AI release suggestion.
    """
    if suggestion is None:
        if debug:
            print("\n[DEBUG] AI release suggestion unavailable.")
        return

    if not debug and not suggestion.should_release:
        return

    if debug:
        print("\n🤖 AI release suggestion:")
        print(f"  - should release: {'yes' if suggestion.should_release else 'no'}")
        if suggestion.release_type is not None:
            print(f"  - type: {suggestion.release_type}")
        if suggestion.next_version is not None:
            print(f"  - next version: {suggestion.next_version}")
        print(f"  - reason: {suggestion.reason}")
        return

    print(
        f"\n🤖 AI suggested release: {suggestion.release_type} → {suggestion.next_version}"
    )
    print(f"Reason: {suggestion.reason}")


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

    selectable_files = filter_selectable_files(changed_files)

    if not selectable_files:
        print("No selectable user files detected.")
        print("Only auto-included files are currently modified.")
        sys.exit(0)

    ai_config = build_ai_config(args, cwd)

    print(f"📦 Repository: {repo_root}")

    if args.all_files:
        print_changed_files(selectable_files)
        selected_files = list(selectable_files)
    else:
        print_numbered_files(selectable_files)
        prompted_selection = prompt_file_selection(selectable_files)
        selected_files = list(selectable_files) if prompted_selection is None else prompted_selection

    print()
    print_selected_files(selected_files)

    if ai_config.debug:
        print()
        print_ai_config(ai_config)

    while True:
        result = generate_and_display_commit_message(
            cwd=cwd,
            ai_config=ai_config,
            selected_files=selected_files,
        )

        action = prompt_user_action()

        if action == "1":
            final_message = result.message
            break
        elif action == "2":
            edited_message = input("Enter commit message: ").strip()
            if not edited_message:
                print("Empty commit message. Cancelled.")
                sys.exit(1)
            final_message = edited_message
            break
        elif action == "3":
            print("\n🔁 Regenerating commit message...")
            continue
        else:
            print("Cancelled.")
            sys.exit(0)

    auto_files_snapshot = snapshot_auto_included_files(cwd)

    update_changelog(cwd, final_message)

    heuristic_suggestion, ai_suggestion, release_decision = get_auto_release_decision(
        cwd,
        ai_config,
    )

    auto_release_version = None

    if (
        not args.dry_run
        and release_decision.should_apply
        and release_decision.next_version is not None
    ):
        if prompt_auto_release(
            version=release_decision.next_version,
            reason=release_decision.reason,
        ):
            try:
                prepare_release_changelog(cwd, version=release_decision.next_version)
            except OSError as exc:
                print(f"Warning: failed to prepare release changelog: {exc}", file=sys.stderr)
            else:
                print(f"🏷 Auto-release prepared: v{release_decision.next_version}")
                auto_release_version = release_decision.next_version

    files_to_stage = list(selected_files)

    for auto_file in AUTO_INCLUDED_FILES:
        if auto_file not in files_to_stage and (cwd / auto_file).exists():
            files_to_stage.append(auto_file)

    if args.dry_run:
        print("\n🧪 Dry run enabled: no commit was created.")
        print(f"💬 Suggested final commit message: {final_message}")

        if files_to_stage:
            print("\nFiles to include:")
            for file_path in files_to_stage:
                print(f"  - {file_path}")

        print_release_evaluation_summary(
            heuristic_suggestion,
            ai_suggestion,
            release_decision,
        )

        print_heuristic_release_suggestion_from_result(
            heuristic_suggestion,
            debug=ai_config.debug,
        )
        print_ai_release_suggestion_from_result(
            ai_suggestion,
            debug=ai_config.debug,
        )

        restore_auto_included_files(cwd, auto_files_snapshot)
        sys.exit(0)

    try:
        git_add_files(files_to_stage, cwd)
        commit_output = git_commit(final_message, cwd)
    except GitError as exc:
        restore_auto_included_files(cwd, auto_files_snapshot)
        print(f"Git error while creating commit: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n✅ Commit created successfully.\n")
    print(commit_output)

    if auto_release_version is not None:
        try:
            created_tag = create_release_tag(cwd, auto_release_version)
            print(f"🏷 Created tag: {created_tag}")
        except GitError as exc:
            print(f"Warning: release tag could not be created: {exc}", file=sys.stderr)

    print_release_evaluation_summary(
        heuristic_suggestion,
        ai_suggestion,
        release_decision,
    )

    print_heuristic_release_suggestion_from_result(
        heuristic_suggestion,
        debug=ai_config.debug,
    )
    print_ai_release_suggestion_from_result(
        ai_suggestion,
        debug=ai_config.debug,
    )


if __name__ == "__main__":
    main()