#!/usr/bin/env bash
# Hacker Agent — initialize the SQLite memory store.
# Safe to re-run: the schema is idempotent.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

echo "[+] Resolving memory DB path…"
python3 -m hacker_agent memory path

echo "[+] Touching schema…"
python3 -c "from hacker_agent.memory import HackerMemorySystem; HackerMemorySystem()"

echo "[+] Memory ready."
python3 -m hacker_agent stats
