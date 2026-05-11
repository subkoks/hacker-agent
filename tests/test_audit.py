"""Tests for the audit checklist generator."""

from __future__ import annotations

import json

import pytest

from hacker_agent.audit import AVAILABLE_AUDIT_TYPES, AuditChecklistGenerator


@pytest.mark.parametrize("audit_type", AVAILABLE_AUDIT_TYPES)
def test_generate_each_audit_type(audit_type: str) -> None:
    checklist = AuditChecklistGenerator.generate(audit_type, target="example.com")
    assert checklist["audit_type"] == audit_type
    assert checklist["target"] == "example.com"
    assert checklist["total_items"] > 0
    assert checklist["categories"]


def test_generate_all_returns_every_type() -> None:
    all_checklists = AuditChecklistGenerator.generate_all(target=None)
    assert set(all_checklists.keys()) == set(AVAILABLE_AUDIT_TYPES)


def test_unknown_audit_type_raises() -> None:
    with pytest.raises(ValueError):
        AuditChecklistGenerator.generate("not-a-real-type")


def test_markdown_format_contains_headings() -> None:
    checklist = AuditChecklistGenerator.generate("web-application", target="acme.test")
    md = AuditChecklistGenerator.format_markdown(checklist)
    assert "# Web Application Security Audit" in md
    assert "- [ ]" in md
    assert "acme.test" in md


def test_html_format_is_well_formed() -> None:
    checklist = AuditChecklistGenerator.generate("api-security")
    html = AuditChecklistGenerator.format_html(checklist)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "API Security Audit" in html


def test_json_format_round_trips() -> None:
    checklist = AuditChecklistGenerator.generate("infrastructure")
    serialized = json.dumps(checklist, default=str)
    restored = json.loads(serialized)
    assert restored["name"] == "Infrastructure Security Audit"
