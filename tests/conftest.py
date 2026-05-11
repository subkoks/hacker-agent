"""Pytest fixtures — isolate every test from the real on-disk memory db."""

from __future__ import annotations

import os
from collections.abc import Iterator
from importlib import reload
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point every path-aware env var at a per-test tmp directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("HACKER_DATA_DIR", str(data_dir))
    monkeypatch.setenv("HACKER_MEMORY_DB", str(data_dir / "hacker-memory.db"))
    monkeypatch.setenv("HACKER_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("HACKER_BACKUP_DIR", str(tmp_path / "backups"))
    # Force config re-resolution under the new env.
    import hacker_agent.config as cfg

    reload(cfg)
    # Re-import downstream modules that cached SETTINGS at import time.
    import hacker_agent.memory.db as db_module

    reload(db_module)
    yield tmp_path
    # Restore default state for any leftover module caches.
    for var in ("HACKER_DATA_DIR", "HACKER_MEMORY_DB", "HACKER_LOG_DIR", "HACKER_BACKUP_DIR"):
        os.environ.pop(var, None)
    reload(cfg)
    reload(db_module)


@pytest.fixture()
def memory():
    """Provide a fresh HackerMemorySystem rooted at the tmp data dir."""
    from hacker_agent.memory import HackerMemorySystem

    return HackerMemorySystem()
