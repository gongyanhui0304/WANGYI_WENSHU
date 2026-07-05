# Query Playbook

## Access Check

User asks:

```text
我能访问哪些邮箱？
```

Action:

1. Call `list_mailboxes()`.
2. Return only mailboxes the MCP Server authorizes.

## Mailbox Summary

User asks:

```text
这个邮箱最近主要在处理什么？
```

Action:

1. Resolve mailbox from the user prompt, conversation context, or `list_mailboxes`; if multiple mailboxes are possible, ask the user to choose.
2. Call `get_index_status(mailbox_id)`.
3. Call `query_summary(mailbox_id, query)`.
4. Call `search_threads(mailbox_id, query)` if more detail is needed.

## Evidence

User asks:

```text
打开支持这个结论的邮件依据。
```

Action:

1. Use the latest mentioned `evidence_id` or `thread_id`.
2. Call `get_evidence(mailbox_id, evidence_id/thread_id)`.
3. Show a concise excerpt and metadata.

## Rebuild

User asks:

```text
重新建立这个邮箱的邮件索引。
```

Action:

1. Confirm the mailbox from context.
2. Call `get_index_status(mailbox_id)`.
3. Call `rebuild_index(mailbox_id)` only if explicitly requested or status requires it.

