# MCP Tool Usage Rules

Required tools:

- `list_mailboxes()`
- `get_index_status(mailbox_id)`
- `query_summary(mailbox_id, query, filters)`
- `search_threads(mailbox_id, query, filters)`
- `get_evidence(mailbox_id, evidence_id or thread_id)`
- `rebuild_index(mailbox_id)`

Never use or request tools that expose arbitrary raw paths, including:

- `read_file(path)`
- `list_dir(path)`
- `grep(path)`

All mailbox access must be validated by MCP with the current user token.
