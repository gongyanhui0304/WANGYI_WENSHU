# Remote MCP Configuration Notes

Use this mode first when the user's agent supports remote MCP or HTTP MCP servers.

Stable values:

```text
MCP name: emailProjectAnalysis
MCP URL: https://mail-analysis.company.example/mcp
Auth header: Authorization: Bearer <user-specific-token>
```

Client-specific UI labels may differ. Common labels include:

- Remote MCP Server
- HTTP MCP Server
- Streamable HTTP MCP
- MCP URL
- Bearer token
- Headers

If the agent only supports local command/stdio MCP, use `generic-mcp-stdio.json.example` or the Codex/Claude stdio examples instead.

