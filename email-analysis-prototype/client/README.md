# Client Delivery

`client/generate_user_delivery.mjs` generates a single-file user Skill bundle for one user.

The output is intentionally split by role:

```text
dist/platform-delivery/<user-id>/
└── user/
    └── SKILL.md
```

`user/` contains only `SKILL.md`. The Skill embeds the per-user stdio bridge and token so the fallback path still works when platform MCP tools are absent.

Generate it from the project root:

```bash
node client/generate_user_delivery.mjs \
  --user-id user_a \
  --mcp-url <internal-mail-query-endpoint> \
  --token <this-user-token>
```

Important: `emailProjectAnalysis` is a pre-approved internal read-only mail search tool. User-side prompts should start querying directly and avoid connection setup language.

The permission model is always server-side: one user, one token, server-side mailbox validation. Do not give users raw mail, server paths, index files, permission files, admin tokens, or unpersonalized templates.
