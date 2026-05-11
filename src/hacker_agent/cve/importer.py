"""NVD + CISA KEV CVE importer (direct imports, no subprocess shelling)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from hacker_agent.config import SETTINGS
from hacker_agent.memory import HackerMemorySystem, MemoryCategory, MemoryEntry

logger = logging.getLogger(__name__)

USER_AGENT: str = "Hacker-Agent-CVE-Importer/0.2"
DEFAULT_TIMEOUT: float = 30.0
MAX_TAGS: int = 10


@dataclass(slots=True)
class ImportStats:
    """Counters returned from an import run."""

    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class CVEImporter:
    """Fetch CVE feeds and stream them straight into the memory subsystem."""

    def __init__(
        self,
        memory: HackerMemorySystem | None = None,
        *,
        days_back: int = 7,
        nvd_api_base: str | None = None,
        cisa_kev_url: str | None = None,
        client: httpx.Client | None = None,
        min_cvss_unless_kev: float = 7.0,
    ) -> None:
        self.memory: HackerMemorySystem = memory or HackerMemorySystem()
        self.days_back: int = days_back
        self.nvd_api_base: str = nvd_api_base or SETTINGS.nvd_api_base
        self.cisa_kev_url: str = cisa_kev_url or SETTINGS.cisa_kev_url
        self.min_cvss_unless_kev: float = min_cvss_unless_kev
        self._owns_client: bool = client is None
        self._client: httpx.Client = client or httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> CVEImporter:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def fetch_nvd_recent(self) -> list[dict[str, Any]]:
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=self.days_back)
        params: dict[str, str] = {
            "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": "100",
        }
        try:
            response = self._client.get(self.nvd_api_base, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("NVD fetch failed: %s", exc)
            return []
        except ValueError as exc:
            logger.warning("NVD response not JSON: %s", exc)
            return []
        return list(payload.get("vulnerabilities", []))

    def fetch_cisa_kev(self) -> list[dict[str, Any]]:
        try:
            response = self._client.get(self.cisa_kev_url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("CISA KEV fetch failed: %s", exc)
            return []
        except ValueError as exc:
            logger.warning("CISA KEV response not JSON: %s", exc)
            return []
        return list(payload.get("vulnerabilities", []))

    @staticmethod
    def parse_cvss_score(cve_item: dict[str, Any]) -> float:
        metrics = cve_item.get("cve", {}).get("metrics", {})
        for version in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = metrics.get(version)
            if entries:
                try:
                    return float(entries[0].get("cvssData", {}).get("baseScore", 0.0))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    @staticmethod
    def calculate_importance(cvss_score: float, exploited: bool = False) -> int:
        base = min(10, max(1, int(cvss_score)))
        if exploited and cvss_score >= 7.0:
            return 10
        if exploited:
            return min(10, base + 2)
        return base

    @staticmethod
    def extract_tags(cve_item: dict[str, Any]) -> list[str]:
        tags: set[str] = {"cve", "vulnerability"}
        cve_data = cve_item.get("cve", {})
        for weakness in cve_data.get("weaknesses", []):
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe = desc.get("value", "")
                    if cwe.startswith("CWE-"):
                        tags.add(cwe.lower())
        for config in cve_item.get("configurations", {}).get("nodes", []):
            for cpe_match in config.get("cpeMatch", []):
                criteria = cpe_match.get("criteria", "")
                if not criteria.startswith("cpe:2.3:"):
                    continue
                parts = criteria.split(":")
                if len(parts) >= 5:
                    vendor, product = parts[3], parts[4]
                    if vendor:
                        tags.add(vendor)
                    if product:
                        tags.add(product)
        return sorted(tags)[:MAX_TAGS]

    @staticmethod
    def format_description(cve_item: dict[str, Any]) -> str:
        cve_id = cve_item.get("cve", {}).get("id", "Unknown")
        descriptions = cve_item.get("cve", {}).get("descriptions", [])
        desc_text = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                desc_text = desc.get("value", "")
                break
        cvss_score = CVEImporter.parse_cvss_score(cve_item)
        return f"{cve_id}: {desc_text} (CVSS: {cvss_score})"

    def add_to_memory(self, cve_item: dict[str, Any], *, exploited: bool = False) -> bool:
        cve_id = cve_item.get("cve", {}).get("id", "")
        if not cve_id:
            return False
        cvss_score = self.parse_cvss_score(cve_item)
        importance = self.calculate_importance(cvss_score, exploited)
        tags = self.extract_tags(cve_item)
        content = self.format_description(cve_item)
        if exploited:
            tags = sorted({*tags, "exploited-in-wild", "cisa-kev"})

        entry = MemoryEntry(
            category=MemoryCategory.THREAT,
            source=cve_id,
            content=content,
            tags=tags,
            importance=importance,
            confidence=0.95 if exploited else 0.85,
            context={"cvss": cvss_score, "exploited": exploited},
        )
        self.memory.learn(entry)
        return True

    def import_recent_cves(self) -> ImportStats:
        stats = ImportStats()
        logger.info("Fetching CVEs from last %s days", self.days_back)
        cves = self.fetch_nvd_recent()
        logger.info("Found %d CVEs", len(cves))

        logger.info("Fetching CISA KEV catalog")
        kev_list = self.fetch_cisa_kev()
        kev_cves = {v.get("cveID") for v in kev_list if v.get("cveID")}
        logger.info("KEV catalog has %d entries", len(kev_cves))

        for cve_item in cves:
            cve_id = cve_item.get("cve", {}).get("id", "")
            cvss_score = self.parse_cvss_score(cve_item)
            exploited = cve_id in kev_cves
            if cvss_score < self.min_cvss_unless_kev and not exploited:
                stats.skipped += 1
                continue
            try:
                if self.add_to_memory(cve_item, exploited=exploited):
                    stats.imported += 1
                else:
                    stats.failed += 1
            except Exception as exc:
                stats.failed += 1
                stats.errors.append(f"{cve_id}: {exc}")
                logger.exception("Failed to import %s", cve_id)
        return stats

    def import_cisa_kev_only(self) -> ImportStats:
        stats = ImportStats()
        logger.info("Fetching CISA KEV catalog")
        kev_entries = self.fetch_cisa_kev()
        logger.info("Found %d KEV entries", len(kev_entries))
        for entry in kev_entries:
            cve_id = entry.get("cveID", "")
            if not cve_id:
                stats.skipped += 1
                continue
            vendor = entry.get("vendorProject", "")
            product = entry.get("product", "")
            vulnerability = entry.get("vulnerabilityName", "")
            date_added = entry.get("dateAdded", "")
            due_date = entry.get("dueDate", "")
            content = (
                f"{cve_id}: {vulnerability} - {vendor} {product}. "
                f"CISA KEV (Added: {date_added}, Due: {due_date}). Exploited in the wild."
            )
            tags = sorted(
                {
                    "cisa-kev",
                    "exploited-in-wild",
                    "cisa-catalog",
                    vendor.lower(),
                    product.lower(),
                }
            )
            try:
                memory_entry = MemoryEntry(
                    category=MemoryCategory.THREAT,
                    source=cve_id,
                    content=content,
                    tags=[t for t in tags if t],
                    importance=10,
                    confidence=0.99,
                    context={"date_added": date_added, "due_date": due_date},
                )
                self.memory.learn(memory_entry)
                stats.imported += 1
            except Exception as exc:
                stats.failed += 1
                stats.errors.append(f"{cve_id}: {exc}")
                logger.exception("Failed to import KEV %s", cve_id)
        return stats


__all__ = ["CVEImporter", "ImportStats"]
