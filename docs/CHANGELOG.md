# Changelog

All notable changes to `hacker-agent` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `.github/dependabot.yml` — weekly pip + github-actions update PRs targeting `develop`.
- Issue templates (`bug.yml`, `feature.yml`) and pull request template under `.github/`.
- `CONTRIBUTING.md` describing the dev setup, branch flow, and code standards.
- `docs/SECURITY.md` — vulnerability disclosure policy and Dependabot triage notes.
- `docs/CHANGELOG.md` — this file.

### Changed
- `pytest` pinned to `>=9.0.3,<10.0`, `pytest-asyncio` to `>=1.0,<2.0`, and `pytest-cov` upper bound relaxed to `<7.0` to resolve GHSA-6w46-j5rx-g56g (vulnerable tmpdir handling). `[tool.pytest.ini_options].minversion` bumped accordingly.
- CI workflow (`ci.yml`) now triggers on push to `develop` and feature branches (`fix/**`, `chore/**`, `deps/**`) and on PRs targeting both `main` and `develop`. The job is renamed to `ci` so the status-check context matches branch protection.
- `auto-commit.yml` now runs from `develop` (not `main`) and opens its PRs against `develop`.
- `update-deps.yml` pip-compile PRs target `develop`.

### Security
- Dependabot alert GHSA-6w46-j5rx-g56g (pytest tmpdir handling, medium severity) resolved.

## [0.2.0] - 2026-05-11

### Added
- Initial scaffold of `hacker-agent` as a Python 3.13 package using `uv` + `ruff` + `mypy` + `pytest`.
- Subpackages: `memory`, `cve`, `audit`, `stake`, `ghidra`, `cli`.
- Typer-based CLI exposed as `hacker-agent` and `python -m hacker_agent`.
- 47 unit tests covering memory CRUD, CVE importer, audit checklists, Stake Engine math, Ghidra integration, and CLI smoke.

[Unreleased]: https://github.com/subkoks/hacker-agent/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/subkoks/hacker-agent/releases/tag/v0.2.0
