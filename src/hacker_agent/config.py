"""Central path / config resolution for hacker-agent.

Single source of truth for *every* on-disk path. Never hardcode absolute paths
anywhere else — read them from here. Env overrides take priority, then
project-relative defaults under the resolved project root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path:
    """Locate the project root by walking up from this file.

    The package lives at ``<root>/src/hacker_agent/config.py`` in dev installs
    and at ``site-packages/hacker_agent/config.py`` in installed wheels. In the
    wheel case we fall back to the current working directory.
    """
    here = Path(__file__).resolve()
    # src/hacker_agent/config.py -> src/hacker_agent -> src -> root
    candidate = here.parents[2] if len(here.parents) >= 3 else here.parent
    if (candidate / "pyproject.toml").exists():
        return candidate
    return Path.cwd()


def _env_path(name: str, default: Path) -> Path:
    """Resolve an env-overridable path. Relative env values are project-relative."""
    raw = os.environ.get(name)
    if not raw:
        return default
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate
    return (_project_root() / candidate).resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved runtime settings — pathlib only, no os.path."""

    project_root: Path
    data_dir: Path
    memory_db: Path
    logs_dir: Path
    backups_dir: Path
    nvd_api_base: str
    cisa_kev_url: str
    auto_commit_branch_prefix: str

    def ensure_dirs(self) -> None:
        """Create runtime directories on demand (idempotent)."""
        for directory in (self.data_dir, self.logs_dir, self.backups_dir):
            directory.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Build a :class:`Settings` instance from env + sensible defaults."""
    root = _project_root()
    data_dir = _env_path("HACKER_DATA_DIR", root / "data")
    memory_db = _env_path("HACKER_MEMORY_DB", data_dir / "hacker-memory.db")
    logs_dir = _env_path("HACKER_LOG_DIR", root / "logs")
    backups_dir = _env_path("HACKER_BACKUP_DIR", root / "backups")

    return Settings(
        project_root=root,
        data_dir=data_dir,
        memory_db=memory_db,
        logs_dir=logs_dir,
        backups_dir=backups_dir,
        nvd_api_base=os.environ.get(
            "NVD_API_BASE",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
        ),
        cisa_kev_url=os.environ.get(
            "CISA_KEV_URL",
            "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        ),
        auto_commit_branch_prefix=os.environ.get(
            "AUTO_COMMIT_BRANCH_PREFIX",
            "auto/",
        ),
    )


SETTINGS: Settings = load_settings()

__all__ = ["SETTINGS", "Settings", "load_settings"]
