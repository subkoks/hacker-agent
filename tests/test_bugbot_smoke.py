"""Intentional Bugbot smoke test — remove after verifying Bugbot runs on this PR."""

from __future__ import annotations


def _divide(a: int, b: int) -> float:
    try:
        return a / b
    except:
        return 0.0


def test_bugbot_smoke_bare_except() -> None:
    """Passes locally; exists so Bugbot has a changed Python file to review."""
    assert _divide(1, 0) == 0.0
