# AGENTS.md

This repository is for the server-hosted mail analysis service and the per-user MCP delivery bundle.

## Scope

- Administrators deploy the full project on the server.
- End users receive only their personalized runtime files from `dist/user-delivery/<user_id>/user/`.
- IT/platform administrators use `dist/user-delivery/<user_id>/it/` to register `emailProjectAnalysis` in the target agent platform.
- Preferred runtime access is the server remote MCP endpoint: `POST /mcp`.
- Local `client/email_mcp_stdio.mjs` is the stdio bridge for agents that cannot connect to remote MCP directly.
- `business-app/` is only a temporary demo/debug gateway and is not the recommended delivery path.
- Production indexing is large-mail mode by default. Do not use repeated full-mailbox scans as the production indexing method.

## Data Source Rules

- Do not use a local `emails/` directory as a data source.
- Do not create local copies of raw mail.
- Do not scan raw server mail directly from Codex or from the Skill.
- Query mail only through the configured MCP Server.
- The MCP Server is the final permission boundary.
- Raw mail is read-only.
- Indexes and logs are stored only in server paths configured by environment variables.
- Production indexes must be incremental, sharded, and resumable as described in `docs/large-mail-production-indexing.md`.

## Required Server Environment

- `MAIL_RAW_ROOT`: raw mailbox root on the server.
- `MAIL_INDEX_ROOT`: server-side index root.
- `MAIL_LOG_ROOT`: server-side log root.
- `MAIL_PERMISSIONS_FILE`: token and mailbox permission file.

## User Delivery

Generate a personalized delivery bundle per user with:

```text
client/generate_user_delivery.mjs
```

Default stdio-MCP output:

```text
dist/user-delivery/<user_id>/user/email_mcp_stdio.mjs
dist/user-delivery/<user_id>/user/SKILL.md
dist/user-delivery/<user_id>/it/IT_INSTALL.md
dist/user-delivery/<user_id>/it/mcp-config.codex.toml
dist/user-delivery/<user_id>/it/mcp-config.generic.json
```

The bridge may contain that user's MCP URL and token. Do not configure a default mailbox. The agent must call `list_mailboxes` and use only mailboxes returned for the current token.

Copying files into a workspace is not enough. IT/platform administrators must register `emailProjectAnalysis` in the target agent platform. If the user still has to remind the agent to read `email_mcp_stdio.mjs` or `SKILL.md`, MCP has not been loaded in that agent session.

If the agent platform supports central remote MCP registration, administrators may register `emailProjectAnalysis` centrally and provide only platform-specific user instructions. Business users should not edit MCP config, env files, or repository files.

## Permission Rules

- A user can only access mailboxes listed for their token by the MCP Server.
- The Skill may contain a per-user token reference, but it must not contain hard-coded mailbox permissions.
- The Skill may suggest a mailbox id based on the prompt or current conversation, but MCP must validate it.
- If multiple mailboxes are authorized and the user does not specify one, ask the user to choose.
- Never implement arbitrary `read_file(path)`, `list_dir(path)`, `grep(path)`, shell, SSH, or broad filesystem tools for mail access.
- Evidence must be fetched by `evidence_id` or `thread_id` through MCP.

## Normal Agent Use

Do not place this strict server `AGENTS.md` in unrelated user workspaces. For end-user delivery, use `dist/user-delivery/<user_id>/user/`; for platform setup, use `dist/user-delivery/<user_id>/it/`.