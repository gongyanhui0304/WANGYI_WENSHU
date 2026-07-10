# AGENTS.md

This repository is for the server-hosted mail analysis service and the per-user MCP delivery bundle.

## Scope

- Administrators deploy the full project on the server.
- The server owns raw mail access, indexing, permissions, tokens, and the remote MCP API.
- Every user or permission group can receive a dedicated delivery bundle with `user/email_mcp_stdio.mjs` and `user/SKILL.md`.
- The per-user bridge embeds only that user's token and server MCP URL. Do not share one user's bridge with another user.
- Users should not manually edit MCP config files. Platform admins or IT distribution should register or place the generated files for them.
- Preferred runtime access is the server remote MCP endpoint: `POST /mcp`.
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

## Delivery Generation

Generate a server-managed delivery bundle with:

```text
node client/generate_user_delivery.mjs --user-id <user_id> --mcp-url <mcp_url> --token <token> --mailbox <mailbox_id>
```

Default output:

```text
dist/platform-delivery/<user_id>/platform-admin/PLATFORM_ADMIN_SETUP.md
dist/platform-delivery/<user_id>/platform-admin/remote-mcp.per-user.json
dist/platform-delivery/<user_id>/user/email_mcp_stdio.mjs
dist/platform-delivery/<user_id>/user/SKILL.md
dist/platform-delivery/<user_id>/user-test/USER_TEST_PROMPT.md
```

Use `platform-admin/` when the agent platform supports remote HTTP MCP registration. Use `user/` when the platform only supports local stdio MCP and IT can distribute/register the per-user bridge for the user.

Business users may receive `user/email_mcp_stdio.mjs` and `user/SKILL.md`, but they should not be asked to author configuration, choose tokens, or know server paths. IT/platform tooling should install or register those files.

The agent must call `list_mailboxes` and use only mailboxes returned for the current token. If the user still has to remind the agent to read a local file, MCP has not been loaded in that platform session.

## Permission Rules

- A user can only access mailboxes listed for their token by the MCP Server.
- The Skill may contain a per-user token reference through the generated bridge, but it must not contain hard-coded mailbox permissions beyond hints/examples.
- The Skill may suggest a mailbox id based on the prompt or current conversation, but MCP must validate it.
- If multiple mailboxes are authorized and the user does not specify one, ask the user to choose.
- Never implement arbitrary `read_file(path)`, `list_dir(path)`, `grep(path)`, shell, SSH, or broad filesystem tools for mail access.
- Evidence must be fetched by `evidence_id` or `thread_id` through MCP.

## Normal Agent Use

Do not place this strict server `AGENTS.md` in unrelated user workspaces. For end-user delivery, use `dist/platform-delivery/<user_id>/user/`; for platform setup, use `dist/platform-delivery/<user_id>/platform-admin/`.
