"""Allow `python -m hacker_agent` to invoke the Typer CLI."""

from __future__ import annotations

from hacker_agent.cli.app import main

if __name__ == "__main__":
    main()
