#!/usr/bin/env bash
set -euo pipefail

# Optional business web app deployment.
# Run from the project root on the server.

: "${MAIL_MCP_BASE_URL:?Set MAIL_MCP_BASE_URL, usually http://127.0.0.1:8765}"
: "${BUSINESS_USER_TOKEN_FILE:?Set BUSINESS_USER_TOKEN_FILE to a protected user-token map}"

BUSINESS_APP_ROOT="${BUSINESS_APP_ROOT:-/opt/email-analysis/business_app}"
BUSINESS_APP_HOST="${BUSINESS_APP_HOST:-0.0.0.0}"
BUSINESS_APP_PORT="${BUSINESS_APP_PORT:-8780}"
BUSINESS_APP_LOG="${BUSINESS_APP_LOG:-/tmp/email_analysis_business_web.out}"

mkdir -p "$BUSINESS_APP_ROOT"
cp business-app/server/business_web_app.py "$BUSINESS_APP_ROOT/business_web_app.py"
chmod 755 "$BUSINESS_APP_ROOT/business_web_app.py"

export MAIL_MCP_BASE_URL BUSINESS_USER_TOKEN_FILE BUSINESS_APP_HOST BUSINESS_APP_PORT
export BUSINESS_AUTH_MODE="${BUSINESS_AUTH_MODE:-trusted_header}"
export BUSINESS_AUTH_HEADER="${BUSINESS_AUTH_HEADER:-X-Authenticated-User}"
export BUSINESS_SESSION_COOKIE_NAME="${BUSINESS_SESSION_COOKIE_NAME:-mail_user}"

nohup python3 "$BUSINESS_APP_ROOT/business_web_app.py" > "$BUSINESS_APP_LOG" 2>&1 &
echo "business web app started, pid=$!"
echo "url: http://<server-ip>:$BUSINESS_APP_PORT"
echo "log: $BUSINESS_APP_LOG"
