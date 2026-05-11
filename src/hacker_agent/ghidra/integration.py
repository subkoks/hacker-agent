"""Ghidra MCP bridge.

This module catalogs the Ghidra MCP tools the agent expects to be wired through
the MCP server (Reverse-engineering surface). It also exposes a thin helper that
records analysis findings into :class:`HackerMemorySystem`.

The actual MCP calls are issued by the host (Claude Code) — this module is the
catalog + memory glue, not an MCP client.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hacker_agent.memory import HackerMemorySystem, MemoryCategory, MemoryEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GhidraTool:
    """Single Ghidra MCP tool descriptor."""

    name: str
    category: str
    description: str


GHIDRA_TOOLS: tuple[GhidraTool, ...] = (
    GhidraTool("mcp__ghidra__analyze-program", "Core", "Run auto-analysis on a program"),
    GhidraTool("mcp__ghidra__get-functions", "Core", "List functions in a program"),
    GhidraTool("mcp__ghidra__get-function-count", "Core", "Get total function count"),
    GhidraTool("mcp__ghidra__get-strings", "Core", "Get strings from program"),
    GhidraTool("mcp__ghidra__get-strings-count", "Core", "Get string count"),
    GhidraTool("mcp__ghidra__get-symbols", "Core", "Get symbols"),
    GhidraTool("mcp__ghidra__get-symbols-count", "Core", "Get symbol count"),
    GhidraTool("mcp__ghidra__get-decompilation", "Decompiler", "Decompile a function"),
    GhidraTool(
        "mcp__ghidra__get-callers-decompiled",
        "Decompiler",
        "Decompile callers of a function",
    ),
    GhidraTool(
        "mcp__ghidra__get-referencers-decompiled",
        "Decompiler",
        "Decompile referencers of an address/symbol",
    ),
    GhidraTool("mcp__ghidra__find-cross-references", "XRefs", "Find cross-references"),
    GhidraTool("mcp__ghidra__find-import-references", "XRefs", "Find import references"),
    GhidraTool("mcp__ghidra__find-common-callers", "XRefs", "Find common callers"),
    GhidraTool(
        "mcp__ghidra__trace-data-flow-backward",
        "Data Flow",
        "Trace data flow backward",
    ),
    GhidraTool(
        "mcp__ghidra__trace-data-flow-forward",
        "Data Flow",
        "Trace data flow forward",
    ),
    GhidraTool(
        "mcp__ghidra__search-decompilation",
        "Search",
        "Search decompilation for patterns",
    ),
    GhidraTool("mcp__ghidra__find-constant-uses", "Search", "Find constant uses"),
    GhidraTool(
        "mcp__ghidra__find-constants-in-range",
        "Search",
        "Find constants in a numeric range",
    ),
    GhidraTool(
        "mcp__ghidra__list-common-constants",
        "Search",
        "List most-common constants in the program",
    ),
    GhidraTool("mcp__ghidra__get-call-graph", "Call Graph", "Get call graph"),
    GhidraTool("mcp__ghidra__get-call-tree", "Call Graph", "Get call tree"),
    GhidraTool("mcp__ghidra__analyze-vtable", "VTables", "Analyze a vtable"),
    GhidraTool("mcp__ghidra__find-vtable-callers", "VTables", "Find vtable callers"),
    GhidraTool(
        "mcp__ghidra__find-vtables-containing-function",
        "VTables",
        "Find vtables containing a function",
    ),
    GhidraTool("mcp__ghidra__list-structures", "Structures", "List structures"),
    GhidraTool("mcp__ghidra__get-structure-info", "Structures", "Get structure info"),
    GhidraTool("mcp__ghidra__parse-c-structure", "Structures", "Parse a C structure"),
    GhidraTool("mcp__ghidra__apply-structure", "Structures", "Apply a structure"),
    GhidraTool("mcp__ghidra__get-bookmarks", "Annotations", "Get bookmarks"),
    GhidraTool("mcp__ghidra__set-bookmark", "Annotations", "Set a bookmark"),
    GhidraTool("mcp__ghidra__get-comments", "Annotations", "Get comments"),
    GhidraTool("mcp__ghidra__set-comment", "Annotations", "Set a comment"),
    GhidraTool("mcp__ghidra__read-memory", "Memory", "Read memory"),
    GhidraTool("mcp__ghidra__get-memory-blocks", "Memory", "Get memory blocks"),
    GhidraTool("mcp__ghidra__list-project-files", "Project", "List project files"),
    GhidraTool("mcp__ghidra__import-file", "Project", "Import a file into the project"),
    GhidraTool("mcp__ghidra__get-data-types", "Types", "Get data types"),
    GhidraTool(
        "mcp__ghidra__get-data-type-by-string",
        "Types",
        "Look up a data type by string",
    ),
    GhidraTool("mcp__ghidra__apply-data-type", "Types", "Apply a data type"),
)

WORKFLOW_GUIDE: str = """
# Ghidra + Hacker Agent Workflow

