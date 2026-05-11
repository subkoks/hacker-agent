"""Hacker Agent CLI — unified Typer entry point.

The interface mirrors the old argparse CLI but is delivered as a proper
package script (`hacker-agent` / `python -m hacker_agent`).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from hacker_agent import __version__
from hacker_agent.audit import AVAILABLE_AUDIT_TYPES, AuditChecklistGenerator
from hacker_agent.config import SETTINGS
from hacker_agent.cve import CVEImporter
from hacker_agent.ghidra import GhidraIntegration
from hacker_agent.memory import HackerMemorySystem, MemoryCategory, MemoryEntry
from hacker_agent.stake import GameTemplates, StakeEngineGameMath

logger = logging.getLogger("hacker_agent")
console = Console()

app = typer.Typer(
    name="hacker-agent",
    help="Permanent-memory security research and reverse-engineering toolkit.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

memory_app = typer.Typer(help="Permanent memory + auto-learning operations.", no_args_is_help=True)
cve_app = typer.Typer(help="NVD / CISA KEV CVE ingestion.", no_args_is_help=True)
audit_app = typer.Typer(help="Security audit checklist generation.", no_args_is_help=True)
stake_app = typer.Typer(
    help="Stake Engine RGS templates + provably-fair math.", no_args_is_help=True
)
ghidra_app = typer.Typer(help="Ghidra MCP bridge.", no_args_is_help=True)

app.add_typer(memory_app, name="memory")
app.add_typer(cve_app, name="cve")
app.add_typer(audit_app, name="audit")
app.add_typer(stake_app, name="stake")
app.add_typer(ghidra_app, name="ghidra")


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"hacker-agent {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", help="Show version and exit.", callback=_version_callback, is_eager=True
        ),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose logging.")] = False,
) -> None:
    """Root callback — sets logging level, prints version if requested."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )


def _split_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [t.strip() for t in value.split(",") if t.strip()]


def _memory() -> HackerMemorySystem:
    return HackerMemorySystem()


# ---------------------------------------------------------------------------
# Top-level convenience commands (preserve old CLI ergonomics)
# ---------------------------------------------------------------------------


@app.command("learn")
def cli_learn(
    content: Annotated[str, typer.Option("--content", help="Knowledge content.")],
    category: Annotated[MemoryCategory, typer.Option("--category")] = MemoryCategory.TECHNIQUE,
    importance: Annotated[int, typer.Option("--importance", min=1, max=10)] = 5,
    tags: Annotated[str, typer.Option("--tags", help="Comma-separated tags.")] = "",
    source: Annotated[str, typer.Option("--source")] = "cli",
) -> None:
    """Record a new memory entry."""
    entry = MemoryEntry(
        category=category,
        source=source,
        content=content,
        tags=_split_tags(tags),
        importance=importance,
    )
    memory_id = _memory().learn(entry)
    console.print(f"[green]Learned:[/green] {memory_id}")


