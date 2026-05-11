"""Tests for the NVD/CISA-KEV importer (offline; httpx is mocked)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from hacker_agent.cve import CVEImporter
from hacker_agent.memory import HackerMemorySystem, MemoryCategory


def _nvd_sample(cve_id: str = "CVE-2025-99999", cvss: float = 9.8) -> dict[str, Any]:
    return {
        "vulnerabilities": [
            {
                "cve": {
                    "id": cve_id,
                    "descriptions": [
                        {"lang": "en", "value": f"{cve_id} is a critical example vulnerability."}
                    ],
                    "weaknesses": [
                        {"description": [{"lang": "en", "value": "CWE-89"}]},
                    ],
                    "metrics": {
                        "cvssMetricV31": [{"cvssData": {"baseScore": cvss}}],
                    },
                },
                "configurations": {
                    "nodes": [
                        {"cpeMatch": [{"criteria": "cpe:2.3:a:acme:widget:1.0:*:*:*:*:*:*:*"}]}
                    ]
                },
            }
        ]
    }


def _kev_sample(cve_id: str = "CVE-2025-99999") -> dict[str, Any]:
    return {
        "vulnerabilities": [
            {
                "cveID": cve_id,
                "vendorProject": "Acme",
                "product": "Widget",
                "vulnerabilityName": "Acme Widget RCE",
                "dateAdded": "2026-01-15",
                "dueDate": "2026-02-05",
            }
        ]
    }


def _build_importer(memory: HackerMemorySystem, transport: httpx.MockTransport) -> CVEImporter:
    client = httpx.Client(transport=transport, headers={"User-Agent": "test"})
    return CVEImporter(memory=memory, client=client)


def test_import_recent_cves_persists_to_memory(memory: HackerMemorySystem) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "nvd.nist.gov" in request.url.host:
            return httpx.Response(200, json=_nvd_sample())
        if "cisa.gov" in request.url.host:
            return httpx.Response(200, json=_kev_sample())
        return httpx.Response(404)

    importer = _build_importer(memory, httpx.MockTransport(handler))
    try:
        stats = importer.import_recent_cves()
    finally:
        importer.close()

    assert stats.imported == 1
    assert stats.failed == 0
    rows = memory.recall("CVE-2025-99999")
    assert rows, "expected the imported CVE to be recallable"
    assert rows[0]["category"] == MemoryCategory.THREAT.value


def test_import_skips_low_severity_without_kev(memory: HackerMemorySystem) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "nvd.nist.gov" in request.url.host:
            return httpx.Response(200, json=_nvd_sample(cve_id="CVE-2025-00001", cvss=3.1))
        return httpx.Response(200, json={"vulnerabilities": []})

    importer = _build_importer(memory, httpx.MockTransport(handler))
    try:
        stats = importer.import_recent_cves()
    finally:
        importer.close()

    assert stats.imported == 0
    assert stats.skipped == 1
    assert not memory.recall("CVE-2025-00001")


def test_import_cisa_kev_only(memory: HackerMemorySystem) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_kev_sample("CVE-2024-12345"))

    importer = _build_importer(memory, httpx.MockTransport(handler))
    try:
        stats = importer.import_cisa_kev_only()
    finally:
        importer.close()

    assert stats.imported == 1
    rows = memory.recall("CVE-2024-12345")
    assert rows and rows[0]["importance"] == 10


def test_parse_cvss_score_handles_missing_metrics() -> None:
    assert CVEImporter.parse_cvss_score({"cve": {}}) == 0.0


def test_extract_tags_dedupes_and_caps() -> None:
    item = _nvd_sample()["vulnerabilities"][0]
    tags = CVEImporter.extract_tags(item)
    assert "cve" in tags
    assert "vulnerability" in tags
    assert any(t.startswith("cwe-") for t in tags)
    assert len(tags) <= 10


@pytest.mark.parametrize(
    "score,exploited,expected",
    [
        (9.8, False, 9),
        (9.8, True, 10),
        (5.0, True, 7),
        (1.5, False, 1),
    ],
)
def test_calculate_importance(score: float, exploited: bool, expected: int) -> None:
    assert CVEImporter.calculate_importance(score, exploited) == expected