## Phase 1 — Import & initial analysis
1. Import binary with the Ghidra MCP `import-file` tool
2. Run `analyze-program` to populate auto-analysis
3. Capture triage facts (architecture, entry point, language) into memory

## Phase 2 — Deep analysis (via MCP)
1. List functions with `get-functions`
2. Decompile candidates with `get-decompilation`
3. Find cross-references with `find-cross-references`
4. Search the decompilation for patterns with `search-decompilation`

## Phase 3 — Knowledge extraction
1. Identify cryptographic routines, anti-debug, IO / network
2. Annotate findings with `set-comment` / `set-bookmark`
3. Trace flows with `trace-data-flow-{backward,forward}`

## Phase 4 — Memory persistence
Store findings as `MemoryEntry` records via :class:`HackerMemorySystem`:
- `technique` — exploitation primitives recovered
- `tool`      — Ghidra recipes that worked
- `insight`   — design observations / config / keys
- `threat`    — IOCs / suspicious indicators
"""


class GhidraIntegration:
    """Catalog + memory-glue for the Ghidra MCP workflow."""

    def __init__(
        self,
        memory: HackerMemorySystem | None = None,
        *,
        project_dir: Path | None = None,
        project_name: str = "RE",
    ) -> None:
        self.memory: HackerMemorySystem = memory or HackerMemorySystem()
        self.project_dir: Path = (
            (
                project_dir
                or Path(os.environ.get("GHIDRA_PROJECT_DIR", "~/Projects/ghidra-re/projects"))
            )
            .expanduser()
            .resolve()
        )
        self.project_name: str = project_name

    @staticmethod
    def list_available_tools() -> tuple[GhidraTool, ...]:
        return GHIDRA_TOOLS

    @staticmethod
    def tools_by_category() -> dict[str, list[GhidraTool]]:
        grouped: dict[str, list[GhidraTool]] = {}
        for tool in GHIDRA_TOOLS:
            grouped.setdefault(tool.category, []).append(tool)
        for tools in grouped.values():
            tools.sort(key=lambda t: t.name)
        return grouped

    @staticmethod
    def workflow_guide() -> str:
        return WORKFLOW_GUIDE

    def record_analysis(
        self,
        binary_path: str | Path,
        *,
        triage: dict[str, Any] | None = None,
        entry_decompilation: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Persist a Ghidra analysis snapshot into the memory system."""
        target = Path(binary_path).expanduser()
        triage_info = triage or {}
        content = json.dumps(
            {
                "binary": target.name,
                "path": str(target),
                "triage": triage_info,
                "entry_decompilation": (entry_decompilation or "")[:2000],
                "notes": notes,
            },
            indent=2,
            default=str,
        )
        entry = MemoryEntry(
            category=MemoryCategory.TECHNIQUE,
            source="ghidra-analysis",
            content=content,
            tags=["ghidra", "reverse-engineering", "binary-analysis"],
            importance=8,
            confidence=0.9,
            context={"recorded_at": datetime.now(UTC).isoformat()},
        )
        memory_id = self.memory.learn(entry)

        if isinstance(triage_info, dict):
            architecture = triage_info.get("architecture")
            if architecture:
                self.memory.learn(
                    MemoryEntry(
                        category=MemoryCategory.INSIGHT,
                        source="ghidra-analysis",
                        content=f"Architecture: {architecture}",
                        tags=["ghidra", "architecture", target.name],
                        importance=7,
                        confidence=0.95,
                    )
                )
            interesting = triage_info.get("interesting_strings") or []
            if interesting:
                preview = ", ".join(map(str, interesting[:10]))
                self.memory.learn(
                    MemoryEntry(
                        category=MemoryCategory.THREAT,
                        source="ghidra-analysis",
                        content=f"Interesting strings found: {preview}",
                        tags=["ghidra", "strings", "indicators", target.name],
                        importance=6,
                        confidence=0.8,
                    )
                )

        logger.info("Recorded Ghidra analysis for %s as %s", target.name, memory_id)
        return memory_id


__all__ = ["GHIDRA_TOOLS", "WORKFLOW_GUIDE", "GhidraIntegration", "GhidraTool"]
