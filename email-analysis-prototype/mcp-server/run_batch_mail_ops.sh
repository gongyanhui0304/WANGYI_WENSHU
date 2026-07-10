#!/usr/bin/env bash
set -euo pipefail

SERVER_APP_ROOT="${SERVER_APP_ROOT:-$HOME/email-analysis/mcp_email_server}"
: "${MAIL_RAW_ROOT:?Set MAIL_RAW_ROOT to the server raw mail root}"
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT to the server index root}"
: "${MAIL_LOG_ROOT:?Set MAIL_LOG_ROOT to the server log root}"

cd "$SERVER_APP_ROOT"
chmod 755 batch_mail_ops.py mail_indexer.py

cmd="${1:-}"
if [ -z "$cmd" ]; then
  cat >&2 <<'MSG'
Usage:
  run_batch_mail_ops.sh discover [--departments caigou yingxiao]
  run_batch_mail_ops.sh index --mode incremental [--departments caigou]
  run_batch_mail_ops.sh index --mode backfill --departments caigou --max-groups 5000
  run_batch_mail_ops.sh grant-departments --create-department-users --admin-user-id mail_admin
MSG
  exit 2
fi
shift

exec python3 batch_mail_ops.py "$cmd" "$@"
