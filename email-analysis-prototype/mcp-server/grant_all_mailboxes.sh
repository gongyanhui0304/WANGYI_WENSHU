#!/usr/bin/env bash
set -euo pipefail

# Template helper for a single user token. Do not put real tokens in this file.
: "${MAIL_INDEX_ROOT:?Set MAIL_INDEX_ROOT}"
: "${MAIL_MCP_TOKEN:?Set MAIL_MCP_TOKEN}"
: "${MAILBOX_IDS:?Set MAILBOX_IDS, space separated}"

mkdir -p "$MAIL_INDEX_ROOT"
python3 - "$MAIL_INDEX_ROOT/permissions.json" "$MAIL_MCP_TOKEN" "$MAILBOX_IDS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
token = sys.argv[2]
mailboxes = sys.argv[3].split()
payload = {
    "users": [
        {
            "user_id": "codex_user",
            "display_name": "Codex User",
            "token": token,
            "allowed_mailboxes": mailboxes,
            "permissions": ["read_index", "read_evidence", "request_rebuild"],
        }
    ]
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {path}")
PY
chmod 600 "$MAIL_INDEX_ROOT/permissions.json"
