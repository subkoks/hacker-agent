"""Smoke tests for the Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from hacker_agent.cli.app import app

runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "hacker-agent" in result.stdout


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "hacker-agent" in result.stdout


def test_learn_then_recall_roundtrip() -> None:
    learned = runner.invoke(
        app,
        ["learn", "--content", "Use Burp Suite to test access control", "--category", "tool"],
    )
    assert learned.exit_code == 0
    assert "Learned" in learned.stdout

    recalled = runner.invoke(app, ["recall", "--query", "Burp"])
    assert recalled.exit_code == 0
    assert "Burp Suite" in recalled.stdout


def test_audit_generate_markdown() -> None:
    result = runner.invoke(app, ["audit", "generate", "--type", "web-application"])
    assert result.exit_code == 0
    assert "Web Application Security Audit" in result.stdout


def test_stake_seeds_returns_valid_pair() -> None:
    result = runner.invoke(app, ["stake", "seeds"])
    assert result.exit_code == 0
    # Strip rich formatting by looking for JSON markers.
    body = result.stdout
    assert "server_seed" in body
    assert "server_seed_hash" in body


def test_ghidra_tools_listing() -> None:
    result = runner.invoke(app, ["ghidra", "tools"])
    assert result.exit_code == 0
    assert "Ghidra MCP tools" in result.stdout


def test_memory_path_prints_resolved_db() -> None:
    result = runner.invoke(app, ["memory", "path"])
    assert result.exit_code == 0
    assert "hacker-memory.db" in result.stdout
