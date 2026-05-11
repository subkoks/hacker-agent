"""Pydantic models for the permanent memory subsystem."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryCategory(StrEnum):
    """Top-level memory taxonomy used everywhere in the agent."""

    TECHNIQUE = "technique"
    FAILURE = "failure"
    THREAT = "threat"
    TOOL = "tool"
    INSIGHT = "insight"


class PatternType(StrEnum):
    """Patterns auto-extracted while learning."""

    SUCCESS = "success"
    FAILURE = "failure"
    TREND = "trend"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MemoryEntry(BaseModel):
    """A single fact, finding, technique, or observation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = ""
    timestamp: str = Field(default_factory=_utc_now_iso)
    category: MemoryCategory = MemoryCategory.INSIGHT
    source: str = "manual"
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=5, ge=1, le=10)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    related_ids: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        return [str(t).strip() for t in value if str(t).strip()]

    def model_post_init(self, _context: Any) -> None:
        if not self.id:
            digest = hashlib.sha256(
                f"{self.timestamp}{self.content}".encode("utf-8", errors="replace")
            ).hexdigest()[:16]
            object.__setattr__(self, "id", digest)


class LearningPattern(BaseModel):
    """A success/failure/trend pattern derived from one or more memories."""

    model_config = ConfigDict(extra="ignore")

    id: str
    pattern_type: PatternType
    category: MemoryCategory
    pattern_data: dict[str, Any] = Field(default_factory=dict)
    first_observed: str
    last_observed: str
    occurrence_count: int = 1
    effectiveness_score: float = 0.0


class KnowledgeGap(BaseModel):
    """A topic the agent has identified as under-covered."""

    model_config = ConfigDict(extra="ignore")

    id: str
    topic: str
    reason: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    discovered_date: str = Field(default_factory=_utc_now_iso)
    resolved_date: str | None = None
    related_engagements: list[str] = Field(default_factory=list)


class AutoLearnStats(BaseModel):
    """Counters returned from an auto-learn cycle."""

    processed: int = 0
    learned: int = 0
    errors: int = 0


class Recommendations(BaseModel):
    """Bundled output of :meth:`HackerMemorySystem.get_recommendations`."""

    recommended_techniques: list[dict[str, Any]] = Field(default_factory=list)
    avoid_these_failures: list[dict[str, Any]] = Field(default_factory=list)
    proven_patterns: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "AutoLearnStats",
    "KnowledgeGap",
    "LearningPattern",
    "MemoryCategory",
    "MemoryEntry",
    "PatternType",
    "Recommendations",
]
