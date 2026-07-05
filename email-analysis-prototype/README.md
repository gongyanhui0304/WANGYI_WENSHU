# Server-Hosted Mail Analysis via MCP

> 部署同事优先阅读：`docs/deployment-handoff-for-admin.md`。本项目已确定面向大邮件库，部署默认按 `docs/large-mail-production-indexing.md` 的增量、分片、可恢复索引方式执行；不要把全量扫描 cron 当成生产索引方式。

This project is deployed centrally on a server. Users ask questions from an MCP-capable agent such as Codex, Claude, Cursor, Cline, or Windsurf. Users do not touch raw mail, server indexes, scripts, server paths, or mailbox files.

## Architecture

```text
User agent
  -> emailProjectAnalysis MCP tool
  -> central server /mcp endpoint
  -> token permission check
  -> server-side large-mail production index
  -> controlled evidence by evidence_id/thread_id
```

Raw mail never leaves the server.

## Large Mail Production Mode

This project is now documented and delivered for a confirmed large mail store. Production indexing must use incremental file state tracking, mailbox/date shards, resumable jobs, atomic writes, retry/dead-letter handling, and operational monitoring.

The included `mcp-server/server/mail_indexer.py` now implements the single-host production indexer used for server validation: `--changed-list` incremental input, `indexed_files.sqlite`, mailbox/year_month shards, resumable `index_jobs`, dead-letter logging, and rollup/thread indexes for MCP reads. It still must not be scheduled as a repeated full-mailbox scan for the full mail store; daily production runs should feed changed files from server sync logs, filesystem events, or an upstream manifest. The production indexing contract is:

```text
新增/变化发现 -> indexed_files 状态表 -> parser worker -> mailbox/year_month 分片 -> rollup/thread index -> MCP 查询
```

See:

```text
docs/large-mail-production-indexing.md
```

## Final User Delivery

Generate a personalized bundle for each user:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
```

Output is split by role:

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

`user/` contains the user-specific bridge and Skill. `it/` contains installation instructions and MCP config snippets for deployment or platform administrators.

Files placed in a workspace are not auto-loaded as MCP tools. To make email questions work without manually reminding the agent, an administrator must register `emailProjectAnalysis` in the target agent platform first. If the platform supports remote MCP registration, administrators may register the `/mcp` endpoint and that user's token centrally instead of using the local stdio bridge.

The MCP URL should be a long-lived service entrance, not a temporary server IP:

```text
https://mail-analysis.company.example/mcp
```

If the real server changes later, keep this URL unchanged and move it with DNS, an internal VIP, gateway, or reverse proxy. Users should not need to replace their bridge or Skill files.

## Permission Rule

Do not customize mailbox permissions by editing Skill logic. The delivered user Skill may contain that user's token, but access scope is controlled only by the server-side token record in `MAIL_PERMISSIONS_FILE`.

```text
token_a -> allowed_mailboxes: [mailbox_a]
token_b -> allowed_mailboxes: [mailbox_b, mailbox_c]
```

The agent must call `list_mailboxes` and use only mailboxes returned for the current token.

## Server Setup

Copy this project to the server, then set environment variables:

```bash
export MAIL_RAW_ROOT=/path/to/raw-mails
export MAIL_INDEX_ROOT=/path/to/mail-index
export MAIL_LOG_ROOT=/path/to/mail-logs
export MAIL_PERMISSIONS_FILE=/path/to/mail-index/permissions.json
export SERVER_APP_ROOT=/opt/email-analysis/mcp_email_server
export MAIL_API_HOST=0.0.0.0
export MAIL_API_PORT=8765
```

Deploy runtime files and start the API. The top-level script copies runtime files, creates the protected permission file if needed, creates an admin token, starts the API, and can start a controlled initial validation index job for selected mailboxes:

```bash
./server-hosted-deploy.sh
```

Production indexing for the full mail store is not a repeated full-scan cron. Use `CHANGED_LIST=/path/to/changed-files.txt ./mcp-server/run_index_docx_mailboxes.sh <mailbox>` for daily incremental runs. Use `ALLOW_BACKFILL_SCAN=1` only for controlled initial backfill, repair, or small validation batches before opening broad production queries.

The service exposes:

```text
POST /mcp                  remote MCP JSON-RPC endpoint
POST /list_mailboxes       legacy HTTP endpoint used by optional stdio bridge
POST /query_summary        legacy HTTP endpoint used by optional stdio bridge
POST /search_threads       legacy HTTP endpoint used by optional stdio bridge
POST /get_evidence         legacy HTTP endpoint used by optional stdio bridge
POST /rebuild_index        legacy HTTP endpoint used by optional stdio bridge
```

## Add Users and Permissions

On the server runtime directory:

```bash
cd "$SERVER_APP_ROOT"

python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id user_a \
  --display-name "User A" \
  --mailboxes mailbox_a mailbox_b \
  --allow-rebuild
```

The script prints the generated token once. Put that token into the user's personalized delivery files.

List configured users without showing tokens:

```bash
python3 manage_permissions.py --file "$MAIL_PERMISSIONS_FILE" list
```

## User Questions

Users ask directly in their agent:

```text
我能访问哪些邮箱？
最近主要在处理什么？
付款审批现在怎么样？
哪些项目有风险？
打开支持这个结论的邮件依据。
```

If the token can access exactly one mailbox, the agent may use that mailbox after `list_mailboxes`. If multiple mailboxes are returned and the prompt does not specify one, the agent must ask the user to choose.

## Do Not Distribute

Do not give ordinary users raw mail, server indexes, server permission files, admin scripts, env files, unpersonalized bridge templates, or shared all-mailbox tokens. Give each user only the personalized files required by their agent platform.