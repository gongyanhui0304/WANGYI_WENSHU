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
  ADMIN_MAILBOX_IDS="$(
    find "$MAIL_RAW_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
      | while IFS= read -r mailbox_name; do
          skip=0
          for excluded in $MAILBOX_EXCLUDE_NAMES; do
            if [ "$mailbox_name" = "$excluded" ]; then
              skip=1
              break
            fi
          done
          if [ "$skip" -eq 0 ]; then
            printf '%s\n' "$mailbox_name"
          fi
        done \
      | sort \
      | tr '\n' ' '
  )"
fi

if [ -z "$ADMIN_MAILBOX_IDS" ]; then
  echo "No mailbox directories found. Set ADMIN_MAILBOX_IDS explicitly." >&2
  exit 1
fi

mkdir -p "$SERVER_APP_ROOT" "$MAIL_INDEX_ROOT" "$MAIL_LOG_ROOT"
cp "$PROJECT_ROOT/mcp-server/server/mail_http_api.py" "$SERVER_APP_ROOT/mail_http_api.py"
cp "$PROJECT_ROOT/mcp-server/server/mail_indexer.py" "$SERVER_APP_ROOT/mail_indexer.py"
cp "$PROJECT_ROOT/mcp-server/server/manage_permissions.py" "$SERVER_APP_ROOT/manage_permissions.py"
chmod 755 "$SERVER_APP_ROOT/mail_http_api.py" "$SERVER_APP_ROOT/mail_indexer.py" "$SERVER_APP_ROOT/manage_permissions.py"

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

if command -v lsof >/dev/null 2>&1; then
  old_pids=$(lsof -ti tcp:"$MAIL_API_PORT" || true)
  if [ -n "$old_pids" ]; then
    echo "Stopping old process(es) on port $MAIL_API_PORT: $old_pids"
    kill $old_pids || true
    sleep 2
  fi
fi

export MAIL_RAW_ROOT MAIL_INDEX_ROOT MAIL_LOG_ROOT MAIL_PERMISSIONS_FILE MAIL_API_HOST MAIL_API_PORT
nohup python3 mail_http_api.py > "$MAIL_LOG_ROOT/mail_http_api.out" 2>&1 &
api_pid=$!
echo "mail api started, pid=$api_pid"
sleep 2

echo "--- api log ---"
tail -n 30 "$MAIL_LOG_ROOT/mail_http_api.out" || true

echo "--- index status before rebuild ---"
python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['MAIL_INDEX_ROOT'])
for p in sorted(root.iterdir() if root.exists() else []):
    f = p / 'index_status.json'
    if f.exists():
        try:
            print(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(p.name, e)
PY

echo "--- optional rebuild indexes ---"
export MAIL_INDEX_MAX_READ_BYTES="${MAIL_INDEX_MAX_READ_BYTES:-524288}"
export MAIL_INDEX_MAX_EVIDENCE="${MAIL_INDEX_MAX_EVIDENCE:-80000}"
export MAIL_INDEX_MAX_EXCERPT_CHARS="${MAIL_INDEX_MAX_EXCERPT_CHARS:-4000}"
nohup python3 mail_indexer.py $ADMIN_MAILBOX_IDS > "$MAIL_LOG_ROOT/mail_indexer_admin_mailboxes.out" 2>&1 &
index_pid=$!
echo "indexer started, pid=$index_pid"
sleep 2
tail -n 40 "$MAIL_LOG_ROOT/mail_indexer_admin_mailboxes.out" || true

echo "--- next checks ---"
echo "API log: tail -f $MAIL_LOG_ROOT/mail_http_api.out"
echo "Index log: tail -f $MAIL_LOG_ROOT/mail_indexer_admin_mailboxes.out"
echo "Admin token saved once at: $MAIL_LOG_ROOT/admin_token_last_created.json"
echo "Remote MCP URL for users: http://<server-ip>:$MAIL_API_PORT/mcp"

