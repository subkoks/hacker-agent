"""Tests for the Stake Engine game-math + templates module."""

from __future__ import annotations

import hashlib

import pytest

from hacker_agent.stake import GameTemplates, StakeEngineGameMath


def test_generate_server_seed_returns_hashed_pair() -> None:
    seed, seed_hash = StakeEngineGameMath.generate_server_seed()
    assert len(seed) == 64
    assert hashlib.sha256(seed.encode()).hexdigest() == seed_hash


def test_generate_result_is_deterministic() -> None:
    a = StakeEngineGameMath.generate_result("server", "client", 42)
    b = StakeEngineGameMath.generate_result("server", "client", 42)
    assert a == b
    assert 0.0 <= a <= 1.0


def test_crash_result_bounds() -> None:
    seed, _ = StakeEngineGameMath.generate_server_seed()
    for nonce in range(100):
        m = StakeEngineGameMath.crash_game_result(seed, "client", nonce)
        assert 1.0 <= m <= 1000.0


def test_dice_result_bounds() -> None:
    seed, _ = StakeEngineGameMath.generate_server_seed()
    for nonce in range(100):
        v = StakeEngineGameMath.dice_game_result(seed, "client", nonce)
        assert 0.0 <= v <= 100.0


def test_dice_payout_math() -> None:
    payout_under = StakeEngineGameMath.dice_payout(25.0, 50.0, is_under=True)
    payout_over = StakeEngineGameMath.dice_payout(75.0, 50.0, is_under=False)
    payout_loss = StakeEngineGameMath.dice_payout(60.0, 50.0, is_under=True)
    assert payout_under == pytest.approx(1.98, abs=0.001)
    assert payout_over == pytest.approx(1.98, abs=0.001)
    assert payout_loss == 0.0


def test_plinko_returns_valid_path() -> None:
    seed, _ = StakeEngineGameMath.generate_server_seed()
    result = StakeEngineGameMath.plinko_result(seed, "client", nonce=1, rows=8, risk="medium")
    assert len(result["path"]) == 8
    assert result["multiplier"] > 0


def test_verify_crash_fairness() -> None:
    seed, seed_hash = StakeEngineGameMath.generate_server_seed()
    m = StakeEngineGameMath.crash_game_result(seed, "client", 7)
    assert StakeEngineGameMath.verify_crash_fairness(seed, seed_hash, "client", 7, m)
    assert not StakeEngineGameMath.verify_crash_fairness(seed, seed_hash, "client", 7, m + 1)


@pytest.mark.slow
def test_simulate_crash_rtp_within_tolerance() -> None:
    result = StakeEngineGameMath.simulate_crash_rtp(rounds=10_000)
    # RTP estimator over only 10k rounds is noisy; we just sanity-check magnitudes.
    assert 0.0 <= result.actual_rtp <= 2.0
    assert result.rounds == 10_000


def test_game_templates_known_games() -> None:
    for game in ("crash", "dice", "slots", "plinko"):
        assert "class" in GameTemplates.get(game)
    assert "Crash" in GameTemplates.get("all")
    with pytest.raises(ValueError):
        GameTemplates.get("nonexistent")
