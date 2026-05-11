"""Extra CLI coverage — exercise every Typer command path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hacker_agent.cli.app import app

runner = CliRunner()


def _learn(content: str, category: str = "tool", importance: int = 5) -> None:
    result = runner.invoke(
        app,
        [
            "learn",
            "--content",
            content,
            "--category",
            category,
            "--importance",
            str(importance),
        ],
    )
    assert result.exit_code == 0, result.stdout


def test_stats_emits_json() -> None:
    _learn("nmap top ports scan")
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "total_memories" in result.stdout


def test_search_alias_returns_results() -> None:
    _learn("burp suite repeater")
    result = runner.invoke(app, ["search", "--query", "burp"])
    assert result.exit_code == 0
    assert "burp" in result.stdout.lower()


def test_list_with_category_and_limit() -> None:
    _learn("ffuf wordlist usage", category="tool")
    _learn("xss payload set", category="technique")
    result = runner.invoke(app, ["list", "--category", "tool", "--limit", "5"])
    assert result.exit_code == 0
    assert "ffuf" in result.stdout


def test_consolidate_dumps_statistics() -> None:
    _learn("insight A", category="insight")
    result = runner.invoke(app, ["consolidate"])
    assert result.exit_code == 0
    assert "statistics" in result.stdout


def test_recommend_with_context() -> None:
    _learn("OAuth scope confusion attack", category="technique", importance=8)
    result = runner.invoke(
        app, ["recommend", "--context", json.dumps({"technology": "OAuth", "target_type": "web"})]
    )
    assert result.exit_code == 0
    assert "recommended_techniques" in result.stdout


def test_gaps_reports_missing_topic() -> None:
    result = runner.invoke(app, ["gaps", "--context", json.dumps({"technology": "Quantum-CRDT"})])
    assert result.exit_code == 0
    assert "Insufficient knowledge" in result.stdout


def test_auto_learn_runs() -> None:
    result = runner.invoke(app, ["auto-learn", "--source", "test"])
    assert result.exit_code == 0
    assert "processed" in result.stdout


def test_export_and_import_via_cli(tmp_path: Path) -> None:
    _learn("export source entry", category="insight")
    dump = tmp_path / "out.json"
    result = runner.invoke(app, ["export", "--filepath", str(dump)])
    assert result.exit_code == 0
    assert dump.exists()

    # Import via the top-level alias.
    result_in = runner.invoke(app, ["import", "--filepath", str(dump)])
    assert result_in.exit_code == 0
    assert "Imported" in result_in.stdout


def test_memory_import_subcommand(tmp_path: Path) -> None:
    _learn("subcommand exportable entry", category="insight")
    dump = tmp_path / "sub.json"
    runner.invoke(app, ["memory", "export", "--filepath", str(dump)])
    assert dump.exists()
    result = runner.invoke(app, ["memory", "import", str(dump)])
    assert result.exit_code == 0
    assert "Imported" in result.stdout


def test_quick_topic_command() -> None:
    _learn("Burp Suite intruder usage", category="tool")
    result = runner.invoke(app, ["quick", "--topic", "Burp"])
    assert result.exit_code == 0
    assert "Burp" in result.stdout


def test_cheatsheet_command() -> None:
    _learn("nmap stealth scan flags", category="tool")
    result = runner.invoke(app, ["cheatsheet", "--tool-name", "nmap"])
    assert result.exit_code == 0
    assert "nmap" in result.stdout.lower()


def test_cve_check_command() -> None:
    _learn("CVE-2025-12345 reference note", category="threat")
    result = runner.invoke(app, ["cve-check", "--cve-id", "CVE-2025-12345"])
    assert result.exit_code == 0
    assert "CVE-2025-12345" in result.stdout


def test_tech_stack_command() -> None:
    _learn("GraphQL introspection trick", category="technique", importance=7)
    result = runner.invoke(app, ["tech-stack", "--technology", "GraphQL"])
    assert result.exit_code == 0
    assert "GraphQL" in result.stdout


def test_browse_command_with_data() -> None:
    _learn("entry for browse", category="insight")
    result = runner.invoke(app, ["browse", "--limit", "5"])
    assert result.exit_code == 0
    assert "ID" in result.stdout


def test_browse_command_empty() -> None:
    # Fresh empty DB (autouse fixture wipes between tests).
    result = runner.invoke(app, ["browse"])
    assert result.exit_code == 0
    assert "No memories" in result.stdout


def test_dashboard_command() -> None:
    _learn("dashboard sample", category="technique", importance=7)
    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0
    assert "Knowledge Dashboard" in result.stdout


def test_audit_list_command() -> None:
    result = runner.invoke(app, ["audit", "list"])
    assert result.exit_code == 0
    assert "web-application" in result.stdout


def test_audit_generate_json_to_output(tmp_path: Path) -> None:
    out = tmp_path / "checklist.json"
    result = runner.invoke(
        app,
        [
            "audit",
            "generate",
            "--type",
            "api-security",
            "--format",
            "json",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert isinstance(data, dict)


def test_audit_generate_all_html() -> None:
    result = runner.invoke(app, ["audit", "generate", "--type", "all", "--format", "html"])
    assert result.exit_code == 0
    assert "<" in result.stdout


def test_stake_template_known_game() -> None:
    result = runner.invoke(app, ["stake", "template", "--game", "dice"])
    assert result.exit_code == 0
    assert "class" in result.stdout.lower()


@pytest.mark.slow
def test_stake_verify_rtp_small_sim() -> None:
    result = runner.invoke(
        app,
        ["stake", "verify-rtp", "--rounds", "1000", "--cash-out-at", "2.0"],
    )
    assert result.exit_code == 0
    assert "actual_rtp" in result.stdout


def test_stake_verify_rtp_unsupported_game() -> None:
    result = runner.invoke(app, ["stake", "verify-rtp", "--game", "slots", "--rounds", "1000"])
    # Typer surfaces BadParameter as non-zero exit.
    assert result.exit_code != 0


def test_ghidra_guide_command() -> None:
    result = runner.invoke(app, ["ghidra", "guide"])
    assert result.exit_code == 0
    assert "Ghidra" in result.stdout


def test_ghidra_record_command(tmp_path: Path) -> None:
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps({"strings": ["password", "admin"], "imports": ["fopen"]}))
    decomp = tmp_path / "decomp.txt"
    decomp.write_text("int main() { return 0; }")
    fake_binary = tmp_path / "fake.bin"
    fake_binary.write_bytes(b"\x7fELF...")
    result = runner.invoke(
        app,
        [
            "ghidra",
            "record",
            "--binary",
            str(fake_binary),
            "--triage",
            str(triage),
            "--entry-decompilation",
            str(decomp),
            "--notes",
            "initial recon",
        ],
    )
    assert result.exit_code == 0
    assert "Recorded" in result.stdout
