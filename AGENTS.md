# hacker-agent — agent rules

## Scope

- Authorized security research and reverse engineering only. Require written scope before offensive workflows.
- Never commit secrets, `.env`, keys, or live memory database files.

## Stack

- Python 3.13+, `uv`, `ruff`, `mypy`, `pytest`.
- CLI: `hacker-agent` / `python -m hacker_agent`.
- SQLite memory at `HACKER_MEMORY_DB` (default `data/hacker-memory.db`).

## Workflow

- Branch from `main`; PRs target `main`. Releases are tagged on `main`.
- Run `ruff check`, `ruff format --check`, `mypy src`, `pytest -q` before push.
- Conventional commits; stage files by name.

## Project subagents

Domain-specific delegation lives in `.claude/agents/` (Claude Code) and
`.cursor/agents/` (Cursor): `security-researcher` (authorized research, CVE
triage, memory) and `ghidra-reverse-engineer` (Ghidra MCP RE). Keep both copies
in sync when adding or editing an agent. Run `./install.sh` after clone or pull
to refresh global Claude/Cursor symlinks.
