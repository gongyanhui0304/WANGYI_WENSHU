# Client Delivery

`client/generate_user_delivery.mjs` generates a personalized delivery bundle for one user.

The output is intentionally split by role:

```text
dist/user-delivery/<user-id>/
├── user/
│   ├── email_mcp_stdio.mjs
│   └── SKILL.md
└── it/
    ├── IT_INSTALL.md
    ├── mcp-config.codex.toml
    └── mcp-config.generic.json
```

`user/` contains the files tied to that user's token. `it/` contains setup instructions and MCP config snippets for deployment or platform administrators.

Generate it from the project root:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
```

Important: putting `email_mcp_stdio.mjs` and `SKILL.md` into a workspace does not automatically load the MCP server. An administrator must register `emailProjectAnalysis` in the agent platform's MCP/Tools/Connector settings. After that, the user can ask natural email questions without manually reminding the agent to read the bridge or Skill.

Do not give users raw mail, server paths, index files, permission files, admin tokens, or unpersonalized templates.

If an agent platform supports central remote MCP registration, administrators may register `emailProjectAnalysis` centrally instead of using the stdio bridge. The same permission model still applies: one user, one token, server-side mailbox validation.