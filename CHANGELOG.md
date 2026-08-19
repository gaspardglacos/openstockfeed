# Changelog

All notable changes to OpenStockFeed will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `tests/` directory with smoke tests for the CLI (`--help`, `-m osf`).
- `tests/test_package.py` to verify package version wiring.
- `osf/__main__.py` enabling `python -m osf` as an entry point.
- `requirements-dev.txt` for development and test dependencies.
- GitHub Actions CI matrix (Python 3.10 / 3.11 / 3.12 on Ubuntu and Windows).
- CHANGELOG.md.
- `.worktrees/` and other local artifacts added to `.gitignore`.

### Changed
- README rewritten: closed broken Markdown code fences, replaced incorrect
  "Selenium" wording with "Playwright", added badges, requirements section,
  development instructions, and project layout.
- `requirements.txt` reduced to package runtime deps only (playwright, psutil,
  requests); `gold.py` requirements documented inline.
- `.gitignore` extended with `.worktrees/`, `.pytest_cache/`, `.coverage`,
  `htmlcov/`, and `.DS_Store`.

## [0.1.0] - 2026-08-02

### Added
- Initial release.
- Live stock price watching via Playwright + Microsoft Edge (headless by default).
- CLI command `osf` with ticker, interval, output, webhook, visibility flags.
- Optional JSONL output and webhook notifications.
- Automatic Edge/EdgeDriver cleanup on exit.
- `pyproject.toml` build metadata; PyPI distribution.

[Unreleased]: https://github.com/gbeharel/openstockfeed/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gbeharel/openstockfeed/releases/tag/v0.1.0