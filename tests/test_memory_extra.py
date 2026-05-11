"""Extra coverage for the memory subsystem — list_recent, patterns, auto_learn, gaps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hacker_agent.memory import HackerMemorySystem, MemoryCategory, MemoryEntry


def test_list_recent_respects_category_and_limit(memory: HackerMemorySystem) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.TOOL, content="nmap port scanner"))
    memory.learn(MemoryEntry(category=MemoryCategory.TOOL, content="ffuf web fuzzer"))
    memory.learn(MemoryEntry(category=MemoryCategory.THREAT, content="ransomware kill chain"))

    tools = memory.list_recent(category=MemoryCategory.TOOL, limit=10)
    assert {row["category"] for row in tools} == {MemoryCategory.TOOL.value}
    assert len(tools) == 2

    capped = memory.list_recent(limit=1)
    assert len(capped) == 1


def test_list_recent_accepts_string_category(memory: HackerMemorySystem) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.INSIGHT, content="insight 1"))
    memory.learn(MemoryEntry(category=MemoryCategory.THREAT, content="threat 1"))
    rows = memory.list_recent(category="insight", limit=10)
    assert len(rows) == 1
    assert rows[0]["category"] == "insight"


def test_failure_pattern_increments_occurrence(memory: HackerMemorySystem) -> None:
    for n in range(3):
        memory.learn(
            MemoryEntry(
                category=MemoryCategory.FAILURE,
                content=f"WAF blocked SQLi payload #{n}",
                tags=["waf", "sqli"],
                importance=6,
            )
        )
    data = memory.consolidate_knowledge()
    failure_patterns = [p for p in data["patterns"] if p["pattern_type"] == "failure"]
    assert failure_patterns, "expected at least one failure pattern after 3 hits"
    assert failure_patterns[0]["occurrence_count"] >= 2


def test_success_pattern_tracks_effectiveness(memory: HackerMemorySystem) -> None:
    for n in range(5):
        memory.learn(
            MemoryEntry(
                category=MemoryCategory.TECHNIQUE,
                content=f"SSRF vector #{n}",
                tags=["ssrf"],
                importance=8,
                confidence=0.9,
            )
        )
    patterns = memory.consolidate_knowledge()["patterns"]
    success = [p for p in patterns if p["pattern_type"] == "success"]
    assert success
    assert 0.0 < success[0]["effectiveness_score"] <= 1.0


def test_threat_trend_detected_when_repeated(memory: HackerMemorySystem) -> None:
    for n in range(4):
        memory.learn(
            MemoryEntry(
                category=MemoryCategory.THREAT,
                content=f"phishing campaign variant {n}",
                tags=["phishing", "campaign"],
                importance=7,
            )
        )
    patterns = memory.consolidate_knowledge()["patterns"]
    trend = [p for p in patterns if p["pattern_type"] == "trend"]
    assert trend, "expected a trend pattern for repeated threat tag"


def test_auto_learn_logs_an_entry(memory: HackerMemorySystem) -> None:
    stats = memory.auto_learn(source="unit-test")
    assert stats.processed == 0
    assert stats.learned == 0
    assert stats.errors == 0


def test_identify_knowledge_gaps_returns_message_when_under_three(
    memory: HackerMemorySystem,
) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.TECHNIQUE, content="brief note on Solana"))
    gaps = memory.identify_knowledge_gaps({"technology": "Solana"})
    assert gaps == ["Insufficient knowledge about Solana"]


def test_identify_knowledge_gaps_empty_when_no_technology(memory: HackerMemorySystem) -> None:
    assert memory.identify_knowledge_gaps({}) == []


def test_identify_knowledge_gaps_silent_when_well_covered(memory: HackerMemorySystem) -> None:
    for n in range(5):
        memory.learn(
            MemoryEntry(
                category=MemoryCategory.TECHNIQUE,
                content=f"deep dive on GraphQL #{n}",
                tags=["graphql"],
            )
        )
    assert memory.identify_knowledge_gaps({"technology": "GraphQL"}) == []


def test_import_replace_mode_clears_existing(memory: HackerMemorySystem, tmp_path: Path) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.INSIGHT, content="old insight"))
    assert memory.statistics()["total_memories"] == 1

    dump = tmp_path / "fresh.json"
    dump.write_text(
        json.dumps(
            {
                "categories": {
                    "insight": [
                        {
                            "id": "new1",
                            "timestamp": "2026-01-01T00:00:00+00:00",
                            "category": "insight",
                            "source": "import",
                            "content": "new insight",
                            "tags": json.dumps(["fresh"]),
                            "importance": 5,
                            "confidence": 0.8,
                            "context": "{}",
                        }
                    ]
                }
            }
        )
    )
    count = memory.import_knowledge(dump, merge=False)
    assert count == 1
    rows = memory.list_recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["content"] == "new insight"


def test_import_handles_unstringified_tags(memory: HackerMemorySystem, tmp_path: Path) -> None:
    dump = tmp_path / "raw-tags.json"
    dump.write_text(
        json.dumps(
            {
                "categories": {
                    "technique": [
                        {
                            "timestamp": "2026-01-01T00:00:00+00:00",
                            "category": "technique",
                            "content": "technique with list tags",
                            "tags": ["a", "b"],
                            "context": {"k": "v"},
                        }
                    ]
                }
            }
        )
    )
    count = memory.import_knowledge(dump)
    assert count == 1


def test_recommendations_include_failures_to_avoid(memory: HackerMemorySystem) -> None:
    memory.learn(
        MemoryEntry(
            category=MemoryCategory.FAILURE,
            content="vulnerable to detection when scanning Akamai-fronted hosts",
            tags=["akamai"],
        )
    )
    recs = memory.get_recommendations({"technology": "Akamai", "target_type": "web"})
    assert any("Akamai" in row["content"] for row in recs.avoid_these_failures)


def test_statistics_shortcut_matches_consolidate(memory: HackerMemorySystem) -> None:
    memory.learn(MemoryEntry(category=MemoryCategory.INSIGHT, content="a"))
    memory.learn(MemoryEntry(category=MemoryCategory.TECHNIQUE, content="b"))
    via_stats = memory.statistics()
    via_consolidate = memory.consolidate_knowledge()["statistics"]
    assert via_stats["total_memories"] == via_consolidate["total_memories"]


def test_memory_entry_id_is_deterministic_for_same_content() -> None:
    a = MemoryEntry(content="same", timestamp="2026-01-01T00:00:00+00:00")
    b = MemoryEntry(content="same", timestamp="2026-01-01T00:00:00+00:00")
    assert a.id == b.id


def test_memory_entry_rejects_confidence_out_of_range() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MemoryEntry(content="x", confidence=1.5)
