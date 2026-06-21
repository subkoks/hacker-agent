# CLAUDE.md — hacker-agent

@AGENTS.md

> The block above imports the canonical project rules. This file adds the
> Claude Code working map: architecture, commands, and gotchas.

## What this is

`hacker-agent` (v0.2.x, MIT) — a permanent-memory security-research and
reverse-engineering toolkit. CLI-first (`typer` + `rich`), backed by a SQLite
memory store, with feeds for CVE/CISA-KEV/NVD, audit checklists, a Ghidra MCP
bridge, and Stake-engine helpers.

**Authorized security research only.** Require written scope before any
offensive workflow. Never commit secrets, `.env`, keys, or the live memory DB.

## Stack

- Python 3.13+ managed with `uv`; `ruff` (lint/format), `mypy` (types), `pytest`.
- Runtime deps: `httpx`, `pydantic` v2, `typer`, `rich`, `platformdirs`, `python-dateutil`.
- Entry point: `hacker-agent = "hacker_agent.cli.app:main"` (also `python -m hacker_agent`).
- Memory: SQLite at `HACKER_MEMORY_DB` (default `data/hacker-memory.db`).

## Layout (`src/hacker_agent/`)

- `cli/` — `typer` app and command surface (entry point lives here).
- `memory/` — SQLite-backed permanent memory (store, query, export).
- `cve/` — CVE / CISA-KEV / NVD feed ingestion and lookup.
- `audit/` — security audit checklists and runners.
- `ghidra/` — Ghidra MCP bridge for reverse-engineering workflows.
- `stake/` — Stake-engine specific helpers.
- `config.py` — settings/env resolution. `__main__.py` — module entry.
- `tests/` — pytest suite, one file per module (`test_<module>.py`).

## Commands

```bash
uv sync                              # install runtime deps into .venv
uv sync --extra dev                  # add dev tooling (pytest, mypy) — needed for the checks below
uv run hacker-agent --help           # run the CLI
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest -q                     # full suite
uv run pytest tests/test_cve.py -q   # single module
```

Run lint + format-check + mypy + pytest before every push.

## Conventions

- `snake_case`; type hints at boundaries; validate external/feed input with pydantic.
- Branch from `main`; PRs target `main`; conventional commits; stage files by name.
- Releases tagged on `main`. Project subagents live in `.claude/agents/` (Claude Code). Cursor retired 2026-06-17 — `.cursor/agents/` no longer maintained.

## CI

`@claude` mentions invoke the agent; PRs get automatic Claude review. Dependabot
is enabled (`.github/dependabot.yml`). Don't commit `data/hacker-memory.db`,
`.venv/`, or cache dirs — they're gitignored.
