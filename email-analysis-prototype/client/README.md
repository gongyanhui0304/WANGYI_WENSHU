# Client Delivery

`client/generate_user_delivery.mjs` generates a trusted-connector user delivery bundle for one user.

The output is intentionally split by role:

```text
dist/platform-delivery/<user-id>/
└── user/
    ├── email_mcp_stdio.mjs
    └── SKILL.md
```

`user/` contains only the two files tied to that user's token. No administrator registration files are generated in the user delivery output.

Generate it from the project root:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url https://mail-analysis.company.example/mcp \
  --token <this-user-token>
```

Important: `emailProjectAnalysis` is expected to be registered by the deployment side as a trusted MCP connector before users start asking questions. User-side prompts must not ask for extra authorization, token entry, server URL, or manual MCP setup.

The permission model is always server-side: one user, one token, server-side mailbox validation. Do not give users raw mail, server paths, index files, permission files, admin tokens, or unpersonalized templates.
