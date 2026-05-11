"""Stake Engine RGS templates + provably-fair game math.

All randomness uses HMAC-SHA256 over `client_seed:nonce` keyed by `server_seed`,
the standard provably-fair construction.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from dataclasses import dataclass
from typing import Any, ClassVar

CRASH_HOUSE_EDGE: float = 0.01
DICE_HOUSE_EDGE: float = 0.01
CRASH_MAX_MULTIPLIER: float = 1000.0
SEED_ALPHABET: str = string.ascii_letters + string.digits


@dataclass(slots=True)
class RTPResult:
    """Simulation result for RTP verification."""

    game: str
    rounds: int
    total_bet: float
    total_return: float
    actual_rtp: float
    expected_rtp: float
    average_multiplier: float
    median_multiplier: float


class StakeEngineGameMath:
    """Provably-fair game math (Stake Engine RGS reference)."""

    @staticmethod
    def generate_server_seed() -> tuple[str, str]:
        server_seed = "".join(secrets.choice(SEED_ALPHABET) for _ in range(64))
        server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
        return server_seed, server_seed_hash

    @staticmethod
    def generate_result(server_seed: str, client_seed: str, nonce: int) -> float:
        message = f"{client_seed}:{nonce}"
        digest = hmac.new(server_seed.encode(), message.encode(), hashlib.sha256).hexdigest()
        int_value = int(digest[:16], 16)
        return int_value / (2**64)

    @staticmethod
    def crash_game_result(
        server_seed: str,
        client_seed: str,
        nonce: int,
        house_edge: float = CRASH_HOUSE_EDGE,
        max_multiplier: float = CRASH_MAX_MULTIPLIER,
    ) -> float:
        rand = StakeEngineGameMath.generate_result(server_seed, client_seed, nonce)
        effective_rand = rand * (1 - house_edge)
        if effective_rand <= 0:
            return max_multiplier
        multiplier = max(1.0, min(max_multiplier, 99.0 / (effective_rand * 100)))
        return round(multiplier, 2)

    @staticmethod
    def dice_game_result(server_seed: str, client_seed: str, nonce: int) -> float:
        rand = StakeEngineGameMath.generate_result(server_seed, client_seed, nonce)
        result = (rand * 10000) % 10000
        return round(result / 100, 2)

    @staticmethod
    def dice_payout(result: float, target: float, is_under: bool = True) -> float:
        if is_under:
            won = result < target
            probability = target / 100
        else:
            won = result > target
            probability = (100 - target) / 100
        if not won or probability <= 0:
            return 0.0
        return round((1 - DICE_HOUSE_EDGE) / probability, 4)

    @staticmethod
    def slots_result(
        server_seed: str,
        client_seed: str,
        nonce: int,
        reels: list[list[str]],
        paylines: int = 20,
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for i, reel in enumerate(reels):
            reel_rand = StakeEngineGameMath.generate_result(
                server_seed, f"{client_seed}:reel{i}", nonce
            )
            position = int(reel_rand * len(reel)) % len(reel)
            results.append({"reel_index": i, "position": position, "symbol": reel[position]})
        return {"reels": results, "paylines": paylines}

    @staticmethod
    def plinko_result(
        server_seed: str,
        client_seed: str,
        nonce: int,
        rows: int = 16,
        risk: str = "medium",
    ) -> dict[str, Any]:
        multipliers = {
            "low": [0.5, 0.7, 0.9, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
            "medium": [0.3, 0.5, 0.8, 1.0, 1.5, 3.0, 5.0, 10.0, 25.0],
            "high": [0.2, 0.3, 0.5, 0.8, 1.0, 3.0, 10.0, 30.0, 100.0],
        }
        path: list[int] = []
        position = rows // 2
        for row in range(rows):
            rand = StakeEngineGameMath.generate_result(
                server_seed, f"{client_seed}:plinko:{row}", nonce
            )
            direction = -1 if rand < 0.5 else 1
            position += direction
            position = max(0, min(position, row + 1))
            path.append(direction)
        multiplier_list = multipliers.get(risk, multipliers["medium"])
        bucket = min(position, len(multiplier_list) - 1)
        return {"path": path, "final_position": position, "multiplier": multiplier_list[bucket]}

    @staticmethod
    def verify_crash_fairness(
        server_seed: str,
        server_seed_hash: str,
        client_seed: str,
        nonce: int,
        result: float,
    ) -> bool:
        expected_hash = hashlib.sha256(server_seed.encode()).hexdigest()
        if expected_hash != server_seed_hash:
            return False
        expected = StakeEngineGameMath.crash_game_result(server_seed, client_seed, nonce)
        return abs(expected - result) < 0.01

    @staticmethod
    def simulate_crash_rtp(
        rounds: int = 100_000,
        cash_out_at: float = 2.0,
        client_seed: str = "test_client_seed",
    ) -> RTPResult:
        server_seed, _ = StakeEngineGameMath.generate_server_seed()
        results = [
            StakeEngineGameMath.crash_game_result(server_seed, client_seed, n)
            for n in range(rounds)
        ]
        total_bet = float(rounds)
        # Cash out at `cash_out_at`x: win on crash >= cash_out_at, lose otherwise.
        total_return = sum(cash_out_at if r >= cash_out_at else 0.0 for r in results)
        sorted_results = sorted(results)
        return RTPResult(
            game="crash",
            rounds=rounds,
            total_bet=total_bet,
            total_return=total_return,
            actual_rtp=total_return / total_bet if total_bet else 0.0,
            expected_rtp=1.0 - CRASH_HOUSE_EDGE,
            average_multiplier=sum(results) / len(results) if results else 0.0,
            median_multiplier=sorted_results[len(sorted_results) // 2] if sorted_results else 0.0,
        )


class StakeEngineRGSClient:
    """Reference template for the Stake Engine RGS HTTP contract.

    Returned dicts document the wire shape for `/authenticate`, `/play`, and
    `/endRound` — wire them up to httpx in concrete integrations.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.stake-engine.com") -> None:
        self.api_key: str = api_key
        self.base_url: str = base_url.rstrip("/")
        self.session_token: str | None = None

    def authenticate(self, player_id: str, game_id: str, currency: str = "USD") -> dict[str, Any]:
        return {
            "endpoint": f"{self.base_url}/authenticate",
            "method": "POST",
            "headers": {"X-API-Key": self.api_key, "Content-Type": "application/json"},
            "body": {"playerId": player_id, "gameId": game_id, "currency": currency},
            "response": {
                "sessionToken": "string",
                "balance": "integer (micro-units)",
                "currency": "string",
            },
        }

    def play(
        self,
        session_token: str,
        bet_amount: int,
        client_seed: str,
        additional_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "endpoint": f"{self.base_url}/play",
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {session_token}",
                "Content-Type": "application/json",
            },
            "body": {
                "betAmount": bet_amount,
                "clientSeed": client_seed,
                "additionalData": additional_data or {},
            },
            "response": {
                "transactionId": "string",
                "serverSeedHash": "string",
                "result": "object",
                "payout": "integer",
                "balance": "integer",
            },
        }

    def end_round(
        self, session_token: str, transaction_id: str, server_seed: str
    ) -> dict[str, Any]:
        return {
            "endpoint": f"{self.base_url}/endRound",
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {session_token}",
                "Content-Type": "application/json",
            },
            "body": {"transactionId": transaction_id, "serverSeed": server_seed},
            "response": {
                "verified": "boolean",
                "previousBalance": "integer",
                "newBalance": "integer",
            },
        }


