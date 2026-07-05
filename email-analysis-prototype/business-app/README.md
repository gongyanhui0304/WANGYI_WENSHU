# Business Access Layer

This directory is a minimal server-side web gateway for business users.

Business users should not configure Codex, local env files, mailbox paths, or MCP
tokens. They open an internal page, log in through the enterprise gateway, and
ask questions. The gateway maps their authenticated user id to an MCP token on
the server, then calls the existing MCP HTTP API.

## Production Flow

```text
Browser
  -> enterprise SSO / reverse proxy
  -> business_web_app.py
  -> mail MCP HTTP API
  -> MCP permission check
  -> server-side index/evidence
```

The business app is not the final permission boundary. The MCP API still checks
the token and mailbox permissions on every call.

## Required Server Config

Copy the template and keep the real file outside version control:

```bash
cp business-app/config/business_app.env.example /etc/email-analysis/business_app.env
cp business-app/config/business_user_tokens.example.json /etc/email-analysis/business_user_tokens.json
chmod 600 /etc/email-analysis/business_user_tokens.json
```

Set at least:

```text
MAIL_MCP_BASE_URL=http://127.0.0.1:8765
BUSINESS_USER_TOKEN_FILE=/etc/email-analysis/business_user_tokens.json
BUSINESS_AUTH_MODE=trusted_header
BUSINESS_AUTH_HEADER=X-Authenticated-User
```

The token map should contain one MCP token per enterprise user. Generate those
tokens with `mcp-server/server/manage_permissions.py`; do not invent tokens in
the business app.

## Run

```bash
set -a
. /etc/email-analysis/business_app.env
set +a
python3 business-app/server/business_web_app.py
```

For local demo only:

```bash
export BUSINESS_AUTH_MODE=demo_cookie
python3 business-app/server/business_web_app.py
```

Then open:

```text
http://server:8780/login?user_id=user_a
```

## What Users See

They see a simple page:

```text
邮件问数助手
邮箱：<authorized mailbox list>
问题：最近主要在处理什么？
```

They do not see MCP tokens, server paths, raw mail files, or index files.
