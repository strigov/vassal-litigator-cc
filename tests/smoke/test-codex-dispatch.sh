#!/usr/bin/env bash

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DISPATCH="$PLUGIN_ROOT/bin/codex-dispatch"

if [[ ! -x "$DISPATCH" ]]; then
  echo "ERROR: missing executable wrapper: $DISPATCH" >&2
  exit 1
fi

tmp_home="$(mktemp -d)"
trace_file="$(mktemp)"
help_file="$(mktemp)"
status_file="$(mktemp)"
status_err="$(mktemp)"
cleanup() {
  rm -rf "$tmp_home"
  rm -f "$trace_file" "$help_file" "$status_file" "$status_err"
}
trap cleanup EXIT

export HOME="$tmp_home"
unset CLAUDE_PLUGIN_DATA
unset CLAUDE_PLUGIN_DATA_OVERRIDE

if ! bash -x "$DISPATCH" --help >"$help_file" 2>"$trace_file"; then
  cat "$help_file"
  cat "$trace_file" >&2
  exit 1
fi

grep -q "Usage:" "$help_file"
grep -q "/vendor/codex-companion/scripts/codex-companion.mjs" "$trace_file"

set +e
"$DISPATCH" status --json >"$status_file" 2>"$status_err"
status_rc=$?
set -e

if [[ "$status_rc" -eq 0 ]]; then
  node -e 'JSON.parse(require("node:fs").readFileSync(process.argv[1], "utf8"))' "$status_file"
elif grep -qi "ECONNREFUSED" "$status_err"; then
  :
else
  cat "$status_file"
  cat "$status_err" >&2
  exit "$status_rc"
fi

echo "codex-dispatch smoke passed"
