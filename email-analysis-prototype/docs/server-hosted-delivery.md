# Server-Hosted Delivery Model

This project is delivered through users' own MCP-capable agents. The central server hosts the mail index and permission checks; users do not receive raw mail, server paths, index files, permission files, or admin scripts.

```text
User agent
  -> emailProjectAnalysis MCP tool
  -> central MCP Server /mcp
  -> token-based mailbox authorization
  -> server-side large-mail index/evidence
```

## What Runs on the Server

The full project is deployed once by an administrator. Server data stays outside the project directory and is configured with environment variables:

```bash
MAIL_RAW_ROOT=/path/to/raw-mails
MAIL_INDEX_ROOT=/path/to/mail-index
MAIL_LOG_ROOT=/path/to/mail-logs
MAIL_PERMISSIONS_FILE=/path/to/mail-index/permissions.json
```

Production indexing follows `docs/large-mail-production-indexing.md`.

## Per-User Delivery Bundle

For each user, generate a personalized bundle:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
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

`user/` is the user-specific material. `it/` is for deployment or platform administrators to register `emailProjectAnalysis` in the target agent platform.

Copying files into a workspace is not enough. The platform must load the MCP server. If the user still has to remind the agent to read `email_mcp_stdio.mjs` or `SKILL.md`, the MCP tool has not been registered or the current session has not loaded it.

If the agent platform supports remote MCP registration, administrators may register `emailProjectAnalysis` centrally with the remote URL and that user's token instead of using the stdio bridge.

## Permission Boundary

Permissions are enforced on the MCP Server, not in the Skill logic.

```text
token_a -> allowed_mailboxes: [mailbox_a]
token_b -> allowed_mailboxes: [mailbox_b]
```

A user can ask for another mailbox, but MCP must return `forbidden` unless their token is authorized.

## Admin Workflow

1. Deploy the project on the server.
2. Configure `MAIL_RAW_ROOT`, `MAIL_INDEX_ROOT`, `MAIL_LOG_ROOT`, `MAIL_PERMISSIONS_FILE`.
3. Deploy large-mail production indexing.
4. Create one MCP token per user.
5. Generate a personalized delivery bundle per user.
6. Register `emailProjectAnalysis` in the target agent platform using `it/IT_INSTALL.md`.
7. Open a new user session and verify with `list_mailboxes` or the question `我能访问哪些邮箱？`.

## User Workflow

After IT has registered the MCP tool, the user asks directly:

```text
我能访问哪些邮箱？
这个邮箱最近主要在处理什么？
付款审批现在怎么样？
打开支持这个结论的邮件依据。
```

The agent should call MCP tools and answer only from authorized server index/evidence.