# Changelog

## [Unreleased]

## [1.1.1] - 2026-03-19

### Added
- prompt for GitHub token during repository creation

## [1.1.0] - 2026-03-19

### Added
- add option to skip README.md workflow
- enhance configurability of version updates across files
- add origin remote check before push actions
- add SSH protocol selection for remote setup

### Changed
- move release-managed files logic to separate function

## [1.0.1] - 2026-03-19

### Added
- add repository initialization capability

## [1.0.0] - 2026-03-17

### Added
- add first stable release hint in CLI
- add AI-generated first stable hint reason generation
- add first stable release option in prompt_release_choice
- add upstream sync and push prompts
- update project description to reflect broader functionality
- add non-interactive mode option in CLI commands

## [0.7.3] - 2026-03-17

### Added
- add manual release option for specifying version directly

## [0.7.2] - 2026-03-17

### Added
- add dry run tests and improve README update rules

## [0.7.1] - 2026-03-17

### Changed
- update preview and service modules for improved handling of browser commands and normalization

## [0.7.0] - 2026-03-17

### Added
- add preview pair functionality for concurrent file viewing

### Changed
- update preview file opening logic

## [0.6.0] - 2026-03-17

### Added
- add readline support for commit message editing

## [0.5.3] - 2026-03-17

### Changed
- unify heuristic and AI release prompts when consensus

## [0.5.2] - 2026-03-17

### Changed
- conditional print for selected files display

## [0.5.1] - 2026-03-17

### Added
- automate version number synchronization across pyproject.toml and package init file
- add options to edit and clear README preview

### Changed
- enhance version release decision logic in ai_evaluator.py and evaluator.py

## [0.5.0] - 2026-03-17

### Added
- update prompt and evaluation logic for README updates

## [0.4.0] - 2026-03-17

### Added
- generate initial README.md when none exists in a project

### Changed
- wrap main logic in try-except block
- update CLI workflow for file management
- enhance JSON parsing and prompt rules

## [0.3.0] - 2026-03-16

### Changed
- update AI evaluator guidelines and logic

### Added
- add push functionality for releases
- integrate AI-driven README updates in CLI workflow

### Documentation
- update README with enhanced feature descriptions and workflow details

## [0.2.0] - 2026-03-16

### Documentation
- update README section headers
- correct indentation in README.md

### Added
- implement auto-release decision and execution logic
- add summary for release evaluation results

### Changed
- reorganize release module imports and improve auto-release flow
- restructure release prompt and apply logic

## [0.1.0] - 2026-03-15

### Added
- add changelog-based release suggestion functionality
- add auto-included file snapshot and restore functionality
- integrate changelog updates in commit workflow
- add debug option to release suggestion printing
- add dry run output improvements
- add AI-based release suggestion evaluation and output
- add repository structure context to AI prompt

### Documentation
- update changelog.mdEmptyEntriesRemoved
- update README with new features and installation instructions

### Changed
- filter selectable files in CLI output
- restructure entry insertion logic
- unify version resolution across evaluator and AI release logic
- clarify commit message guidelines
- move diff context builder to new module and update files in repo context
- move get_latest_tag to tags module
