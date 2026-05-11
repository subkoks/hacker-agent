# hacker-agent

Permanent-memory security research and reverse-engineering agent toolkit.
A proper Python 3.13 package built on `uv`, `pydantic`, `httpx`, and `typer`.

The agent keeps an SQLite knowledge base across sessions, auto-ingests CVE/CISA-KEV
feeds, generates audit checklists for several target classes, bridges into the
Ghidra MCP toolset, and ships RGS game-math templates for the Stake Engine work.

> **Authorized testing only.** All offensive workflows assume signed scope and
> written authorization. See `~/AGENTS.md` and `~/.claude/rules/security-scope.md`.

## Layout

```
src/hacker_agent/
├── config.py            # Path + env resolution (no hardcoded absolute paths)
├── memory/              # SQLite knowledge base + Pydantic models
├── cli/                 # Typer CLI (`python -m hacker_agent` / `hacker-agent`)
├── cve/                 # NVD + CISA KEV importer (direct imports, no subprocess)
├── stake/               # Provably-fair game math + RGS templates
├── audit/               # Security-audit checklist generator
└── ghidra/              # Ghidra MCP bridge (39 tool catalog)
scripts/                 # Bash daemon + git/GitHub automation
tests/                   # pytest suite
data/                    # Runtime SQLite db (gitignored; .gitkeep tracked)
```

## Install

```bash
# Python 3.13 via pyenv
pyenv install -s 3.13
pyenv local 3.13

# uv-managed virtualenv (preferred)
uv sync --extra dev

# Or plain pip
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and adjust `HACKER_MEMORY_DB` if you want the
database somewhere other than `data/hacker-memory.db` (project-relative).

## Quickstart

```bash
# CLI entry
hacker-agent --help
python -m hacker_agent --help

# Knowledge ops
hacker-agent learn --content "JWT 'none' alg bypass" --category technique --importance 8
hacker-agent recall --query "JWT" --limit 5
hacker-agent dashboard

# CVE feed import (NVD + CISA KEV — direct, no subprocess)
hacker-agent cve import --days 7
hacker-agent cve import --kev-only

# Audit checklists
hacker-agent audit list
hacker-agent audit generate --type web-application --format markdown

# Stake Engine RGS math
hacker-agent stake verify-rtp --game crash --rounds 100000

# Ghidra MCP bridge
hacker-agent ghidra tools
hacker-agent ghidra guide
```

## Quality gates

```bash
ruff check src tests
ruff format --check src tests
mypy src
pytest -q
```

## Auto-mode

The `scripts/auto-mode.sh` daemon runs a health check, snapshot backup, and
auto-commit cycle on an interval. Auto-commits always land on a feature branch
(`auto/<utc-timestamp>`) — `main` is never pushed to from CI.

```bash
scripts/auto-mode.sh once     # single cycle
scripts/auto-mode.sh start    # background daemon
scripts/auto-mode.sh status
scripts/auto-mode.sh stop
```

## Links

- Repository: <https://github.com/subkoks/hacker-agent>
- Issues: <https://github.com/subkoks/hacker-agent/issues>
- NVD CVE 2.0 API: <https://nvd.nist.gov/developers/vulnerabilities>
- CISA KEV catalog: <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
- Stake Engine docs: <https://docs.stake-engine.com>

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, branch flow, and code standards. Vulnerability reports go through [`docs/SECURITY.md`](docs/SECURITY.md), not public issues. Community expectations live in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). User-visible changes are recorded in [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

## License

[MIT](LICENSE)
