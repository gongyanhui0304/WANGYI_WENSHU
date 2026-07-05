# Admin Deployment Checklist: Server-Hosted Large-Mail Mode

## 1. Prepare Server Paths

Choose organization-approved paths:

```bash
export MAIL_RAW_ROOT=/path/to/raw-mails
export MAIL_INDEX_ROOT=/path/to/mail-index
export MAIL_LOG_ROOT=/path/to/mail-logs
export MAIL_PERMISSIONS_FILE=/path/to/mail-index/permissions.json
export SERVER_APP_ROOT=/opt/email-analysis/mcp_email_server
```

Permissions:

```text
MAIL_RAW_ROOT       service user read-only
MAIL_INDEX_ROOT     service user read-write
MAIL_LOG_ROOT       service user write/append
permissions.json    service user read, admin write
```

## 2. Deploy Runtime

From the server copy of this project:

```bash
./server-hosted-deploy.sh
```

This installs runtime files into `SERVER_APP_ROOT` and starts the MCP HTTP API. For process-manager deployments, use `mcp-server/systemd/email-analysis-api.service.example` and `mcp-server/config/server_hosted.env.example`.

## 3. Add Users

Generate a token and mailbox permission per user:

```bash
cd "$SERVER_APP_ROOT"
python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id user_a \
  --display-name "User A" \
  --mailboxes mailbox_a mailbox_b
```

Do not configure a default mailbox. The token's allowed mailbox list is the access scope.

## 4. Deploy Large-Mail Production Indexing

Production indexing must follow:

```text
docs/large-mail-production-indexing.md
```

The package includes these capabilities; verify them on a small real mailbox before broad production use:

```text
indexed_files state table
mailbox/year_month shards
resumable jobs with checkpoints
failed-file retry/dead-letter handling
rollup summary/thread indexes for MCP reads
```

Use `CHANGED_LIST=/path/to/changed-files.txt` for daily production indexing. Use `ALLOW_BACKFILL_SCAN=1` only for controlled initial backfill, repair, or low-frequency reconciliation.

## 5. Generate User Delivery Files

Generate a personalized bundle for each user:

```bash
cd /opt/email-analysis/email-analysis-prototype
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token '<this-user-token>'
```

Output:

```text
dist/user-delivery/user_a/
├── user/
│   ├── email_mcp_stdio.mjs
│   └── SKILL.md
└── it/
    ├── IT_INSTALL.md
    ├── mcp-config.codex.toml
    └── mcp-config.generic.json
```

## 6. Register MCP in the Agent Platform

This is an IT/platform-admin task. Do not rely on the business user reminding the agent to read local files.

For stdio MCP, register:

```text
MCP name: emailProjectAnalysis
command: node
args: <absolute path to>/user/email_mcp_stdio.mjs
```

For platforms with native remote MCP support, register the remote endpoint and that user's token centrally:

```text
MCP name: emailProjectAnalysis
MCP URL: https://mail-analysis.company.example/mcp
Authorization: Bearer <this-user-token>
```

## 7. Validate

Open a new session in the user's agent and ask:

```text
我能访问哪些邮箱？
```

Expected: only mailboxes authorized for that user's token.

Also verify the central MCP endpoint directly:

```bash
curl -sS -X POST https://mail-analysis.company.example/mcp \
  -H "Authorization: Bearer <this-user-token>" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_mailboxes","arguments":{}}}'
```

## 8. Do Not

- Do not give business users the full permission file.
- Do not give users raw mailbox paths.
- Do not give a shared all-mailbox token.
- Do not set a default mailbox in client config.
- Do not ask business users to edit env, admin docs, or MCP config files.
- Do not expose SSH/shell/raw filesystem MCP tools.
- Do not use repeated full-mailbox scans as the production indexing method.