#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: $0 <run_id> <wp_ready_file1> [wp_ready_file2 ...]"
  exit 1
fi

RUN_ID="$1"
shift
FILES=("$@")

REPORT="state/preflight_${RUN_ID}.json"
python3 "$(dirname "$0")/publish_preflight.py" --files "${FILES[@]}" --out "$REPORT"

# preflight.py exits non-zero when blocked
# if here, gate passed
echo "PREFLIGHT_OK run_id=$RUN_ID report=$REPORT"
