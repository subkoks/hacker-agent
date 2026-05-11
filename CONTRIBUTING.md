# Contributing to hacker-agent

Thanks for your interest in contributing. This document describes the workflow, code standards, and review process for changes to `hacker-agent`.

## Before you start

- Open an issue (bug or feature) describing the problem before sending a non-trivial PR.
- Search existing issues to avoid duplicates.
- For sensitive vulnerabilities, follow [`docs/SECURITY.md`](docs/SECURITY.md) — do **not** open a public issue.

## Development setup

Requirements:

- Python **3.13+** (managed via `pyenv` recommended)
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- macOS or Linux (Windows via WSL works but is not first-class)

```bash
git clone https://github.com/subkoks/hacker-agent.git
cd hacker-agent
uv sync --extra dev
uv run python -m hacker_agent --version
```

## Branch & commit flow

- `main` and `develop` are protected. Never push directly.
- Branch naming: `feature/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`, `deps/<topic>`.
- Open PRs against `develop`. `develop` is merged into `main` for releases.
- Commits use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): short description`.
- One logical change per commit; rebase to clean history before review.
- Stage files by name (`git add path/to/file`). Avoid `git add -A` / `git add .`.

## Code standards

- `ruff check src tests` — lint must pass.
- `ruff format --check src tests` — formatter is the source of truth.
- `mypy src` — strict type checking, no new `Any` without justification.
- `pytest -q` — all tests must pass; add tests for new behavior.
- Use `pathlib.Path` (never `os.path`).
- Prefer `httpx` for HTTP, `pydantic` v2 at boundaries, `typer` for CLI.
- Logging via `logging`; never `print` in library code.

The full CI gauntlet is wired in `.github/workflows/ci.yml` — running it locally before pushing saves a round-trip:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest -q --cov=src/hacker_agent
```

## Tests

- Tests live in `tests/` and mirror the package layout.
- Use `respx` to mock HTTP calls; never hit live NVD/CISA endpoints in tests.
- Mark slow or networked tests with `@pytest.mark.slow` / `@pytest.mark.network`.

## Pull request expectations

- Use the PR template (auto-loaded).
- CI must be green before review.
- Update `docs/CHANGELOG.md` under `## Unreleased` for any user-facing change.
- Public API changes require a docstring update and a note in the PR body.

## Releases

Maintainers cut releases by:

1. Updating `version` in `pyproject.toml`.
2. Moving `Unreleased` notes to a dated section in `docs/CHANGELOG.md`.
3. Tagging `vX.Y.Z` on `main` — the `release.yml` workflow builds the wheel and creates the GitHub release.

## Security

See [`docs/SECURITY.md`](docs/SECURITY.md) for the disclosure policy.
