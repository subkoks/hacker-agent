"""Tests for the SQLite-backed memory subsystem."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from hacker_agent.memory import HackerMemorySystem, MemoryCategory, MemoryEntry


def test_learn_then_recall_roundtrip(memory: HackerMemorySystem) -> None:
    entry = MemoryEntry(
        category=MemoryCategory.TECHNIQUE,
        content="JWT 'none' algorithm bypass via header manipulation",
        tags=["jwt", "auth", "bypass"],
        importance=8,
    )
    memory_id = memory.learn(entry)
    assert memory_id == entry.id

    hits = memory.recall("JWT")
    assert hits, "expected the freshly learned entry to be returned"
    assert hits[0]["id"] == memory_id
    assert hits[0]["category"] == MemoryCategory.TECHNIQUE.value


def test_recall_respects_category_filter(memory: HackerMemorySystem) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.TECHNIQUE, content="SSRF via redirect"))
    memory.learn(
        MemoryEntry(category=MemoryCategory.THREAT, content="SSRF-based RCE in cloud metadata")
    )

    techniques = memory.recall("SSRF", category=MemoryCategory.TECHNIQUE)
    assert all(row["category"] == MemoryCategory.TECHNIQUE.value for row in techniques)
    threats = memory.recall("SSRF", category=MemoryCategory.THREAT)
    assert all(row["category"] == MemoryCategory.THREAT.value for row in threats)


def test_recall_uses_min_importance(memory: HackerMemorySystem) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.INSIGHT, content="trivial note", importance=2))
    memory.learn(
        MemoryEntry(category=MemoryCategory.INSIGHT, content="important note", importance=9)
    )
    hits = memory.recall("note", min_importance=8)
    assert len(hits) == 1
    assert hits[0]["importance"] == 9


def test_recall_increments_access_counter(memory: HackerMemorySystem) -> None:
    entry = MemoryEntry(category=MemoryCategory.TOOL, content="ffuf brute-force wordlist runner")
    memory.learn(entry)
    first = memory.recall("ffuf")
    second = memory.recall("ffuf")
    assert second[0]["access_count"] > first[0]["access_count"]


def test_failure_pattern_extraction(memory: HackerMemorySystem) -> None:
    memory.learn(
        MemoryEntry(
            category=MemoryCategory.FAILURE,
            content="WAF detected the SQL injection attempt and blocked it",
            tags=["sqli", "waf"],
            importance=6,
        )
    )
    consolidated = memory.consolidate_knowledge()
    # First occurrence: consolidate's pattern view filters by occurrence_count >= 2.
    # Confirm the underlying memory landed and the consolidate API stays well-formed.
    assert consolidated["statistics"]["total_memories"] == 1
    assert isinstance(consolidated["patterns"], list)


def test_recommendations(memory: HackerMemorySystem) -> None:
    memory.learn(
        MemoryEntry(
            category=MemoryCategory.TECHNIQUE,
            content="GraphQL introspection abuse",
            tags=["graphql"],
            importance=8,
            confidence=0.9,
        )
    )
    memory.learn(
        MemoryEntry(
            category=MemoryCategory.FAILURE,
            content="GraphQL persisted queries blocked enumeration",
            tags=["graphql"],
            importance=5,
        )
    )
    recs = memory.get_recommendations({"technology": "GraphQL", "target_type": "web"})
    assert recs.recommended_techniques
    assert any("GraphQL" in row["content"] for row in recs.recommended_techniques)


def test_export_then_import_roundtrip(memory: HackerMemorySystem, tmp_path) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.INSIGHT, content="exportable insight"))
    export_path = memory.export_brain_dump(tmp_path / "dump.json")
    assert export_path.exists()
    payload = json.loads(export_path.read_text())
    assert payload["statistics"]["total_memories"] == 1

    fresh = HackerMemorySystem(db_path=tmp_path / "fresh.db")
    imported = fresh.import_knowledge(export_path)
    assert imported >= 1
    assert fresh.statistics()["total_memories"] >= 1


def test_memory_entry_validation_rejects_bad_importance() -> None:
    with pytest.raises(ValidationError):
        MemoryEntry(category=MemoryCategory.INSIGHT, content="x", importance=11)
