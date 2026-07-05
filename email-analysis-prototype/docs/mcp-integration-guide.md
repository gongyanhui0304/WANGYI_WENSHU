# MCP Integration Guide: Central Server + Per-User Token

## Recommended Pattern

```text
MCP-capable agent
  -> remote MCP URL https://mail-analysis.company.example/mcp
  -> token authorization
  -> mailbox-scoped index/evidence
```

## User-Side Options

### Option A: Remote MCP Config, Preferred

Use this when the agent supports remote MCP/HTTP servers.

```text
name: emailProjectAnalysis
url: https://mail-analysis.company.example/mcp
Authorization: Bearer <personal-user-token>
```

No local bridge file is required.

### Option B: Local Stdio Bridge, Fallback

Use this only when the agent requires a local stdio MCP command:

```text
client/email_mcp_stdio.mjs
```

The bridge forwards MCP tool calls to the central server API with the user's token.

## Why This Does Not Affect Normal Agent Work

- The MCP server name is isolated: `emailProjectAnalysis`.
- No strict server `AGENTS.md` is placed in unrelated user workspaces.
- The bridge, when used, does not expose local filesystem tools.
- The central server enforces all mailbox permissions.

## Permission Flow

```text
User asks a question
  -> agent calls MCP tool
  -> server receives Authorization: Bearer <user-token>
  -> server loads permissions.json
  -> server checks mailbox_id is allowed
  -> server returns index/evidence or forbidden
```

## First Test

Ask:

```text
我能访问哪些邮箱？
```

Then ask:

```text
这个邮箱最近主要在处理什么？
```

If the first answer is empty or forbidden, fix server permissions before testing business questions.

