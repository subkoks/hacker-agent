# hacker-agent — agent rules

## Scope

- Authorized security research and reverse engineering only. Require written scope before offensive workflows.
- Never commit secrets, `.env`, keys, or live memory database files.

## Stack

- Python 3.13+, `uv`, `ruff`, `mypy`, `pytest`.
- CLI: `hacker-agent` / `python -m hacker_agent`.
- SQLite memory at `HACKER_MEMORY_DB` (default `data/hacker-memory.db`).

## Workflow

- Branch from `develop`; PRs target `develop`. Releases merge `develop` → `main`.
- Run `ruff check`, `ruff format --check`, `mypy src`, `pytest -q` before push.
- Conventional commits; stage files by name.

## Project subagents

Use `.cursor/agents/` definitions for domain-specific delegation in Cursor.
