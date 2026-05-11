#!/usr/bin/env bash
# Hacker Agent — GitHub remote setup.
# Idempotent: creates the repo if missing, attaches the remote, pushes main.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="${1:-hacker-agent}"
GITHUB_USER="${2:-${GITHUB_USER:-}}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

cd "${PROJECT_DIR}"

if ! command -v gh >/dev/null 2>&1; then
    printf '%bgh CLI not installed.%b Install from https://cli.github.com/\n' "${RED}" "${NC}"
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    printf '%bNot authenticated. Run: gh auth login%b\n' "${YELLOW}" "${NC}"
    exit 1
fi

if [[ -z "${GITHUB_USER}" ]]; then
    GITHUB_USER="$(gh api user --jq .login)"
fi

printf '%bUser:%b %s\n' "${GREEN}" "${NC}" "${GITHUB_USER}"
printf '%bRepo:%b %s\n' "${GREEN}" "${NC}" "${REPO_NAME}"

if [[ ! -d .git ]]; then
    git init
    git add .python-version pyproject.toml requirements.in README.md .gitignore .env.example
    git commit -m "init: scaffold hacker-agent" >/dev/null
fi

if ! gh repo view "${GITHUB_USER}/${REPO_NAME}" >/dev/null 2>&1; then
    printf '%bCreating private repo %s/%s ...%b\n' "${YELLOW}" "${GITHUB_USER}" "${REPO_NAME}" "${NC}"
    gh repo create "${GITHUB_USER}/${REPO_NAME}" --private --source=. --push
    printf '%bRepo created and pushed.%b\n' "${GREEN}" "${NC}"
else
    printf '%bRepo exists — attaching remote (if missing).%b\n' "${YELLOW}" "${NC}"
    if ! git remote get-url origin >/dev/null 2>&1; then
        git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    fi
    git push -u origin "$(git rev-parse --abbrev-ref HEAD)" || true
fi

printf '\n%bDone:%b https://github.com/%s/%s\n' "${GREEN}" "${NC}" "${GITHUB_USER}" "${REPO_NAME}"
