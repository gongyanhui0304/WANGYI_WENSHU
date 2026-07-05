# Business Access Layer

This project has two entry points:

```text
Technical users:
  Agent Skill/instructions -> MCP Server -> server index/evidence

Business users:
  Web page / enterprise IM bot -> business gateway -> MCP Server -> server index/evidence
```

## Why Add This Layer

`config/server_connection.local.env` is for development and testing. It is not a business-user delivery mechanism.

Business users should not configure:

- MCP server URLs
- MCP tokens
- mailbox ids
- raw mail paths
- index paths
- project files

They should log in once through the enterprise identity system and ask questions in a business UI.

## Permission Model

The business layer maps a logged-in enterprise user to that user's MCP token:

```text
enterprise user id -> MCP token -> allowed mailboxes
```

The MCP Server remains the final permission boundary. Even if the business UI sends a mailbox id, MCP must validate that the token can access that mailbox.

Do not configure a default mailbox in the business layer. If a user has access to multiple mailboxes, the UI should ask them to choose or let the agent call `list_mailboxes` first.

## Recommended Production Deployment

```text
Browser / IM
  -> SSO or gateway login
  -> trusted user header or signed identity
  -> business web app
  -> MCP HTTP API
  -> permission check
  -> index/evidence
```

For a web deployment, use a reverse proxy such as Nginx or an enterprise gateway to inject a trusted header, for example:

```text
X-Authenticated-User: user_a
```

Only the proxy should be allowed to reach the business app directly.

## Files

```text
business-app/server/business_web_app.py
business-app/config/business_app.env.example
business-app/config/business_user_tokens.example.json
business-app/systemd/email-analysis-business-web.service.example
```

## Token Handling

Generate MCP tokens with:

```bash
python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id user_a \
  --display-name "User A" \
  --mailboxes mailbox_a \
  --allow-rebuild
```

Then store only the generated token in the protected business token map:

```json
{
  "user_id": "user_a",
  "display_name": "User A",
  "mcp_token": "generated_token"
}
```

Do not send this token to the browser.

## Skill Role

The Skill remains useful for developers, admins, and technical analysts. It is not the final permission boundary. Permissions always come from MCP tokens on the server.
