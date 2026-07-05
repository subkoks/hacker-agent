#!/usr/bin/env bash
# install.sh — wire hacker-agent project subagents into local AI editors.
#
# Usage:
#   ./install.sh              install into every detected editor
#   ./install.sh --dry-run    print actions without changing anything
#   ./install.sh --uninstall  remove the symlinks this script created
#
# Idempotent. macOS bash 3.2-safe.

set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  case "$SOURCE" in /*) ;; *) SOURCE="$DIR/$SOURCE" ;; esac
done
REPO="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

DRY=0
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help)   grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

GREEN='\033[0;32m'; YEL='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
say()  { printf "${CYAN}%s${NC}\n" "$*"; }
ok()   { printf "  ${GREEN}link${NC} %s\n" "$*"; }
skip() { printf "  ${YEL}skip${NC} %s\n" "$*"; }

AGENTS="security-researcher ghidra-reverse-engineer"

link() {
  local target="$1" linkpath="$2"
  if [ "$UNINSTALL" -eq 1 ]; then
    if [ -L "$linkpath" ] && [ "$(readlink "$linkpath")" = "$target" ]; then
      [ "$DRY" -eq 1 ] && { echo "  rm   $linkpath"; return; }
      rm -f "$linkpath"; echo "  rm   $linkpath"
    fi
    return
  fi
  if [ -e "$linkpath" ] && [ ! -L "$linkpath" ]; then
    skip "$linkpath (real file/dir exists, not ours — leaving it)"
    return
  fi
  [ "$DRY" -eq 1 ] && { ok "$linkpath -> $target"; return; }
  mkdir -p "$(dirname "$linkpath")"
  ln -sfn "$target" "$linkpath"
  ok "$linkpath -> $target"
}

say "hacker-agent installer"
say "repo: $REPO"
[ "$DRY" -eq 1 ] && say "(dry-run — no changes)"
[ "$UNINSTALL" -eq 1 ] && say "(uninstall mode)"

for a in $AGENTS; do
  src="$REPO/.claude/agents/${a}.md"
  if [ ! -f "$src" ]; then
    skip "missing agent source: $src"
    continue
  fi
  if [ -d "$HOME/.claude" ]; then
    say "Claude (agent): $a"
    link "$src" "$HOME/.claude/agents/${a}.md"
  fi
  if [ -d "$HOME/.cursor" ]; then
    say "Cursor (agent): $a"
    link "$src" "$HOME/.cursor/agents/${a}/agent.md"
  fi
done

say "done."
if [ "$UNINSTALL" -eq 0 ] && [ "$DRY" -eq 0 ]; then
  echo ""
  echo "Verify in Cursor: Task -> security-researcher or ghidra-reverse-engineer"
  echo "Python env:       uv sync --extra dev && uv run pytest -q"
fi
