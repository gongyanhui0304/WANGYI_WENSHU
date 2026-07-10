# Agent Platform Integration Playbook

This project should be integrated by platform capability, not by a single agent brand.

## Goal

The backend remains heavy: raw mail, index data, permissions, token issuance, and MCP API all live on the server. Users do not handle raw mail paths or permissions. For platforms that require local stdio MCP, users can receive a per-user `email_mcp_stdio.mjs` and `SKILL.md`, but IT/platform tooling should distribute or register those files for them.

## Already Verified Server Contract

The server exposes a remote MCP endpoint:

```text
POST http://<mail-server-host>:8765/mcp
Authorization: Bearer <user-token>
Content-Type: application/json
```

MCP server name:

```text
emailProjectAnalysis
```

Core tools:

```text
list_mailboxes
get_index_status
query_summary
search_threads
get_evidence
rebuild_index
```

Permissions are enforced on the server by token. Do not give users raw mail paths, index paths, permissions.json, or admin tokens.

## Preferred Order

### Level 1: Remote MCP / HTTP MCP

Use this for any platform that supports remote MCP, HTTP MCP, Streamable HTTP MCP, connectors, or tool servers with custom headers.

Register:

```text
name: emailProjectAnalysis
transport: http
url: http://<mail-server-host>:8765/mcp
header: Authorization: Bearer <user-token>
```

Best production variant:

```text
name: emailProjectAnalysis
transport: http
url: https://mail-analysis.company.example/mcp
header: Authorization: Bearer <user-token>
```

Use a stable domain or gateway in production, not a temporary LAN IP, if users may change networks or servers may move.

### Level 2: Per-User Local stdio bridge

Use this when the agent platform has MCP but only accepts local command/stdio servers.

Generate one bundle per user or permission group:

```text
node client/generate_user_delivery.mjs --user-id <user_id> --mcp-url <url>/mcp --token <token>
```

Distribute or register:

```text
dist/platform-delivery/<user_id>/user/email_mcp_stdio.mjs
dist/platform-delivery/<user_id>/user/SKILL.md
```

Register the local bridge with the target agent runtime:

```text
name: emailProjectAnalysis
command: node
args: <absolute-path-to>/email_mcp_stdio.mjs
```

The generated bridge contains that user's MCP URL and token. Do not share it across users.

### Level 3: Custom HTTP tool/plugin fallback

Use this when the platform has no MCP support but supports custom tools, plugins, actions, API connectors, or workflow nodes.

Wrap these HTTP calls:

```text
POST /mcp tools/call list_mailboxes
POST /mcp tools/call search_threads
POST /mcp tools/call get_evidence
```

The wrapper must still send:

```text
Authorization: Bearer <user-token>
```

Do not implement arbitrary filesystem tools like read_file, list_dir, grep, shell, SSH, or raw path access.

## Platform Capability Checklist

For Codex, Cursor, Claude, Trae, WorkBuddy, Qoder/Qorder, or any other agent platform, ask the same questions:

1. Does it support remote HTTP MCP servers with headers? Use Level 1.
2. If not, does it support local stdio MCP command registration? Use Level 2 with the generated per-user bridge.
3. If not, does it support custom HTTP API tools/plugins/actions? Use Level 3.
4. If none of the above, the platform cannot directly use this service yet. It needs an adapter or a platform feature upgrade.

## Acceptance Test

After registration, open a new agent session and ask:

```text
我能访问哪些邮箱？
```

Expected behavior:

```text
The agent calls emailProjectAnalysis.list_mailboxes.
```

Then ask:

```text
查一下 caigou/hqsc_gd3 里和承认书有关的邮件
```

Expected behavior:

```text
The agent calls search_threads, then get_evidence when evidence is needed.
```

Failure signs:

```text
The agent only says it read SKILL.md.
The agent says emailProjectAnalysis/list_mailboxes is not available.
The agent asks the user to paste server paths or raw files.
The server returns unauthorized.
```

## Unauthorized Debugging

If the server returns unauthorized:

1. Confirm the token exists in the server permissions file used by the running API process.
2. Confirm the Authorization header is exactly:

```text
Authorization: Bearer <token>
```

3. Confirm the API process was started with:

```text
MAIL_PERMISSIONS_FILE=<the permissions.json containing this token>
```

4. Restart the API after permission-file changes if needed.

## Deployment Recommendation

For real rollout, create delivery bundles by department, role, or user:

```text
agent_test_caigou
caigou_buyer_001
yingxiao_sales_001
```

Platforms should register the standard stdio command from `platform-admin/mcp-registration.json`. Deploy `user/email_mcp_stdio.mjs` and make `user/SKILL.md` available to the agent; users do not edit MCP configuration.
