#!/usr/bin/env bash
set -euo pipefail

SERVER_APP_ROOT="${SERVER_APP_ROOT:-/opt/email-analysis/mcp_email_server}"
: "${MAIL_RAW_ROOT:?Set MAIL_RAW_ROOT to the server raw mail root}"
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT to the server index root}"
: "${MAIL_LOG_ROOT:?Set MAIL_LOG_ROOT to the server log root}"

cd "$SERVER_APP_ROOT"
chmod 755 mail_indexer.py

export MAIL_INDEX_MAX_READ_BYTES="${MAIL_INDEX_MAX_READ_BYTES:-524288}"
export MAIL_INDEX_MAX_EXCERPT_CHARS="${MAIL_INDEX_MAX_EXCERPT_CHARS:-4000}"

mkdir -p "$MAIL_INDEX_ROOT" "$MAIL_LOG_ROOT"

if [ "$#" -gt 0 ]; then
  mailboxes=("$@")
elif [ -n "${MAILBOX_IDS:-}" ]; then
  read -r -a mailboxes <<< "$MAILBOX_IDS"
else
  mapfile -t mailboxes < <(find "$MAIL_RAW_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
fi

if [ "${#mailboxes[@]}" -eq 0 ]; then
  echo "No mailbox ids provided or discovered." >&2
  exit 1
fi

indexer_args=()
if [ -n "${CHANGED_LIST:-}" ]; then
  indexer_args+=(--changed-list "$CHANGED_LIST" --job-type "${MAIL_INDEX_JOB_TYPE:-incremental}")
elif [ "${ALLOW_BACKFILL_SCAN:-}" = "1" ]; then
  indexer_args+=(--job-type "${MAIL_INDEX_JOB_TYPE:-backfill}")
else
  cat >&2 <<'MSG'
Refusing to start a mailbox-wide scan without an explicit mode.
For daily production indexing, pass CHANGED_LIST=/path/to/changed-files.txt.
For controlled initial backfill or repair only, set ALLOW_BACKFILL_SCAN=1.
MSG
  exit 2
fi

if [ -n "${RESUME_JOB_ID:-}" ]; then
  indexer_args=(--resume-job-id "$RESUME_JOB_ID" --job-type "${MAIL_INDEX_JOB_TYPE:-repair}")
fi

if [ -n "${MAX_GROUPS:-}" ]; then
  indexer_args+=(--max-groups "$MAX_GROUPS")
fi

log="$MAIL_LOG_ROOT/mail_indexer_production.out"
nohup python3 mail_indexer.py "${indexer_args[@]}" "${mailboxes[@]}" > "$log" 2>&1 &

echo "indexer started, pid=$!"
echo "mode args: ${indexer_args[*]}"
echo "mailboxes: ${mailboxes[*]}"
echo "log: $log"
sleep 2
tail -n 40 "$log" || true