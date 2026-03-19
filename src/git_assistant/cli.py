from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import readline
except ImportError:  # pragma: no cover
    readline = None

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
    get_upstream_status,
    git_add_files,
    git_commit,
    git_init,
    git_pull_ff_only,
    is_git_repo,
    has_remote_named,
    git_push,
    git_push_tag,
    run_git_command,
)
from git_assistant.hosting import (
    HostingProviderError,
    RemoteRepositoryRequest,
    create_remote_repository,
    list_remote_providers,
)
from git_assistant.readme.service import (
    ReadmeUpdateError,
    apply_generated_readme,
    apply_readme_update,
    clear_readme_preview,
    edit_generated_readme_proposal,
    edit_generated_readme,
    edit_readme_update_proposal,
    edit_readme_update,
    evaluate_readme_update,
    generate_initial_readme,
    preview_generated_readme,
    preview_readme_update,
)
from git_assistant.release.ai_evaluator import (
    evaluate_release_with_ai,
    generate_first_stable_hint_reason,
)
from git_assistant.release.decision import decide_auto_release
from git_assistant.release.evaluator import evaluate_first_stable_hint, evaluate_release
from git_assistant.release.executor import (
    create_release_tag,
    get_release_managed_files,
    normalize_release_version,
    prepare_release_changelog,
)


CHANGELOG_FILE = "CHANGELOG.md"
README_FILE = "README.md"
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
        "--skip-readme",
        action="store_true",
        help="Skip README.md evaluation, generation, editing, and staging during the workflow",
    )

    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Include all changed files without prompting for selection",
    )

    parser.add_argument(
        "--release",
        default=None,
        help="Apply a release directly using a version like 0.7.2 or v0.7.2",
    )

    parser.add_argument(
        "--non-interactive",
        "--yes",
        dest="non_interactive",
        action="store_true",
        help="Run non-interactively using automatic default decisions where possible (--yes is kept as a compatibility alias)",
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize a local repository if needed and optionally configure a remote repository",
    )

    return parser.parse_args()


def restore_managed_files(cwd: Path) -> None:
    """
    Restore managed files (CHANGELOG.md, README.md) to their last committed
    state via git checkout. Files that don't exist in the last commit are
    deleted if they were created during this workflow.
    """
    for file_path in [CHANGELOG_FILE, README_FILE]:
        abs_path = cwd / file_path
        if _path_exists_in_head(cwd, file_path):
            run_git_command(["checkout", "--", file_path], cwd=cwd)
            continue

        if abs_path.exists():
            abs_path.unlink()


def restore_workflow_state(cwd: Path) -> None:
    """
    Restore workflow-managed files and remove temporary preview artifacts.
    """
    restore_managed_files(cwd)
    clear_readme_preview(cwd)


def restore_dry_run_state(cwd: Path) -> None:
    """
    Best-effort cleanup for dry runs so the repository ends in its initial state.
    """
    try:
        restore_workflow_state(cwd)
    except (GitError, OSError) as exc:
        print(
            f"Warning: dry-run cleanup could not fully restore the workspace: {exc}",
            file=sys.stderr,
        )


def _path_exists_in_head(cwd: Path, file_path: str) -> bool:
    """
    Return True when the path exists in HEAD.
    """
    try:
        run_git_command(["cat-file", "-e", f"HEAD:{file_path}"], cwd=cwd)
        return True
    except GitError:
        return False


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


def prompt_sync_action(clean_worktree: bool) -> str:
    print("\n⚠ Remote branch has new commits.")
    if clean_worktree:
        print("[1] Pull now")
        print("[2] Continue anyway")
        print("[0] Cancel")
    else:
        print("Local changes detected; automatic pull is disabled for safety.")
        print("[1] Continue anyway")
        print("[0] Cancel")
    return input("> ").strip()


def prompt_push_after_commit() -> str:
    print("\n⚙ Push commit to origin?")
    print("[1] Push commit")
    print("[0] Skip")
    return input("> ").strip()


def prompt_remote_creation() -> str:
    print("\n🌐 Create and configure a remote repository?")
    print("[1] Yes")
    print("[0] No")
    return input("> ").strip()


def prompt_remote_provider_choice() -> str:
    providers = list_remote_providers()
    print("\n🌐 Choose a remote hosting provider:")
    for index, provider in enumerate(providers, start=1):
        print(f"[{index}] {provider.label}")
    print("[0] Cancel")
    return input("> ").strip()