_CRASH_TEMPLATE = '''
class CrashGame:
    """Stake Engine Crash Game Implementation (reference)."""

    HOUSE_EDGE = 0.01
    MAX_MULTIPLIER = 1000.0
    RTP = 0.99

    def calculate_result(self, server_seed: str, client_seed: str, nonce: int) -> float:
        digest = hmac.new(
            server_seed.encode(),
            f"{client_seed}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        rand = int(digest[:16], 16) / (2 ** 64)
        effective_rand = rand * (1 - self.HOUSE_EDGE)
        if effective_rand <= 0:
            return self.MAX_MULTIPLIER
        return round(max(1.0, min(self.MAX_MULTIPLIER, 0.99 / effective_rand)), 2)
'''

_DICE_TEMPLATE = '''
class DiceGame:
    """Stake Engine Dice Game Implementation (reference)."""

    HOUSE_EDGE = 0.01

    def calculate_result(self, server_seed: str, client_seed: str, nonce: int) -> float:
        digest = hmac.new(
            server_seed.encode(),
            f"{client_seed}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        rand = int(digest[:16], 16) / (2 ** 64)
        return round((rand * 10000) % 10000 / 100, 2)

    def calculate_payout(self, result: float, target: float, is_under: bool = True) -> float:
        won = result < target if is_under else result > target
        probability = (target / 100) if is_under else ((100 - target) / 100)
        return 0.0 if not won else round((1 - self.HOUSE_EDGE) / probability, 4)
'''

