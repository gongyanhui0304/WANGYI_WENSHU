#!/usr/bin/env bash
set -euo pipefail

# Server-hosted deployment script for email-analysis-prototype.
# Run this from the project root on the server, or set PROJECT_ROOT explicitly.
# All environment-specific values must be provided by the administrator.

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
: "${MAIL_RAW_ROOT:?Set MAIL_RAW_ROOT to the raw mailbox root}"
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT to the index root}"
: "${MAIL_LOG_ROOT:?Set MAIL_LOG_ROOT to the log root}"

SERVER_APP_ROOT="${SERVER_APP_ROOT:-/opt/email-analysis/mcp_email_server}"
MAIL_PERMISSIONS_FILE="${MAIL_PERMISSIONS_FILE:-$MAIL_INDEX_ROOT/permissions.json}"
MAIL_API_HOST="${MAIL_API_HOST:-0.0.0.0}"
MAIL_API_PORT="${MAIL_API_PORT:-8765}"
ADMIN_USER_ID="${ADMIN_USER_ID:-admin}"
ADMIN_DISPLAY_NAME="${ADMIN_DISPLAY_NAME:-Admin User}"
MAILBOX_EXCLUDE_NAMES="${MAILBOX_EXCLUDE_NAMES:-}"

if [ ! -f "$PROJECT_ROOT/mcp-server/server/mail_http_api.py" ]; then
  echo "PROJECT_ROOT is not email-analysis-prototype: $PROJECT_ROOT" >&2
  echo "Upload the project zip, unzip it, then run from that directory." >&2
  exit 1
fi

if [ -z "${ADMIN_MAILBOX_IDS:-}" ]; then
  if [ ! -d "$MAIL_RAW_ROOT" ]; then
    echo "MAIL_RAW_ROOT does not exist: $MAIL_RAW_ROOT" >&2
    exit 1
  fi
  ADMIN_MAILBOX_IDS="$(python3 "$PROJECT_ROOT/mcp-server/server/batch_mail_ops.py" discover --departments caigou yingxiao 2>/dev/null | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin).get("mailboxes", [])))' || true)"
fi

if [ -z "$ADMIN_MAILBOX_IDS" ]; then
  echo "No mailbox directories found. Set ADMIN_MAILBOX_IDS explicitly." >&2
  exit 1
fi

mkdir -p "$SERVER_APP_ROOT" "$MAIL_INDEX_ROOT" "$MAIL_LOG_ROOT"
cp "$PROJECT_ROOT/mcp-server/server/mail_http_api.py" "$SERVER_APP_ROOT/mail_http_api.py"
cp "$PROJECT_ROOT/mcp-server/server/mail_indexer.py" "$SERVER_APP_ROOT/mail_indexer.py"
cp "$PROJECT_ROOT/mcp-server/server/manage_permissions.py" "$SERVER_APP_ROOT/manage_permissions.py"
cp "$PROJECT_ROOT/mcp-server/server/batch_mail_ops.py" "$SERVER_APP_ROOT/batch_mail_ops.py"
chmod 755 "$SERVER_APP_ROOT/mail_http_api.py" "$SERVER_APP_ROOT/mail_indexer.py" "$SERVER_APP_ROOT/manage_permissions.py" "$SERVER_APP_ROOT/batch_mail_ops.py"

if [ ! -f "$MAIL_PERMISSIONS_FILE" ]; then
  echo '{"users": []}' > "$MAIL_PERMISSIONS_FILE"
  chmod 600 "$MAIL_PERMISSIONS_FILE"
fi

cd "$SERVER_APP_ROOT"

python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id "$ADMIN_USER_ID" \
  --display-name "$ADMIN_DISPLAY_NAME" \
  --mailboxes $ADMIN_MAILBOX_IDS \
  --allow-rebuild \
  --rotate-token | tee "$MAIL_LOG_ROOT/admin_token_last_created.json"
chmod 600 "$MAIL_LOG_ROOT/admin_token_last_created.json"

old_pids=$(ps -ef | grep 'mail_http_api.py' | grep -v grep | awk '{print $2}' || true)
if [ -n "$old_pids" ]; then
  echo "Stopping old mail API process(es): $old_pids"
  kill $old_pids || true
  sleep 2
fi

export MAIL_RAW_ROOT MAIL_INDEX_ROOT MAIL_LOG_ROOT MAIL_PERMISSIONS_FILE MAIL_API_HOST MAIL_API_PORT
nohup python3 mail_http_api.py > "$MAIL_LOG_ROOT/mail_http_api.out" 2>&1 &
api_pid=$!
echo "mail api started, pid=$api_pid"
sleep 2

echo "--- api log ---"
tail -n 30 "$MAIL_LOG_ROOT/mail_http_api.out" || true

echo "--- optional indexing ---"
echo "Initial backfill: SERVER_APP_ROOT=$SERVER_APP_ROOT mcp-server/run_batch_mail_ops.sh index --mode backfill --departments caigou --max-groups 5000"
echo "Incremental:    SERVER_APP_ROOT=$SERVER_APP_ROOT mcp-server/run_incremental_all_mailboxes.sh --departments caigou yingxiao"
echo "Remote MCP URL for users: http://<server-ip>:$MAIL_API_PORT/mcp"