def prompt_github_owner(default_owner: str | None = None) -> str:
    prompt = "GitHub owner or organization"
    if default_owner:
        prompt = f"{prompt} [{default_owner}]"
    return input(f"{prompt}: ").strip()


def prompt_remote_visibility() -> str:
    print("\n🔐 Repository visibility:")
    print("[1] Private")
    print("[2] Public")
    return input("> ").strip()


def prompt_edit_commit_message(suggested_message: str) -> str:
    prompt = "Edit commit message: "

    if readline is None:
        print(f"{prompt}{suggested_message}")
        return input().strip()

    def _prefill() -> None:
        readline.insert_text(suggested_message)
        readline.redisplay()

    try:
        readline.set_pre_input_hook(_prefill)
        return input(prompt).strip()
    finally:
        readline.set_pre_input_hook(None)


def maybe_handle_upstream_sync(cwd: Path, *, clean_worktree: bool, non_interactive: bool = False) -> None:
    try:
        upstream = get_upstream_status(cwd)
    except GitError as exc:
        print(f"Warning: could not determine upstream sync status: {exc}", file=sys.stderr)
        return

    if not upstream.has_upstream or upstream.behind <= 0:
        return

    print("\n🌐 Upstream status:")
    print(f"- behind: {upstream.behind}")
    if upstream.ahead > 0:
        print(f"- ahead: {upstream.ahead}")
    if upstream.upstream_ref:
        print(f"- upstream: {upstream.upstream_ref}")

    if non_interactive:
        if clean_worktree:
            try:
                git_pull_ff_only(cwd)
            except GitError as exc:
                print(f"Git error while pulling latest changes: {exc}", file=sys.stderr)
                sys.exit(1)
            print("⬇ Repository updated with remote changes.")
            return

        print("⚠ Continuing without pull because local changes are present.")
        return

    while True:
        action = prompt_sync_action(clean_worktree)

        if clean_worktree and action == "1":
            try:
                git_pull_ff_only(cwd)
            except GitError as exc:
                print(f"Git error while pulling latest changes: {exc}", file=sys.stderr)
                sys.exit(1)
            print("⬇ Repository updated with remote changes.")
            return

        if clean_worktree and action == "2":
            return

        if not clean_worktree and action == "1":
            return

        if action == "0":
            print("Cancelled.")
            sys.exit(0)

        print("Invalid option.")


def _default_github_owner() -> str | None:
    for env_name in ("GITHUB_OWNER", "GITHUB_USER", "USER"):
        value = os.environ.get(env_name)
        if value:
            return value
    return None


def _get_github_token() -> str | None:
    for env_name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(env_name)
        if value:
            return value
    return None


def choose_remote_provider(non_interactive: bool = False) -> str | None:
    providers = list_remote_providers()

    if non_interactive:
        return None

    while True:
        choice = prompt_remote_provider_choice()

        if choice == "0":
            return None

        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(providers):
                return providers[index].key

        print("Invalid option.")


def maybe_configure_remote_repository(
    cwd: Path,
    *,
    non_interactive: bool = False,
) -> None:
    if has_remote_named("origin", cwd):
        print("🌐 Remote 'origin' is already configured.")
        return

    if non_interactive:
        print("ℹ Skipping remote repository creation in non-interactive mode.")
        return

    while True:
        action = prompt_remote_creation()

        if action == "0":
            return

        if action == "1":
            break

        print("Invalid option.")

    provider_key = choose_remote_provider(non_interactive=non_interactive)
    if provider_key is None:
        return

    repo_name = cwd.resolve().name

    if provider_key == "github":
        token = _get_github_token()
        if not token:
            print(
                "Warning: set GITHUB_TOKEN or GH_TOKEN to create GitHub repositories.",
                file=sys.stderr,
            )
            return

        default_owner = _default_github_owner()
        owner = prompt_github_owner(default_owner=default_owner) or (default_owner or "")
        if not owner:
            print("Cancelled: no GitHub owner provided.", file=sys.stderr)
            return

        while True:
            visibility_choice = prompt_remote_visibility()
            if visibility_choice == "1":
                visibility = "private"
                break
            if visibility_choice == "2":
                visibility = "public"
                break
            print("Invalid option.")

        request = RemoteRepositoryRequest(
            owner=owner,
            name=repo_name,
            visibility=visibility,
        )

        try:
            remote_url = create_remote_repository(
                provider_key,
                cwd,
                request,
                token=token,
            )
        except HostingProviderError as exc:
            print(f"Remote setup failed: {exc}", file=sys.stderr)
            return

        print(f"🌐 Remote repository configured: {remote_url}")
        return

    print(f"Warning: provider '{provider_key}' is not implemented.", file=sys.stderr)


