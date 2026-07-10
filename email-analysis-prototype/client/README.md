# Client Delivery

`client/generate_user_delivery.mjs` generates a personalized MCP delivery bundle for one user.

The output is intentionally split by role:

```text
dist/platform-delivery/<user-id>/
├── user/
│   ├── email_mcp_stdio.mjs
│   └── SKILL.md
└── platform-admin/
    ├── PLATFORM_ADMIN_SETUP.md
    ├── mcp-registration.stdio.json
    └── remote-mcp.per-user.json
```

`user/` contains only the two files tied to that user's token. `platform-admin/` contains platform-neutral MCP registration materials for deployment or platform administrators.

Generate it from the project root:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
```

Important: putting `email_mcp_stdio.mjs` and `SKILL.md` into a workspace does not automatically load the MCP server in any agent platform. An administrator must register `emailProjectAnalysis` in that platform's MCP / Tools / Connector settings.

Two connection modes are supported:

- Remote MCP / HTTP MCP: use `platform-admin/remote-mcp.per-user.json`.
- Standard stdio MCP: copy the user package files to a stable local path, then register `node <path>/email_mcp_stdio.mjs` using the equivalent of `platform-admin/mcp-registration.stdio.json`.

The permission model is always server-side: one user, one token, server-side mailbox validation. Do not give users raw mail, server paths, index files, permission files, admin tokens, or unpersonalized templates.