@app.command("recall")
def cli_recall(
    query: Annotated[str, typer.Option("--query")],
    category: Annotated[MemoryCategory | None, typer.Option("--category")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 10,
    min_importance: Annotated[int, typer.Option("--min-importance", min=1, max=10)] = 1,
) -> None:
    """Search the permanent memory."""
    results = _memory().recall(query, category=category, limit=limit, min_importance=min_importance)
    console.print_json(json.dumps(results, indent=2, default=str))


@app.command("search")
def cli_search(query: Annotated[str, typer.Option("--query")]) -> None:
    """Free-text search across the memory store."""
    results = _memory().recall(query, limit=50)
    console.print_json(json.dumps(results, indent=2, default=str))


@app.command("list")
def cli_list(
    category: Annotated[MemoryCategory | None, typer.Option("--category")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 20,
) -> None:
    """List recent memories."""
    rows = _memory().list_recent(category=category, limit=limit)
    console.print_json(json.dumps(rows, indent=2, default=str))


@app.command("stats")
def cli_stats() -> None:
    """Show aggregate memory statistics."""
    console.print_json(json.dumps(_memory().statistics(), indent=2, default=str))


@app.command("consolidate")
def cli_consolidate() -> None:
    """Run knowledge consolidation."""
    console.print_json(json.dumps(_memory().consolidate_knowledge(), indent=2, default=str))


@app.command("recommend")
def cli_recommend(
    context: Annotated[
        str, typer.Option("--context", help='JSON context, e.g. \'{"technology":"GraphQL"}\'.')
    ],
) -> None:
    """Return technique recommendations for a context."""
    parsed = json.loads(context)
    recs = _memory().get_recommendations(parsed)
    console.print_json(recs.model_dump_json(indent=2))


@app.command("gaps")
def cli_gaps(
    context: Annotated[str, typer.Option("--context")],
) -> None:
    """Identify knowledge gaps for an engagement context."""
    parsed = json.loads(context)
    gaps = _memory().identify_knowledge_gaps(parsed)
    console.print_json(json.dumps(gaps, indent=2))


@app.command("auto-learn")
def cli_auto_learn(source: Annotated[str, typer.Option("--source")] = "mixed") -> None:
    """Run the auto-learn cycle."""
    stats = _memory().auto_learn(source)
    console.print_json(stats.model_dump_json(indent=2))


@app.command("export")
def cli_export(filepath: Annotated[Path | None, typer.Option("--filepath")] = None) -> None:
    """Export a brain dump JSON to disk."""
    output = _memory().export_brain_dump(filepath)
    console.print(f"[green]Exported to:[/green] {output}")


@app.command("import")
def cli_import(
    filepath: Annotated[Path, typer.Option("--filepath")],
    merge: Annotated[bool, typer.Option("--merge/--replace")] = True,
) -> None:
    """Import a brain dump JSON into memory."""
    count = _memory().import_knowledge(filepath, merge=merge)
    console.print(f"[green]Imported[/green] {count} entries from {filepath}")


@app.command("quick")
def cli_quick(topic: Annotated[str, typer.Option("--topic")]) -> None:
    """Quick reference lookup — top 5 entries on a topic."""
    console.print(f":mag: Quick reference: [bold]{topic}[/bold]")
    rows = _memory().recall(topic, limit=5)
    console.print_json(json.dumps(rows, indent=2, default=str))


@app.command("cheatsheet")
def cli_cheatsheet(tool_name: Annotated[str, typer.Option("--tool-name")]) -> None:
    """Show cheatsheet for a specific tool."""
    console.print(f":clipboard: Cheatsheet for [bold]{tool_name}[/bold]")
    tool_rows = _memory().recall(tool_name, category=MemoryCategory.TOOL, limit=3)
    console.print_json(json.dumps(tool_rows, indent=2, default=str))
    console.print(":bulb: Related techniques:")
    tech_rows = _memory().recall(tool_name, category=MemoryCategory.TECHNIQUE, limit=3)
    console.print_json(json.dumps(tech_rows, indent=2, default=str))


@app.command("cve-check")
def cli_cve_check(cve_id: Annotated[str, typer.Option("--cve-id")]) -> None:
    """Check whether a specific CVE id is in memory."""
    console.print(f":mag: Checking for [bold]{cve_id}[/bold]")
    rows = _memory().recall(cve_id, limit=10)
    console.print_json(json.dumps(rows, indent=2, default=str))


@app.command("tech-stack")
def cli_tech_stack(technology: Annotated[str, typer.Option("--technology")]) -> None:
    """Analyze a target technology stack with the agent memory."""
    mem = _memory()
    console.print(f":dart: Tech stack analysis: [bold]{technology}[/bold]")
    console.print("[underline]Known techniques[/underline]")
    console.print_json(json.dumps(mem.recall(technology, limit=5), indent=2, default=str))
    context = {"technology": technology, "target_type": "web"}
    console.print("[underline]Knowledge gaps[/underline]")
    console.print_json(json.dumps(mem.identify_knowledge_gaps(context), indent=2))
    console.print("[underline]Recommendations[/underline]")
    console.print_json(mem.get_recommendations(context).model_dump_json(indent=2))


@app.command("browse")
def cli_browse(
    category: Annotated[MemoryCategory | None, typer.Option("--category")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 50,
) -> None:
    """Browse recent memories in a compact table."""
    rows = _memory().list_recent(category=category, limit=limit)
    if not rows:
        console.print("[yellow]No memories found.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=14)
    table.add_column("Time", width=20)
    table.add_column("Cat", width=10)
    table.add_column("Imp", width=4, justify="right")
    table.add_column("Content")
    for row in rows:
        preview = (row.get("content") or "")[:64]
        ts = (row.get("timestamp") or "")[:19]
        table.add_row(
            str(row.get("id", ""))[:14],
            ts,
            str(row.get("category", "")),
            str(row.get("importance", "")),
            preview,
        )
    console.print(table)


@app.command("dashboard")
def cli_dashboard() -> None:
    """Knowledge dashboard."""
    mem = _memory()
    data = mem.consolidate_knowledge()
    stats = data.get("statistics", {})
    console.rule("Hacker Agent Knowledge Dashboard")
    console.print_json(json.dumps(stats, indent=2, default=str))

    categories_table = Table(title="Category Distribution")
    categories_table.add_column("Category")
    categories_table.add_column("Count", justify="right")
    for cat in MemoryCategory:
        entries = data.get("categories", {}).get(cat.value, [])
        categories_table.add_row(cat.value, str(len(entries)))
    console.print(categories_table)

    tag_counter: Counter[str] = Counter()
    for entries in data.get("categories", {}).values():
        for entry in entries:
            tags_raw = entry.get("tags") or "[]"
            try:
                tags = json.loads(tags_raw) if isinstance(tags_raw, str) else list(tags_raw)
            except (TypeError, ValueError):
                tags = []
            tag_counter.update(t for t in tags if t)
    if tag_counter:
        top_tags = Table(title="Top Tags")
        top_tags.add_column("Tag")
        top_tags.add_column("Count", justify="right")
        for tag, count in tag_counter.most_common(10):
            top_tags.add_row(tag, str(count))
        console.print(top_tags)


# ---------------------------------------------------------------------------
# `memory` sub-app (alternate namespacing)
# ---------------------------------------------------------------------------


@memory_app.command("path")
def memory_path() -> None:
    """Print the resolved SQLite db path."""
    console.print(str(SETTINGS.memory_db))


@memory_app.command("export")
def memory_export(filepath: Annotated[Path | None, typer.Option("--filepath")] = None) -> None:
    """Export brain dump (same as top-level `export`)."""
    output = _memory().export_brain_dump(filepath)
    console.print(f"[green]Exported to:[/green] {output}")


@memory_app.command("import")
def memory_import(
    filepath: Annotated[Path, typer.Argument(help="Brain-dump JSON path.")],
    merge: Annotated[bool, typer.Option("--merge/--replace")] = True,
) -> None:
    """Import a brain dump."""
    count = _memory().import_knowledge(filepath, merge=merge)
    console.print(f"[green]Imported[/green] {count} entries from {filepath}")


# ---------------------------------------------------------------------------
# `cve` sub-app
# ---------------------------------------------------------------------------


@cve_app.command("import")
def cve_import(
    days: Annotated[int, typer.Option("--days", min=1, max=120)] = 7,
    kev_only: Annotated[bool, typer.Option("--kev-only/--no-kev-only")] = False,
    show_stats: Annotated[bool, typer.Option("--stats/--no-stats")] = False,
) -> None:
    """Import recent CVEs (NVD) and/or the CISA KEV catalog."""
    with CVEImporter(days_back=days) as importer:
        result = importer.import_cisa_kev_only() if kev_only else importer.import_recent_cves()
    console.print(
        f"[green]Imported:[/green] {result.imported}  "
        f"[yellow]Skipped:[/yellow] {result.skipped}  "
        f"[red]Failed:[/red] {result.failed}"
    )
    if result.errors:
        console.print("[red]Errors:[/red]")
        for err in result.errors[:20]:
            console.print(f"  - {err}")
    if show_stats:
        console.print_json(json.dumps(_memory().statistics(), indent=2, default=str))


# ---------------------------------------------------------------------------
# `audit` sub-app
# ---------------------------------------------------------------------------


@audit_app.command("list")
def audit_list() -> None:
    """List available audit checklist types."""
    table = Table(title="Available audit types")
    table.add_column("Key")
    table.add_column("Name")
    for key in AVAILABLE_AUDIT_TYPES:
        table.add_row(key, AuditChecklistGenerator.CHECKLISTS[key]["name"])
    console.print(table)


@audit_app.command("generate")
def audit_generate(
    audit_type: Annotated[str, typer.Option("--type", "-t")],
    target: Annotated[str | None, typer.Option("--target")] = None,
    fmt: Annotated[str, typer.Option("--format", help="markdown | json | html")] = "markdown",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Generate one (or all) audit checklists."""
    if audit_type == "all":
        bundles = AuditChecklistGenerator.generate_all(target)
    else:
        bundles = {audit_type: AuditChecklistGenerator.generate(audit_type, target)}
    parts: list[str] = []
    for checklist in bundles.values():
        if fmt == "json":
            parts.append(json.dumps(checklist, indent=2, default=str))
        elif fmt == "html":
            parts.append(AuditChecklistGenerator.format_html(checklist))
        else:
            parts.append(AuditChecklistGenerator.format_markdown(checklist))
    body = "\n\n---\n\n".join(parts)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
        console.print(f"[green]Saved:[/green] {output}")
    else:
        console.print(body)


# ---------------------------------------------------------------------------
# `stake` sub-app
# ---------------------------------------------------------------------------


@stake_app.command("template")
def stake_template(
    game: Annotated[str, typer.Option("--game", help="crash|dice|slots|plinko|all")] = "all",
) -> None:
    """Print a reference game template."""
    console.print(GameTemplates.get(game))


@stake_app.command("verify-rtp")
def stake_verify_rtp(
    game: Annotated[str, typer.Option("--game")] = "crash",
    rounds: Annotated[int, typer.Option("--rounds", min=1_000, max=10_000_000)] = 100_000,
    cash_out_at: Annotated[float, typer.Option("--cash-out-at")] = 2.0,
) -> None:
    """Run a quick simulated RTP verification."""
    if game != "crash":
        raise typer.BadParameter("Only 'crash' RTP simulation is implemented today.")
    result = StakeEngineGameMath.simulate_crash_rtp(rounds=rounds, cash_out_at=cash_out_at)
    console.print_json(json.dumps(result.__dict__, indent=2))


@stake_app.command("seeds")
def stake_seeds() -> None:
    """Generate a fresh server seed + hash pair (for local testing only)."""
    seed, seed_hash = StakeEngineGameMath.generate_server_seed()
    console.print_json(json.dumps({"server_seed": seed, "server_seed_hash": seed_hash}, indent=2))


# ---------------------------------------------------------------------------
# `ghidra` sub-app
# ---------------------------------------------------------------------------


@ghidra_app.command("tools")
def ghidra_tools() -> None:
    """List the Ghidra MCP tool catalog known to this agent."""
    table = Table(title=f"Ghidra MCP tools ({len(GhidraIntegration.list_available_tools())})")
    table.add_column("Category", style="bold")
    table.add_column("Tool")
    table.add_column("Description")
    for category, tools in GhidraIntegration.tools_by_category().items():
        for tool in tools:
            table.add_row(category, tool.name, tool.description)
    console.print(table)


@ghidra_app.command("guide")
def ghidra_guide() -> None:
    """Print the Ghidra + Hacker Agent workflow guide."""
    console.print(GhidraIntegration.workflow_guide())


@ghidra_app.command("record")
def ghidra_record(
    binary: Annotated[Path, typer.Option("--binary")],
    triage_json: Annotated[Path | None, typer.Option("--triage")] = None,
    decompilation: Annotated[Path | None, typer.Option("--entry-decompilation")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Record a Ghidra analysis snapshot into the memory store."""
    triage: dict[str, Any] | None = None
    if triage_json:
        triage = json.loads(triage_json.read_text(encoding="utf-8"))
    decomp_text: str | None = None
    if decompilation:
        decomp_text = decompilation.read_text(encoding="utf-8")
    memory_id = GhidraIntegration().record_analysis(
        binary,
        triage=triage,
        entry_decompilation=decomp_text,
        notes=notes,
    )
    console.print(
        f"[green]Recorded:[/green] {memory_id} @ {datetime.now(UTC).isoformat()} for {binary.name}"
    )


def main() -> None:
    """Entry point used by `python -m hacker_agent` and the console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
