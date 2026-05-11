"""SQLite-backed permanent memory store."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from hacker_agent.config import SETTINGS
from hacker_agent.memory.models import (
    AutoLearnStats,
    MemoryCategory,
    MemoryEntry,
    PatternType,
    Recommendations,
)

SCHEMA: str = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    importance INTEGER DEFAULT 5,
    confidence REAL DEFAULT 0.8,
    related_ids TEXT,
    context TEXT,
    access_count INTEGER DEFAULT 0,
    last_accessed TEXT
);
CREATE INDEX IF NOT EXISTS idx_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags);
CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp);
CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance);

CREATE TABLE IF NOT EXISTS learning_patterns (
    id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    category TEXT NOT NULL,
    pattern_data TEXT NOT NULL,
    first_observed TEXT,
    last_observed TEXT,
    occurrence_count INTEGER DEFAULT 1,
    effectiveness_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS auto_learn_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    source TEXT,
    items_processed INTEGER,
    items_learned INTEGER,
    errors TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    reason TEXT,
    priority INTEGER,
    discovered_date TEXT,
    resolved_date TEXT,
    related_engagements TEXT
);
"""

_FAILURE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "detection": ("detected", "blocked", "flagged", "waf", "ips"),
    "mitigation": ("patched", "fixed", "mitigated", "remediated"),
    "technique": ("outdated", "deprecated", "no longer works"),
    "configuration": ("misconfigured", "wrong setting", "invalid"),
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class HackerMemorySystem:
    """Permanent memory + auto-learning for security research workflows."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path: Path = (db_path or SETTINGS.memory_db).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def learn(self, entry: MemoryEntry) -> str:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, timestamp, category, source, content, tags, importance,
                 confidence, related_ids, context, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE((SELECT access_count FROM memories WHERE id = ?), 0),
                        ?)
                """,
                (
                    entry.id,
                    entry.timestamp,
                    entry.category.value,
                    entry.source,
                    entry.content,
                    json.dumps(entry.tags),
                    entry.importance,
                    entry.confidence,
                    json.dumps(entry.related_ids),
                    json.dumps(entry.context),
                    entry.id,
                    entry.timestamp,
                ),
            )

        self._extract_patterns(entry)
        return entry.id

    def recall(
        self,
        query: str,
        category: MemoryCategory | str | None = None,
        limit: int = 10,
        min_importance: int = 1,
    ) -> list[dict[str, Any]]:
        category_value = category.value if isinstance(category, MemoryCategory) else category
        sql = "SELECT * FROM memories WHERE (content LIKE ? OR tags LIKE ?) AND importance >= ?"
        params: list[Any] = [f"%{query}%", f"%{query}%", min_importance]
        if category_value:
            sql += " AND category = ?"
            params.append(category_value)
        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            now = _utc_now_iso()
            for row in rows:
                conn.execute(
                    "UPDATE memories SET access_count = access_count + 1, "
                    "last_accessed = ? WHERE id = ?",
                    (now, row["id"]),
                )
            return [dict(row) for row in rows]

    def list_recent(
        self,
        category: MemoryCategory | str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        category_value = category.value if isinstance(category, MemoryCategory) else category
        sql = "SELECT * FROM memories"
        params: list[Any] = []
        if category_value:
            sql += " WHERE category = ?"
            params.append(category_value)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def _extract_patterns(self, entry: MemoryEntry) -> None:
        if entry.category is MemoryCategory.FAILURE:
            self._analyze_failure_pattern(entry)
        elif entry.category is MemoryCategory.TECHNIQUE and entry.confidence > 0.7:
            self._track_success_pattern(entry)
        if entry.category is MemoryCategory.THREAT:
            self._detect_threat_trend(entry)

    def _analyze_failure_pattern(self, entry: MemoryEntry) -> None:
        content_lower = entry.content.lower()
        detected_type = "unknown"
        for ftype, keywords in _FAILURE_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                detected_type = ftype
                break

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM learning_patterns WHERE pattern_type = 'failure' "
                "AND category = ? AND pattern_data LIKE ?",
                (entry.category.value, f"%{detected_type}%"),
            ).fetchone()

            if existing:
                data = json.loads(existing["pattern_data"])
                data.setdefault("occurrences", []).append(
                    {"timestamp": entry.timestamp, "content_summary": entry.content[:100]}
                )
                conn.execute(
                    "UPDATE learning_patterns SET occurrence_count = occurrence_count + 1, "
                    "last_observed = ?, pattern_data = ? WHERE id = ?",
                    (entry.timestamp, json.dumps(data), existing["id"]),
                )
            else:
                pattern_id = hashlib.sha256(
                    f"failure-{detected_type}-{entry.timestamp}".encode()
                ).hexdigest()[:16]
                conn.execute(
                    """
                    INSERT INTO learning_patterns
                    (id, pattern_type, category, pattern_data, first_observed, last_observed)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pattern_id,
                        PatternType.FAILURE.value,
                        entry.category.value,
                        json.dumps(
                            {
                                "failure_type": detected_type,
                                "detection_method": entry.context.get("defense", "unknown"),
                                "occurrences": [{"timestamp": entry.timestamp}],
                            }
                        ),
                        entry.timestamp,
                        entry.timestamp,
                    ),
                )

    def _track_success_pattern(self, entry: MemoryEntry) -> None:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM learning_patterns WHERE pattern_type = 'success' AND category = ?",
                (entry.category.value,),
            ).fetchone()
            if existing:
                data = json.loads(existing["pattern_data"])
                successes = data.setdefault("successes", [])
                successes.append({"timestamp": entry.timestamp, "technique": entry.content[:50]})
                total = len(successes)
                effectiveness = min(1.0, total / (total + 5))
                conn.execute(
                    "UPDATE learning_patterns SET occurrence_count = occurrence_count + 1, "
                    "last_observed = ?, pattern_data = ?, effectiveness_score = ? WHERE id = ?",
                    (entry.timestamp, json.dumps(data), effectiveness, existing["id"]),
                )
            else:
                pattern_id = hashlib.sha256(
                    f"success-{entry.category.value}-{entry.timestamp}".encode()
                ).hexdigest()[:16]
                conn.execute(
                    """
                    INSERT INTO learning_patterns
                    (id, pattern_type, category, pattern_data,
                     first_observed, last_observed, occurrence_count, effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pattern_id,
                        PatternType.SUCCESS.value,
                        entry.category.value,
                        json.dumps(
                            {
                                "successes": [
                                    {"timestamp": entry.timestamp, "technique": entry.content[:50]}
                                ]
                            }
                        ),
                        entry.timestamp,
                        entry.timestamp,
                        1,
                        1 / 6,
                    ),
                )

    def _detect_threat_trend(self, entry: MemoryEntry) -> None:
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        primary_tag = entry.tags[0] if entry.tags else ""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM memories "
                "WHERE category = 'threat' AND content LIKE ? AND timestamp > ?",
                (f"%{primary_tag}%", thirty_days_ago),
            ).fetchone()
            similar = int(row["c"]) if row else 0
            if similar >= 3:
                trend_id = hashlib.sha256(
                    f"trend-{primary_tag or 'unknown'}-{_utc_now_iso()}".encode()
                ).hexdigest()[:16]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO learning_patterns
                    (id, pattern_type, category, pattern_data,
                     first_observed, last_observed, occurrence_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trend_id,
                        PatternType.TREND.value,
                        entry.category.value,
                        json.dumps(
                            {
                                "threat_type": primary_tag or "unknown",
                                "similar_threats": similar,
                                "example": entry.content[:100],
                            }
                        ),
                        entry.timestamp,
                        entry.timestamp,
                        similar,
                    ),
                )

    def auto_learn(self, source: str = "mixed") -> AutoLearnStats:
        stats = AutoLearnStats()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO auto_learn_log (timestamp, source, items_processed, items_learned, errors) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    _utc_now_iso(),
                    source,
                    stats.processed,
                    stats.learned,
                    json.dumps([]),
                ),
            )
        return stats

    def consolidate_knowledge(self) -> dict[str, Any]:
        with self._connect() as conn:
            categories: dict[str, list[dict[str, Any]]] = {}
            for cat in MemoryCategory:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE category = ? "
                    "ORDER BY importance DESC, access_count DESC LIMIT 20",
                    (cat.value,),
                ).fetchall()
                categories[cat.value] = [dict(r) for r in rows]

            patterns = conn.execute(
                "SELECT * FROM learning_patterns WHERE occurrence_count >= 2 "
                "ORDER BY effectiveness_score DESC, occurrence_count DESC"
            ).fetchall()

            gaps = conn.execute(
                "SELECT * FROM knowledge_gaps WHERE resolved_date IS NULL ORDER BY priority DESC"
            ).fetchall()

            stats_row = conn.execute(
                """
                SELECT COUNT(*) AS total_memories,
                       COALESCE(AVG(importance), 0) AS avg_importance,
                       COALESCE(SUM(access_count), 0) AS total_accesses,
                       COUNT(DISTINCT category) AS categories
                FROM memories
                """
            ).fetchone()

        return {
            "categories": categories,
            "patterns": [dict(p) for p in patterns],
            "knowledge_gaps": [dict(g) for g in gaps],
            "statistics": dict(stats_row) if stats_row else {},
            "consolidated_at": _utc_now_iso(),
        }

    def get_recommendations(self, context: dict[str, Any]) -> Recommendations:
        target_type = context.get("target_type", "")
        technology = context.get("technology", "")
        with self._connect() as conn:
            techniques = conn.execute(
                "SELECT * FROM memories WHERE category = 'technique' "
                "AND (content LIKE ? OR tags LIKE ?) AND confidence >= 0.7 "
                "ORDER BY importance DESC, confidence DESC LIMIT 5",
                (f"%{technology}%", f"%{target_type}%"),
            ).fetchall()
            failures = conn.execute(
                "SELECT * FROM memories WHERE category = 'failure' "
                "AND (content LIKE ? OR tags LIKE ?) "
                "ORDER BY timestamp DESC LIMIT 3",
                (f"%{technology}%", f"%{target_type}%"),
            ).fetchall()
            patterns = conn.execute(
                "SELECT * FROM learning_patterns WHERE pattern_type = 'success' "
                "AND effectiveness_score >= 0.6 "
                "ORDER BY effectiveness_score DESC LIMIT 3"
            ).fetchall()
        return Recommendations(
            recommended_techniques=[dict(t) for t in techniques],
            avoid_these_failures=[dict(f) for f in failures],
            proven_patterns=[dict(p) for p in patterns],
        )

    def identify_knowledge_gaps(self, engagement_context: dict[str, Any]) -> list[str]:
        gaps: list[str] = []
        tech = engagement_context.get("technology", "")
        if tech:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE content LIKE ?",
                    (f"%{tech}%",),
                ).fetchone()
                if row and int(row["c"]) < 3:
                    gaps.append(f"Insufficient knowledge about {tech}")
        return gaps

    def statistics(self) -> dict[str, Any]:
        stats = self.consolidate_knowledge().get("statistics", {})
        return dict(stats) if stats else {}

    def export_brain_dump(self, filepath: Path | str | None = None) -> Path:
        if filepath is None:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            filepath = SETTINGS.data_dir / f"hacker-brain-dump-{stamp}.json"
        out = Path(filepath).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        data = self.consolidate_knowledge()
        out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return out

    def import_knowledge(self, filepath: Path | str, merge: bool = True) -> int:
        path = Path(filepath).expanduser().resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        imported = 0
        if not merge:
            with self._connect() as conn:
                conn.execute("DELETE FROM memories")
        for cat_value, entries in data.get("categories", {}).items():
            for entry in entries:
                tags_raw = entry.get("tags", "[]")
                context_raw = entry.get("context", "{}")
                tags = json.loads(tags_raw) if isinstance(tags_raw, str) else list(tags_raw or [])
                context = (
                    json.loads(context_raw)
                    if isinstance(context_raw, str)
                    else dict(context_raw or {})
                )
                memory = MemoryEntry(
                    id=entry.get("id", ""),
                    timestamp=entry.get("timestamp", _utc_now_iso()),
                    category=MemoryCategory(entry.get("category", cat_value)),
                    source=entry.get("source", "import"),
                    content=entry.get("content", ""),
                    tags=tags,
                    importance=int(entry.get("importance", 5)),
                    confidence=float(entry.get("confidence", 0.8)),
                    context=context,
                )
                self.learn(memory)
                imported += 1
        return imported


__all__ = ["SCHEMA", "HackerMemorySystem"]
