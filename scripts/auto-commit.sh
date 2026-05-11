#!/usr/bin/env bash
# Hacker Agent — auto-commit.
# Always commits to a feature branch `${AUTO_COMMIT_BRANCH_PREFIX}<utc-stamp>`.
# Never pushes to main.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${HACKER_LOG_DIR:-${PROJECT_DIR}/logs}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/auto-commit.log"
PREFIX="${AUTO_COMMIT_BRANCH_PREFIX:-auto/}"

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}"
}

cd "${PROJECT_DIR}"

if [[ ! -d .git ]]; then
    log "Not a git repository — aborting"
    exit 1
fi

if [[ -z "$(git config user.name 2>/dev/null || true)" ]]; then
    git config user.name "Hacker Agent Bot"
    git config user.email "bot@hacker-agent.local"
    log "Configured local bot identity"
fi

if [[ -z "$(git status --porcelain)" ]]; then
    log "No changes to commit"
    exit 0
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
case "${CURRENT_BRANCH}" in
    main|master)
        STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
        FEATURE_BRANCH="${PREFIX}${STAMP}"
        log "On protected branch '${CURRENT_BRANCH}' — switching to '${FEATURE_BRANCH}'"
        git checkout -b "${FEATURE_BRANCH}"
        ;;
    *)
        FEATURE_BRANCH="${CURRENT_BRANCH}"
        log "Committing on existing feature branch '${FEATURE_BRANCH}'"
        ;;
esac

CHANGED_FILES="$(git status --porcelain | awk '{print $2}')"
COUNT="$(printf '%s\n' "${CHANGED_FILES}" | wc -l | tr -d ' ')"

# Stage tracked-and-modified plus added files explicitly — never `git add -A`.
while IFS= read -r f; do
    [[ -n "${f}" ]] || continue
    git add -- "${f}"
done <<<"${CHANGED_FILES}"

MSG="chore(auto): update ${COUNT} files $(date -u '+%Y-%m-%d %H:%M:%S UTC')

$(printf '%s\n' "${CHANGED_FILES}" | sed 's/^/- /')"

if git commit -m "${MSG}"; then
    log "Committed ${COUNT} files on ${FEATURE_BRANCH}"
else
    log "Commit failed"
    exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
    if git push -u origin "${FEATURE_BRANCH}"; then
        log "Pushed ${FEATURE_BRANCH} to origin"
    else
        log "Push failed (continuing — local commit retained)"
    fi
else
    log "No origin remote configured — local commit only"
fi

log "auto-commit complete"
