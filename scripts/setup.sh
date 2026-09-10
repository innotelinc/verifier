#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# setup.sh — install the attribution guard hooks and prove they work.
#
#   1. Point this clone's git hooks at .githooks/ (core.hooksPath).
#   2. Self-test guard-lib: foreign trailers must be rejected, the owner's
#      trailers must pass.
#
# Idempotent — safe to re-run at any time.
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .git ]; then
  echo "setup: not a git repository (run inside a clone of verifier)" >&2
  exit 1
fi

git config core.hooksPath .githooks
echo "setup: guard hooks installed (core.hooksPath=.githooks)"

# shellcheck source=.githooks/guard-lib
# shellcheck disable=SC1091
source .githooks/guard-lib

# shellcheck source=.githooks/guard-lib
# shellcheck disable=SC1091
source .githooks/guard-lib

if ! guard_selftest --self-commit; then
  echo "setup: guard self-test FAILED" >&2
  exit 1
fi
echo "setup: guard self-test passed (fixtures + pre-commit hook fire)"
echo "setup: guard rejects foreign attribution trailers"
echo "setup: guard allows the owner's trailers — self-test passed"
