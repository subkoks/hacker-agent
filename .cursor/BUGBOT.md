# Bugbot — hacker-agent review rules

## Scope and ethics (blocking)

- Flag any guidance or code that enables unauthorized access, exploitation without scope, or attacks outside written authorization.
- Require scope context for offensive workflows (audit, exploit PoC, active scanning).
- Never commit `.env`, API keys, tokens, live `data/hacker-memory.db`, or Ghidra project secrets.

## Python (`src/hacker_agent/**`, `tests/**`)

- Python 3.13+; type hints on public functions; `ruff` + `mypy` clean.
- SQLite (`memory/db.py`): flag SQL injection (use parameterized queries), missing transactions on multi-step writes.
- CVE importer: flag unvalidated external fetch without timeout and error handling.
- Ghidra integration: flag hardcoded paths that break portability without env override.

## CLI

- New commands need `--help` and tests in `tests/test_cli*.py`.
- Destructive operations require confirmation flags or dry-run mode.

## Branch workflow

- PRs target `main` — flag PRs targeting wrong base without reason.

## Before merge

- `ruff check`, `ruff format --check`, `mypy src`, `pytest -q` must pass.