_SLOTS_TEMPLATE = '''
class SlotsGame:
    """Stake Engine Slots Game Implementation (reference)."""

    SYMBOLS = {
        "7":     {"weight": 1,  "value": 50},
        "BAR":   {"weight": 2,  "value": 20},
        "bell":  {"weight": 4,  "value": 10},
        "cherry":{"weight": 8,  "value": 5},
        "lemon": {"weight": 16, "value": 3},
        "orange":{"weight": 16, "value": 2},
        "plum":  {"weight": 16, "value": 1},
    }
    REELS = [list(SYMBOLS.keys()) for _ in range(3)]

    def spin(self, server_seed: str, client_seed: str, nonce: int) -> dict:
        results = []
        for i, reel in enumerate(self.REELS):
            digest = hmac.new(
                server_seed.encode(),
                f"{client_seed}:reel{i}:{nonce}".encode(),
                hashlib.sha256,
            ).hexdigest()
            rand = int(digest[:16], 16) / (2 ** 64)
            results.append(reel[int(rand * len(reel)) % len(reel)])
        win = len(set(results)) == 1
        return {
            "result": results,
            "win": win,
            "multiplier": self.SYMBOLS[results[0]]["value"] if win else 0,
        }
'''

_PLINKO_TEMPLATE = '''
class PlinkoGame:
    """Stake Engine Plinko Game Implementation (reference)."""

    MULTIPLIERS = {
        "low":    [0.5, 0.7, 0.9, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
        "medium": [0.3, 0.5, 0.8, 1.0, 1.5, 3.0, 5.0, 10.0, 25.0],
        "high":   [0.2, 0.3, 0.5, 0.8, 1.0, 3.0, 10.0, 30.0, 100.0],
    }

    def __init__(self, rows: int = 16, risk: str = "medium") -> None:
        self.rows = rows
        self.risk = risk
        self.multipliers = self.MULTIPLIERS.get(risk, self.MULTIPLIERS["medium"])

    def drop_ball(self, server_seed: str, client_seed: str, nonce: int) -> dict:
        path = []
        position = self.rows // 2
        for row in range(self.rows):
            digest = hmac.new(
                server_seed.encode(),
                f"{client_seed}:plinko:{row}:{nonce}".encode(),
                hashlib.sha256,
            ).hexdigest()
            rand = int(digest[:16], 16) / (2 ** 64)
            direction = -1 if rand < 0.5 else 1
            position = max(0, min(position + direction, row + 1))
            path.append(direction)
        bucket = min(position, len(self.multipliers) - 1)
        return {
            "path": path,
            "final_position": position,
            "multiplier": self.multipliers[bucket],
            "rows": self.rows,
            "risk": self.risk,
        }
'''


class GameTemplates:
    """Ready-to-paste reference game implementations."""

    TEMPLATES: ClassVar[dict[str, str]] = {
        "crash": _CRASH_TEMPLATE,
        "dice": _DICE_TEMPLATE,
        "slots": _SLOTS_TEMPLATE,
        "plinko": _PLINKO_TEMPLATE,
    }

    @classmethod
    def get(cls, name: str) -> str:
        if name == "all":
            return "\n\n".join(cls.TEMPLATES.values())
        try:
            return cls.TEMPLATES[name]
        except KeyError as exc:  # pragma: no cover - argparse handles the typo path
            raise ValueError(f"Unknown game template: {name}") from exc


__all__ = [
    "CRASH_HOUSE_EDGE",
    "CRASH_MAX_MULTIPLIER",
    "DICE_HOUSE_EDGE",
    "GameTemplates",
    "RTPResult",
    "StakeEngineGameMath",
    "StakeEngineRGSClient",
]
