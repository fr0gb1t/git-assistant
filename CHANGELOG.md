# Changelog

## [Unreleased]

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
