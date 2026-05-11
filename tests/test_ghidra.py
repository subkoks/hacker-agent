"""Tests for the Ghidra MCP bridge module."""

from __future__ import annotations

from hacker_agent.ghidra import GHIDRA_TOOLS, GhidraIntegration
from hacker_agent.memory import HackerMemorySystem, MemoryCategory


def test_tools_catalog_has_expected_size() -> None:
    # Ensure the catalog is non-trivial and stable enough to ship.
    assert len(GHIDRA_TOOLS) >= 35
    names = {t.name for t in GHIDRA_TOOLS}
    assert "mcp__ghidra__analyze-program" in names
    assert "mcp__ghidra__get-decompilation" in names


def test_tools_by_category_partitions_catalog() -> None:
    grouped = GhidraIntegration.tools_by_category()
    flat = [t for tools in grouped.values() for t in tools]
    assert len(flat) == len(GHIDRA_TOOLS)
    assert "Core" in grouped


def test_workflow_guide_mentions_phases() -> None:
    guide = GhidraIntegration.workflow_guide()
    assert "Phase 1" in guide
    assert "Phase 4" in guide


def test_record_analysis_writes_into_memory(memory: HackerMemorySystem) -> None:
    bridge = GhidraIntegration(memory=memory)
    memory_id = bridge.record_analysis(
        "/tmp/example-binary",
        triage={
            "architecture": "x86_64",
            "interesting_strings": ["UPX!", "MZ", "FLAG{ctf}"],
        },
        entry_decompilation="int main(int argc, char** argv) { return 0; }",
        notes="initial recon",
    )
    assert memory_id
    arch_hits = memory.recall("Architecture", category=MemoryCategory.INSIGHT)
    assert arch_hits and "x86_64" in arch_hits[0]["content"]
    string_hits = memory.recall("Interesting strings", category=MemoryCategory.THREAT)
    assert string_hits
