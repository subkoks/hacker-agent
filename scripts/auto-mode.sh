#!/usr/bin/env bash
# Hacker Agent — Auto-Mode controller.
# Cycles: health-check -> backup -> auto-commit (feature branch only) -> upstream-check.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${HACKER_LOG_DIR:-${PROJECT_DIR}/logs}"
BACKUP_DIR="${HACKER_BACKUP_DIR:-${PROJECT_DIR}/backups}"
PID_FILE="${PROJECT_DIR}/.auto-mode.pid"
SLEEP_SECONDS="${HACKER_AUTO_INTERVAL:-3600}"

mkdir -p "${LOG_DIR}" "${BACKUP_DIR}"
LOG_FILE="${LOG_DIR}/auto-mode.log"

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}"
}

usage() {
    cat <<'EOF'
Hacker Agent Auto-Mode Controller

Usage:  scripts/auto-mode.sh <command>

Commands:
  start      Start the auto-mode daemon (interval HACKER_AUTO_INTERVAL seconds, default 3600).
  stop       Stop the running daemon.
  status     Print daemon status and last log lines.
  once       Run a single auto-mode cycle synchronously.
  health     Run a one-shot health check.
  backup     Snapshot src/scripts + export brain dump to backups/.
EOF
}

run_health_check() {
    cd "${PROJECT_DIR}"
    local errors=0

    log "Health check: python compile of src/hacker_agent/"
    while IFS= read -r -d '' file; do
        if ! python3 -m py_compile "${file}" 2>/dev/null; then
            log "Syntax error: ${file}"
            errors=$((errors + 1))
        fi
    done < <(find src/hacker_agent -name '*.py' -print0)

    log "Health check: CLI smoke (--version)"
    if ! python3 -m hacker_agent --version >/dev/null 2>&1; then
        log "CLI smoke test failed"
        errors=$((errors + 1))
    fi

    if [[ "${errors}" -eq 0 ]]; then
        log "Health check passed"
        return 0
    fi
    log "Health check failed (${errors} issues)"
    return 1
}

create_backup() {
    cd "${PROJECT_DIR}"
    local stamp
    stamp="backup-$(date -u +%Y%m%d-%H%M%SZ)"
    local staging="${BACKUP_DIR}/${stamp}"
    mkdir -p "${staging}"

    cp -R src "${staging}/" 2>/dev/null || true
    cp -R scripts "${staging}/" 2>/dev/null || true
    cp pyproject.toml "${staging}/" 2>/dev/null || true

    python3 -m hacker_agent memory export \
        "${staging}/brain-export.json" 2>/dev/null \
        || log "Brain export skipped"

    (cd "${BACKUP_DIR}" && tar -czf "${stamp}.tar.gz" "${stamp}" && rm -rf "${stamp}")
    log "Backup: ${BACKUP_DIR}/${stamp}.tar.gz"

    # Keep last 10 backups
    if compgen -G "${BACKUP_DIR}/backup-*.tar.gz" >/dev/null; then
        ls -t "${BACKUP_DIR}"/backup-*.tar.gz | tail -n +11 | xargs -r rm --
    fi
}

run_auto_commit() {
    cd "${PROJECT_DIR}"
    if [[ ! -d .git ]]; then
        log "Not a git repository, skipping auto-commit"
        return 0
    fi
    if [[ -z "$(git status --porcelain)" ]]; then
        log "No changes to commit"
        return 0
    fi
    "${SCRIPT_DIR}/auto-commit.sh" || log "auto-commit.sh failed"
}

run_upstream_check() {
    cd "${PROJECT_DIR}"
    if ! git remote get-url origin >/dev/null 2>&1; then
        return 0
    fi
    git fetch origin >/dev/null 2>&1 || log "git fetch failed"
    local local_sha remote_sha
    local_sha="$(git rev-parse HEAD)"
    remote_sha="$(git rev-parse origin/main 2>/dev/null || echo '')"
    if [[ -n "${remote_sha}" && "${local_sha}" != "${remote_sha}" ]]; then
        log "Upstream main has new commits — review with: git log HEAD..origin/main"
    fi
}

run_cycle() {
    log "=== auto-mode cycle start ==="
    run_health_check || true
    create_backup
    run_auto_commit
    run_upstream_check
    log "=== auto-mode cycle end ==="
}

start_daemon() {
    if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        log "Already running (PID $(cat "${PID_FILE}"))"
        return 0
    fi
    (
        while true; do
            run_cycle
            sleep "${SLEEP_SECONDS}"
        done
    ) >>"${LOG_FILE}" 2>&1 &
    echo "$!" >"${PID_FILE}"
    log "Started daemon (PID $!)"
}

stop_daemon() {
    if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        kill "$(cat "${PID_FILE}")"
        rm -f "${PID_FILE}"
        log "Stopped daemon"
    else
        rm -f "${PID_FILE}"
        log "Not running"
    fi
}

status_daemon() {
    if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        echo "Auto-mode: running (PID $(cat "${PID_FILE}"))"
    else
        echo "Auto-mode: not running"
        rm -f "${PID_FILE}" 2>/dev/null || true
    fi
    if [[ -f "${LOG_FILE}" ]]; then
        echo "--- last 10 log lines ---"
        tail -n 10 "${LOG_FILE}"
    fi
}

case "${1:-}" in
    start)   start_daemon ;;
    stop)    stop_daemon ;;
    status)  status_daemon ;;
    once)    run_cycle ;;
    health)  run_health_check ;;
    backup)  create_backup ;;
    *)       usage; exit 1 ;;
esac
