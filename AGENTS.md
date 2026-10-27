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

## Coding workspace

- Use Microsoft VS Code and OpenAI Codex. The preferred model is GPT-6.1 Sol
  (`gpt-6.1-sol`), configured in `.codex/config.toml`.
- Use the existing user-level OpenAI provider/login configuration. Do not add
  repository credentials, configure Anthropic, or change global configuration.
- This file is the repository guidance for Codex. `CLAUDE.md` retains a legacy
  project map; its editor-specific directives are not Codex setup instructions.
- Legacy agent definitions remain in `.claude/agents/` and `.cursor/agents/`.
  They are compatibility assets, not native Codex agents. Preserve them without
  adding retired-editor capabilities or OpenAI model identifiers to their format.
- `install.sh` installs legacy Claude/Cursor symlinks. It is not required for
  Codex; do not run it as part of the VS Code/Codex setup.