def handle_repository_init(cwd: Path, *, non_interactive: bool = False) -> None:
    if is_git_repo(cwd):
        repo_root = get_repo_root(cwd)
        print(f"📦 Repository already initialized: {repo_root}")
    else:
        try:
            git_init(cwd)
        except GitError as exc:
            print(f"Git error while initializing repository: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"📦 Repository initialized: {cwd}")

    maybe_configure_remote_repository(cwd, non_interactive=non_interactive)

def prompt_readme_update_action() -> str:
    print("\n📘 README update available:")
    print("[1] Apply update")
    print("[2] Preview update")
    print("[3] Edit proposed README")
    print("[4] Skip")
    return input("> ").strip()


def prompt_readme_generate_action() -> str:
    print("\n📘 No README.md found — generate one?")
    print("[1] Generate and apply")
    print("[2] Preview first")
    print("[3] Edit before applying")
    print("[4] Skip")
    return input("> ").strip()


def maybe_handle_readme_update(
    cwd: Path,
    ai_config: AIConfig,
    *,
    dry_run: bool = False,
    non_interactive: bool = False,
) -> bool:
    clear_readme_preview(cwd)
    readme_path = cwd / README_FILE

    if not readme_path.exists():
        return _handle_readme_generation(
            cwd,
            ai_config,
            dry_run=dry_run,
            non_interactive=non_interactive,
        )

    try:
        result = evaluate_readme_update(cwd, ai_config)
    except ReadmeUpdateError as exc:
        if ai_config.debug:
            print(f"\n[DEBUG] README evaluation failed: {exc}")
        return False

    if not result.should_update:
        if ai_config.debug:
            print(f"\n[DEBUG] README update not needed: {result.reason}")
        return False

    print("\n📘 README evaluation:")
    print(f"- update needed: yes")
    print(f"- reason: {result.reason}")
    if result.updated_sections:
        print(f"- sections: {', '.join(result.updated_sections)}")

    if non_interactive:
        if dry_run:
            clear_readme_preview(cwd)
            print("🧪 README.md update would be applied automatically (dry run).")
            return True
        apply_readme_update(cwd, result)
        clear_readme_preview(cwd)
        print("📝 README.md updated automatically.")
        return True

    while True:
        action = prompt_readme_update_action()

        if action == "1":
            if dry_run:
                clear_readme_preview(cwd)
                print("🧪 README.md update would be applied (dry run).")
                return True
            apply_readme_update(cwd, result)
            clear_readme_preview(cwd)
            print("📝 README.md updated.")
            return True

        if action == "2":
            preview_path, diff_path = preview_readme_update(cwd, result)
            print(f"🔎 Preview opened: {preview_path}")
            print(f"🧾 Diff saved at: {diff_path}")
            continue

        if action == "3":
            try:
                if dry_run:
                    edit_readme_update_proposal(cwd, result)
                else:
                    edit_readme_update(cwd, result)
            except RuntimeError as exc:
                print(f"Warning: {exc}", file=sys.stderr)
                continue
            clear_readme_preview(cwd)
            if dry_run:
                print("🧪 Edited README proposal kept only for dry run.")
                return True
            print("📝 README.md updated from edited proposal.")
            return True

        if action == "4":
            clear_readme_preview(cwd)
            return False

        print("Invalid option.")


def _handle_readme_generation(
    cwd: Path,
    ai_config: AIConfig,
    *,
    dry_run: bool = False,
    non_interactive: bool = False,
) -> bool:
    clear_readme_preview(cwd)
    if non_interactive:
        print("\n✨ Generating README.md...")
        try:
            result = generate_initial_readme(cwd, ai_config)
        except ReadmeUpdateError as exc:
            print(f"Warning: README generation failed: {exc}", file=sys.stderr)
            return False

        if dry_run:
            clear_readme_preview(cwd)
            print("🧪 README.md would be generated automatically (dry run).")
            return True

        apply_generated_readme(cwd, result)
        clear_readme_preview(cwd)
        print("📝 README.md generated automatically.")
        return True

    while True:
        action = prompt_readme_generate_action()

        if action == "4":
            clear_readme_preview(cwd)
            return False

        if action in ("1", "2", "3"):
            print("\n✨ Generating README.md...")
            try:
                result = generate_initial_readme(cwd, ai_config)
            except ReadmeUpdateError as exc:
                print(f"Warning: README generation failed: {exc}", file=sys.stderr)
                return False

            if action == "2":
                preview_path, diff_path = preview_generated_readme(cwd, result)
                print(f"🔎 Preview opened: {preview_path}")
                print(f"🧾 Diff saved at: {diff_path}")
                continue

            if action == "3":
                try:
                    if dry_run:
                        edit_generated_readme_proposal(cwd, result)
                    else:
                        edit_generated_readme(cwd, result)
                except RuntimeError as exc:
                    print(f"Warning: {exc}", file=sys.stderr)
                    continue
                clear_readme_preview(cwd)
                if dry_run:
                    print("🧪 Edited README proposal kept only for dry run.")
                    return True
                print("📝 README.md generated from edited proposal.")
                return True

            if dry_run:
                clear_readme_preview(cwd)
                print("🧪 README.md would be generated (dry run).")
                return True

            apply_generated_readme(cwd, result)
            clear_readme_preview(cwd)
            print("📝 README.md generated.")
            return True

        print("Invalid option.")
def prompt_release_choice(
    heuristic,
    ai,
    first_stable_hint=None,
) -> str | None:
    options: dict[str, str] = {}
    next_option = 1

    heuristic_version = heuristic.next_version if heuristic.should_release else None
    ai_version = ai.next_version if ai and ai.should_release else None

    lines: list[str] = []

    if (
        heuristic.should_release
        and ai is not None
        and ai.should_release
        and heuristic.release_type == ai.release_type
        and heuristic_version is not None
        and heuristic_version == ai_version
    ):
        lines.append(f"[1] Release {heuristic_version}")
        options["1"] = heuristic_version
        next_option += 1
    elif heuristic.should_release and heuristic_version:
        option = str(next_option)
        lines.append(f"[{option}] Release {heuristic_version} (heuristic)")
        options[option] = heuristic_version
        next_option += 1

    if ai and ai.should_release and ai_version and ai_version not in options.values():
        option = str(next_option)
        lines.append(f"[{option}] Release {ai_version} (AI)")
        options[option] = ai_version
        next_option += 1

    if (
        first_stable_hint is not None
        and first_stable_hint.should_suggest
        and first_stable_hint.version
        and first_stable_hint.version not in options.values()
    ):
        option = str(next_option)
        lines.append(f"[{option}] Release {first_stable_hint.version} (first stable)")
        options[option] = first_stable_hint.version

    if not options:
        return None

    print("\n⚙ Apply a release?")
    for line in lines:
        print(line)
    print("[0] Skip")

    choice = input("> ").strip()

    return options.get(choice)

def apply_release(
    cwd: Path,
    version: str,
) -> None:
    """
    Apply a release by closing the Unreleased section,
    committing the changelog, creating a tag, and pushing both
    the release commit and tag to origin.
    """
    normalized_version = normalize_release_version(version)

    try:
        prepare_release_changelog(cwd, version=normalized_version)
    except (OSError, ValueError) as exc:
        print(f"Warning: failed to prepare release changelog: {exc}", file=sys.stderr)
        return

    try:
        git_add_files(get_release_managed_files(cwd), cwd)
        git_commit(f"chore(release): publish v{normalized_version}", cwd)
    except GitError as exc:
        print(f"Git error while creating release commit: {exc}", file=sys.stderr)
        return

    try:
        created_tag = create_release_tag(cwd, normalized_version)
        print(f"🏷 Created tag: {created_tag}")
    except GitError as exc:
        print(f"Warning: release tag could not be created: {exc}", file=sys.stderr)
        return

    try:
        git_push(cwd)
        print("⬆ Release commit pushed to origin.")
    except GitError as exc:
        print(f"Warning: release commit could not be pushed: {exc}", file=sys.stderr)
        return

    try:
        git_push_tag(cwd, created_tag)
        print(f"⬆ Tag pushed to origin: {created_tag}")
    except GitError as exc:
        print(f"Warning: release tag could not be pushed: {exc}", file=sys.stderr)
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


def evaluate_release_suggestions(
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


def print_first_stable_release_hint(hint) -> None:
    if not hint.should_suggest or hint.version is None:
        return

    print("\n🌱 Stable release hint:")
    print(f"- reason: {hint.reason}")
    print(f"- consider: git-assistant --release {hint.version}")


def enrich_first_stable_hint_reason(hint, ai_config: AIConfig):
    if not hint.should_suggest:
        return hint

    try:
        hint.reason = generate_first_stable_hint_reason(hint, ai_config)
    except (AIProviderError, ValueError) as exc:
        if ai_config.debug:
            print(f"\n[DEBUG] First stable hint generation failed: {exc}")

    return hint


def select_files_for_analysis(
    args: argparse.Namespace,
    selectable_files: list[str],
) -> list[str]:
    if args.all_files or getattr(args, "non_interactive", getattr(args, "yes", False)):
        print_changed_files(selectable_files)
        return list(selectable_files)

    print_numbered_files(selectable_files)
    prompted_selection = prompt_file_selection(selectable_files)
    selected_files = list(selectable_files) if prompted_selection is None else prompted_selection
    print()
    print_selected_files(selected_files)
    return selected_files


def resolve_commit_message(
    cwd: Path,
    ai_config: AIConfig,
    selected_files: list[str] | None,
    *,
    non_interactive: bool = False,
) -> str:
    while True:
        result = generate_and_display_commit_message(
            cwd=cwd,
            ai_config=ai_config,
            selected_files=selected_files,
        )

        if non_interactive:
            return result.message

        action = prompt_user_action()

        if action == "1":
            return result.message
        if action == "2":
            edited_message = prompt_edit_commit_message(result.message)
            if not edited_message:
                print("Empty commit message. Cancelled.")
                sys.exit(1)
            return edited_message
        if action == "3":
            print("\n🔁 Regenerating commit message...")
            continue

        print("Cancelled.")
        sys.exit(0)


def print_dry_run_summary(
    final_message: str,
    files_to_stage: list[str],
    heuristic_suggestion,
    ai_suggestion,
    release_decision,
    first_stable_hint,
    *,
    debug: bool = False,
) -> None:
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
        debug=debug,
    )
    print_ai_release_suggestion_from_result(
        ai_suggestion,
        debug=debug,
    )
    print_first_stable_release_hint(first_stable_hint)


def choose_release_version(
    heuristic_suggestion,
    ai_suggestion,
    first_stable_hint,
    *,
    non_interactive: bool = False,
) -> str | None:
    if non_interactive:
        heuristic_version = (
            heuristic_suggestion.next_version
            if heuristic_suggestion.should_release
            else None
        )
        ai_version = (
            ai_suggestion.next_version
            if ai_suggestion and ai_suggestion.should_release
            else None
        )
        if (
            heuristic_suggestion.should_release
            and ai_suggestion is not None
            and ai_suggestion.should_release
            and heuristic_suggestion.release_type == ai_suggestion.release_type
            and heuristic_version is not None
            and heuristic_version == ai_version
        ):
            return heuristic_version
        return None

    return prompt_release_choice(
        heuristic_suggestion,
        ai_suggestion,
        first_stable_hint,
    )


def handle_post_commit_actions(
    cwd: Path,
    heuristic_suggestion,
    ai_suggestion,
    release_decision,
    first_stable_hint,
    *,
    debug: bool = False,
    non_interactive: bool = False,
) -> None:
    print_release_evaluation_summary(
        heuristic_suggestion,
        ai_suggestion,
        release_decision,
    )

    print_heuristic_release_suggestion_from_result(
        heuristic_suggestion,
        debug=debug,
    )

    print_ai_release_suggestion_from_result(
        ai_suggestion,
        debug=debug,
    )

    if heuristic_suggestion.should_release or (ai_suggestion and ai_suggestion.should_release):
        print_first_stable_release_hint(first_stable_hint)

    release_version = choose_release_version(
        heuristic_suggestion,
        ai_suggestion,
        first_stable_hint,
        non_interactive=non_interactive,
    )

    if release_version is not None:
        try:
            apply_release(cwd, release_version)
        except GitError as exc:
            print(
                f"Warning: release could not be created: {exc}",
                file=sys.stderr,
            )
        return

    if non_interactive:
        try:
            git_push(cwd)
        except GitError as exc:
            print(f"Warning: commit could not be pushed: {exc}", file=sys.stderr)
            return
        print("⬆ Commit pushed to origin.")
        return

    while True:
        action = prompt_push_after_commit()

        if action == "1":
            try:
                git_push(cwd)
            except GitError as exc:
                print(f"Warning: commit could not be pushed: {exc}", file=sys.stderr)
                return
            print("⬆ Commit pushed to origin.")
            return

        if action == "0":
            return

        print("Invalid option.")


def main() -> None:
    args = parse_args()
    cwd = Path.cwd()
    non_interactive = getattr(args, "non_interactive", getattr(args, "yes", False))

    if getattr(args, "init", False):
        handle_repository_init(cwd, non_interactive=non_interactive)
        sys.exit(0)

    if not is_git_repo(cwd):
        print("Error: not inside a Git repository.", file=sys.stderr)
        sys.exit(1)

    manual_release = getattr(args, "release", None)

    if manual_release:
        try:
            version = normalize_release_version(manual_release)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"📦 Repository: {get_repo_root(cwd)}")
        print(f"🚀 Applying manual release: {version}")
        apply_release(cwd, version)
        sys.exit(0)

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

    maybe_handle_upstream_sync(
        cwd,
        clean_worktree=not bool(status.strip()),
        non_interactive=non_interactive,
    )

    selectable_files = filter_selectable_files(changed_files)

    if not selectable_files:
        print("No selectable user files detected.")
        print("Only auto-included files are currently modified.")
        sys.exit(0)

    ai_config = build_ai_config(args, cwd)

    print(f"📦 Repository: {repo_root}")

    selected_files = select_files_for_analysis(args, selectable_files)

    if ai_config.debug:
        print()
        print_ai_config(ai_config)

    final_message = resolve_commit_message(
        cwd,
        ai_config,
        selected_files,
        non_interactive=non_interactive,
    )

    try:
        update_changelog(cwd, final_message)
        skip_readme = getattr(args, "skip_readme", False)
        readme_applied = False

        if skip_readme:
            print("⏭ Skipping README.md workflow.")
        else:
            readme_applied = maybe_handle_readme_update(
                cwd,
                ai_config,
                dry_run=args.dry_run,
                non_interactive=non_interactive,
            )

        heuristic_suggestion, ai_suggestion, release_decision = evaluate_release_suggestions(
            cwd,
            ai_config,
        )
        first_stable_hint = evaluate_first_stable_hint(cwd, get_changelog_path(cwd))
        first_stable_hint = enrich_first_stable_hint_reason(first_stable_hint, ai_config)

        files_to_stage = list(selected_files)

        if CHANGELOG_FILE not in files_to_stage and (cwd / CHANGELOG_FILE).exists():
            files_to_stage.append(CHANGELOG_FILE)

        if readme_applied and "README.md" not in files_to_stage and (
            args.dry_run or (cwd / "README.md").exists()
        ):
            files_to_stage.append("README.md")

        if args.dry_run:
            print_dry_run_summary(
                final_message,
                files_to_stage,
                heuristic_suggestion,
                ai_suggestion,
                release_decision,
                first_stable_hint,
                debug=ai_config.debug,
            )
            sys.exit(0)

        try:
            git_add_files(files_to_stage, cwd)
            commit_output = git_commit(final_message, cwd)
        except GitError as exc:
            print(f"Git error while creating commit: {exc}", file=sys.stderr)
            sys.exit(1)

    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as exc:
        if args.dry_run:
            restore_dry_run_state(cwd)
        else:
            restore_workflow_state(cwd)
        print(f"\n❌ Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if args.dry_run:
            restore_dry_run_state(cwd)

    print("\n✅ Commit created successfully.\n")
    print(commit_output)
    handle_post_commit_actions(
        cwd,
        heuristic_suggestion,
        ai_suggestion,
        release_decision,
        first_stable_hint,
        debug=ai_config.debug,
        non_interactive=non_interactive,
    )
if __name__ == "__main__":
    main()
