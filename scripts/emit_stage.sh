#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "usage: $0 <run_id> <stage> <from> <to> [status] [retry_count] [meta_json]"
  exit 1
fi

RUN_ID="$1"
STAGE="$2"
FROM="$3"
TO="$4"
STATUS="${5:-in_progress}"
RETRY="${6:-0}"
META="${7:-{}}"

python3 "$(dirname "$0")/run_state.py" \
  --run-id "$RUN_ID" \
  --stage "$STAGE" \
  --from "$FROM" \
  --to "$TO" \
  --status "$STATUS" \
  --retry-count "$RETRY" \
  --meta "$META"
