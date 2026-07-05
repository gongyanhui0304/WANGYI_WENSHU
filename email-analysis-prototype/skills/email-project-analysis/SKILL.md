---
name: email-project-analysis
description: Analyze server-side mail projects through the emailProjectAnalysis MCP server with per-user mailbox permissions; use for mailbox, customer, project, progress, payment, approval, risk, attachment, thread, and evidence questions.
---

# Email Project Analysis Skill

Use this Skill when a user asks about mailbox projects, customers, people, progress, payment, approvals, risks, attachments, threads, or evidence.

## Connection Model

Prefer the configured `emailProjectAnalysis` MCP tools. The server may be connected as remote MCP at `/mcp` or through a local stdio bridge. The Skill does not care which transport is used, as long as the exposed tool name is `emailProjectAnalysis` and permissions are enforced by the server.

For per-user delivery, this Skill may include that user's MCP connection values:

```text
MCP_NAME=emailProjectAnalysis
MCP_REMOTE_URL=https://mail-analysis.company.example/mcp
MCP_LEGACY_BASE_URL=https://mail-analysis.company.example  # fallback only
MCP_TOKEN=<this-user-token>
```

These values identify the server endpoint and the current user's token. Do not include a default mailbox. The token's server-side permissions decide which mailboxes can be used.

## Mandatory Data Source Rule

Always use the configured MCP Server. Do not read local `emails/`, do not scan raw server paths, and do not fall back to local mail files.

## Permission Model

The MCP token controls the mailbox scope. If this is a personalized Skill, it may embed that user's token and endpoint values, but it still must not embed a default mailbox or hard-code mailbox access decisions.

## Query Order

1. Call `list_mailboxes()` to know which mailboxes the current token can access.
2. Select a mailbox only if the user named it, recent conversation context uniquely identifies it, or `list_mailboxes()` returns exactly one mailbox.
3. If multiple mailboxes are available and the prompt is ambiguous, ask the user which mailbox to analyze.
4. Resolve the user's requested person, customer, project, or topic inside the selected mailbox.
5. Call `get_index_status(mailbox_id)` before relying on a mailbox.
6. Use `query_summary()` and `search_threads()` for normal analysis.
7. Use `get_evidence()` only when the user asks for basis, original mail, or full thread.
8. Use `rebuild_index()` only for explicit rebuild requests or missing/stale/corrupted index states.

## Permissions

- MCP Server is the final permission boundary.
- The Skill must not infer access from a mailbox name in the user prompt.
- If MCP returns forbidden, state that the current user has no access.
- Never accept user-provided filesystem paths as evidence references.

## Evidence

Important conclusions should cite `evidence_id` or `thread_id` when available.

Use wording like:

```text
依据：服务器索引，线程 th_xxx，证据 ev_xxx。
```

If the index only contains attachment names and not document body text, say so clearly.

## Pronouns and Context

Resolve pronouns from the recent conversation:

- "这个邮箱" -> most recently identified mailbox
- "这个项目" -> most recently identified project/topic
- "他/她" -> most recently identified person
- "这封邮件" -> most recently shown evidence

If ambiguous, list possible targets instead of guessing.

## Response Style

Lead with conclusions. Do not paste large mail bodies unless the user asks to open evidence.

For status questions, use:

```text
## 概况
- 邮箱：<mailbox_id>
- 主题/项目：<topic>
- 状态：<status based on index/evidence>
- 依据来源：服务器索引 / 原始证据

## 结论
...

## 关键依据
- <evidence_id> / <thread_id>
```


