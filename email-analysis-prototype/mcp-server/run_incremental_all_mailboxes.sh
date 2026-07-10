#!/usr/bin/env bash
set -euo pipefail

SERVER_APP_ROOT="${SERVER_APP_ROOT:-$HOME/email-analysis/mcp_email_server}"
: "${MAIL_RAW_ROOT:?Set MAIL_RAW_ROOT to the server raw mail root}"
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT to the server index root}"
: "${MAIL_LOG_ROOT:?Set MAIL_LOG_ROOT to the server log root}"

cd "$SERVER_APP_ROOT"
chmod 755 batch_mail_ops.py mail_indexer.py

log="$MAIL_LOG_ROOT/batch_incremental_index.out"
nohup python3 batch_mail_ops.py index --mode incremental "$@" > "$log" 2>&1 &

echo "batch incremental index started, pid=$!"
echo "log: $log"
sleep 2
tail -n 40 "$log" || true
