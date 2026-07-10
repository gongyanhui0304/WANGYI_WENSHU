#!/usr/bin/env bash
set -euo pipefail

# Server-hosted deployment bootstrap.
# Run from the project root on the server. All real paths and tokens come from
# environment variables or a protected EnvironmentFile.

: "${MAIL_RAW_ROOT:?Set MAIL_RAW_ROOT to the raw mail root}"
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT to the index root}"
: "${MAIL_LOG_ROOT:?Set MAIL_LOG_ROOT to the log root}"
SERVER_APP_ROOT="${SERVER_APP_ROOT:-/opt/email-analysis/mcp_email_server}"
MAIL_PERMISSIONS_FILE="${MAIL_PERMISSIONS_FILE:-$MAIL_INDEX_ROOT/permissions.json}"

mkdir -p "$SERVER_APP_ROOT" "$MAIL_INDEX_ROOT" "$MAIL_LOG_ROOT"
cp mcp-server/server/mail_http_api.py "$SERVER_APP_ROOT/mail_http_api.py"
cp mcp-server/server/mail_indexer.py "$SERVER_APP_ROOT/mail_indexer.py"
cp mcp-server/server/manage_permissions.py "$SERVER_APP_ROOT/manage_permissions.py"
cp mcp-server/server/batch_mail_ops.py "$SERVER_APP_ROOT/batch_mail_ops.py"
chmod 755 "$SERVER_APP_ROOT/mail_http_api.py" "$SERVER_APP_ROOT/mail_indexer.py" "$SERVER_APP_ROOT/manage_permissions.py" "$SERVER_APP_ROOT/batch_mail_ops.py"

if [ ! -f "$MAIL_PERMISSIONS_FILE" ]; then
  cat > "$MAIL_PERMISSIONS_FILE" <<'JSON'
{
  "users": []
}
JSON
  chmod 600 "$MAIL_PERMISSIONS_FILE"
  echo "created empty permissions file: $MAIL_PERMISSIONS_FILE"
fi

cd "$SERVER_APP_ROOT"
export MAIL_RAW_ROOT MAIL_INDEX_ROOT MAIL_LOG_ROOT MAIL_PERMISSIONS_FILE
export MAIL_API_HOST="${MAIL_API_HOST:-0.0.0.0}"
export MAIL_API_PORT="${MAIL_API_PORT:-8765}"

nohup python3 mail_http_api.py > "$MAIL_LOG_ROOT/mail_http_api.out" 2>&1 &
echo "mail api started, pid=$!"
echo "runtime: $SERVER_APP_ROOT"
echo "log: $MAIL_LOG_ROOT/mail_http_api.out"
sleep 2
tail -n 20 "$MAIL_LOG_ROOT/mail_http_api.out" || true

echo "Remote MCP URL for users: http://<server-ip>:$MAIL_API_PORT/mcp"
