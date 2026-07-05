# User Delivery Guide

Final stdio-MCP user delivery is one personalized directory containing two files:

```text
email_mcp_stdio.mjs
SKILL.md
```

Generate it with:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
```

The user should not receive raw mail, indexes, permission files, server paths, env files, or admin scripts.

## Platform Setup

If the user's agent supports remote MCP registration, administrators may register `emailProjectAnalysis` centrally:

```text
MCP name: emailProjectAnalysis
MCP URL: https://mail-analysis.company.example/mcp
Authorization: Bearer <user-specific-token>
```

If the platform only supports stdio MCP, give the generated `email_mcp_stdio.mjs` and `SKILL.md` to the user.

## Permission Model

- The same server URL can be shared by all users.
- Each user has a different token.
- The token controls the allowed mailbox list on the server.
- There is no default mailbox.
- The agent must call `list_mailboxes` before analyzing mail.

## User Questions

```text
我能访问哪些邮箱？
最近主要在处理什么？
付款审批现在怎么样？
这个结论有什么邮件依据？
打开这条线程。
```

If exactly one mailbox is returned, the agent may use it. If multiple mailboxes are returned and the user did not specify one, the agent should ask the user to choose.