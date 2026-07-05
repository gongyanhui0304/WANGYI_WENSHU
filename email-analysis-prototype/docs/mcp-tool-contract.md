# MCP Tool Contract

The MCP Server is the final permission boundary for mail analysis. Tools must be mailbox-scoped and token-checked.

## Common Requirements

- Authenticate every request with the current Codex user's token.
- Authorize every `mailbox_id` against that token.
- Do not expose arbitrary filesystem tools.
- Return original evidence only by `evidence_id` or `thread_id`.
- Write audit logs for mailbox list, index queries, evidence reads, and rebuild requests.

## list_mailboxes

Request:

```json
{}
```

Response:

```json
{
  "mailboxes": [
    {
      "mailbox_id": "mailbox_a",
      "display_name": "Mailbox A",
      "permissions": ["read_index", "read_evidence"]
    }
  ]
}
```

## get_index_status

Request:

```json
{"mailbox_id": "mailbox_a"}
```

Response:

```json
{
  "mailbox_id": "mailbox_a",
  "status": "ready",
  "index_updated_at": "2026-07-01 10:30:00",
  "mail_sync_updated_at": "2026-07-01 09:55:00",
  "is_stale": false
}
```

Possible statuses: `ready`, `missing`, `building`, `corrupted`, `stale`, `forbidden`, `raw_missing`.

## query_summary

Request:

```json
{
  "mailbox_id": "mailbox_a",
  "query": "付款审批现在怎么样",
  "filters": {}
}
```

Response:

```json
{
  "answer_basis": "server_index",
  "summary": "Summary based on authorized server index.",
  "items": [
    {
      "title": "Payment approval",
      "status": "in_progress",
      "owner": "person_a",
      "evidence_ids": ["ev_xxx"]
    }
  ]
}
```

## search_threads

Request:

```json
{
  "mailbox_id": "mailbox_a",
  "query": "customer project risk",
  "filters": {"date_from": null, "date_to": null}
}
```

Response:

```json
{
  "answer_basis": "server_index",
  "threads": [
    {
      "thread_id": "th_xxx",
      "subject": "Example subject",
      "participants": ["person_a", "person_b"],
      "started_at": "2026-01-01 09:00:00",
      "last_updated_at": "2026-01-02 18:00:00",
      "summary": "Thread summary.",
      "evidence_ids": ["ev_xxx"]
    }
  ]
}
```

## get_evidence

Request by evidence:

```json
{"mailbox_id": "mailbox_a", "evidence_id": "ev_xxx"}
```

Request by thread:

```json
{"mailbox_id": "mailbox_a", "thread_id": "th_xxx"}
```

Response:

```json
{
  "answer_basis": "original_evidence",
  "mailbox_id": "mailbox_a",
  "evidence": [
    {
      "evidence_id": "ev_xxx",
      "thread_id": "th_xxx",
      "subject": "Example subject",
      "sender": "person_a@example.com",
      "recipients": ["person_b@example.com"],
      "sent_at": "2026-01-01 09:00:00",
      "excerpt": "Controlled excerpt.",
      "attachments": ["attachment.pdf"]
    }
  ]
}
```

## rebuild_index

Request:

```json
{
  "mailbox_id": "mailbox_a",
  "reason": "user_explicit_rebuild_request"
}
```

Allowed reasons:

- `index_missing`
- `index_corrupted`
- `user_explicit_rebuild_request`
- `admin_explicit_rebuild_request`
- `stale_index_confirmed_by_status_check`
