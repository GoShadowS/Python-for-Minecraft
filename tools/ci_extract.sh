#!/usr/bin/env bash
# Extracts the actionable part of a Gradle log and publishes it as a CI annotation.
#
# A raw `tail` of a failed Gradle run is almost entirely daemon stack frames; the actual
# cause sits in the "What went wrong" block and in the compiler diagnostics. Both are
# extracted here. The CI log file itself lives on a storage host that is not reachable
# from the development sandbox, so annotations are the only readable channel:
#   gh api repos/<owner>/<repo>/check-runs/<job-id>/annotations
set -uo pipefail

log="$1"
title="$2"
out="$(mktemp)"

{
  echo "### What went wrong"
  sed -n '/What went wrong/,/^\* Try/p' "$log" | head -60
  echo
  echo "### Exception chain (each Caused by: plus the frames below it)"
  # Frames are kept in full on purpose: whether the failing call runs in the Gradle daemon
  # or in a worker is exactly what the fabric-26.3 investigation needs.
  awk '/^Caused by:/ {show = 18} show > 0 {print; show--}' "$log" | head -120
  echo
  echo "### Compiler / script diagnostics"
  grep -nE "error:|e: |warning:|Could not (find|resolve)|Plugin \[id|not found|Unsupported|Caused by:|Execution failed for task|A problem occurred" "$log" \
    | grep -v "^\s*at " | head -60
  echo
  echo "### First lines"
  head -25 "$log"
} > "$out"

python3 "${GITHUB_WORKSPACE}/tools/ci_annotate.py" error "$title" "$out" 6000
rm -f "$out"
