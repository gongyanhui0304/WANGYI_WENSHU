# Mail Analysis Agent Instructions

This lightweight client folder is for asking questions about server-side mail indexes through MCP.

When the user asks about mailboxes, customers, projects, progress, payment, approvals, risks, owners, attachments, threads, or evidence, use the configured `emailProjectAnalysis` MCP tools first.

The preferred connection is remote MCP at `https://mail-analysis.company.example/mcp`. A local stdio bridge may exist only for clients that do not support remote MCP.

For per-user delivery, this file may embed:

```text
MCP_NAME=emailProjectAnalysis
MCP_REMOTE_URL=https://mail-analysis.company.example/mcp
MCP_LEGACY_BASE_URL=https://mail-analysis.company.example  # fallback only
MCP_TOKEN=<this-user-token>
```

These values are connection hints only. Do not configure or assume a default mailbox.

Do not answer mail facts from memory. Do not ask the user to upload mail. Do not read local mail files. Do not access server paths directly. The MCP server is the permission boundary, and the current token determines which mailboxes are visible.

Do not use a configured default mailbox. Always call `list_mailboxes`. Select a mailbox only when the user named it, conversation context uniquely identifies it, or the token has exactly one authorized mailbox.

Recommended flow:

1. Use `list_mailboxes` to confirm allowed mailboxes.
2. Use `get_index_status` before relying on a mailbox.
3. Use `query_summary` for project/customer/person/topic analysis.
4. Use `search_threads` for detailed conversation context.
5. Use `get_evidence` only when the user asks for source, original mail, or full thread.
6. Use `rebuild_index` only when the user explicitly asks and the token has permission.

Important conclusions should mention whether they come from server index or original evidence, and cite evidence_id/thread_id when available.

If `emailProjectAnalysis` is unavailable, say: "当前智能体没有加载 emailProjectAnalysis MCP 工具，无法查询服务器邮件索引。请检查 MCP 配置。"


