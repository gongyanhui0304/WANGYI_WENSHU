# MCP Server Integration

This directory contains the reusable MCP integration pieces for server-side mail analysis.

```text
Remote-MCP-capable agent
  -> POST /mcp on server/mail_http_api.py
  -> $MAIL_INDEX_ROOT
  -> $MAIL_RAW_ROOT
```

For stdio-only clients:

```text
Agent
  -> bridge/email_mcp_stdio.mjs
  -> server/mail_http_api.py legacy HTTP endpoints
```

## Files

- `server/mail_http_api.py`: server-side remote MCP/HTTP API with token and mailbox authorization.
- `server/mail_indexer.py`: server-side document-aware mailbox indexer.
- `server/manage_permissions.py`: token and mailbox permission manager.
- `bridge/email_mcp_stdio.mjs`: optional fallback bridge for stdio-only clients.
- `config/*.example.*`: templates only; replace all values per deployment.

## Server Environment

Set these on the server:

```bash
export MAIL_RAW_ROOT=/path/to/raw-mails
export MAIL_INDEX_ROOT=/path/to/mail-index
export MAIL_LOG_ROOT=/path/to/mail-logs
export MAIL_PERMISSIONS_FILE=/path/to/mail-index/permissions.json
export SERVER_APP_ROOT=/opt/email-analysis/mcp_email_server
```

## Deploy API

From the project root on the server:

```bash
./mcp-server/deploy_server_bootstrap.sh
```

Create `MAIL_PERMISSIONS_FILE` from `config/permissions.example.json` before starting the API.

## Remote MCP Endpoint

```text
POST http://<server-host>:8765/mcp
Authorization: Bearer <user-specific-token>
```

This endpoint supports MCP JSON-RPC methods including `initialize`, `tools/list`, and `tools/call`.

## Build Index

Daily production indexing must feed a changed-list from the server sync log, filesystem event stream, or upstream manifest:

```bash
CHANGED_LIST=/data/mail-analysis/changed/2026-07-04.txt \
MAILBOX_IDS="mailbox_a mailbox_b" \
./mcp-server/run_index_docx_mailboxes.sh
```

The changed-list contains one relative path per line under each mailbox root. Missing paths are treated as deletes/tombstones when they already exist in `indexed_files.sqlite`.

Controlled initial backfill or repair must be explicit:

```bash
ALLOW_BACKFILL_SCAN=1 \
MAILBOX_IDS="mailbox_a" \
MAX_GROUPS=10000 \
./mcp-server/run_index_docx_mailboxes.sh
```

Resume a partial job:

```bash
RESUME_JOB_ID=<job_id> \
MAILBOX_IDS="mailbox_a" \
./mcp-server/run_index_docx_mailboxes.sh
```

If neither `CHANGED_LIST`, `RESUME_JOB_ID`, nor `ALLOW_BACKFILL_SCAN=1` is provided, the wrapper refuses to start to prevent accidental repeated full-mailbox scans.
## Security Notes

- Do not put real tokens in this repository.
- Do not expose raw path tools.
- Do not distribute `server_connection.local.env`.
- Use one token per user when possible.
- Keep raw mail, indexes, logs, and permission files on the server.
