# Production Batch Rollout

This is the production flow after the single-mailbox validation has passed.

## What Is Already Proven

The pilot mailbox is ready:

```text
mailbox_id: caigou/hqsc_gd3
status: ready
message_count: 19858
failed_group_count: 0
failed_file_count: 0
```

The API and MCP query path are proven. Remaining production work is batching and network reachability.

## Network Boundary

Indexing and permissions do not depend on the public network entrance. You can continue batching while the network team prepares a reachable MCP URL.

For real users, the delivery URL must be reachable from the user's agent runtime:

```text
https://mail-analysis.company.example/mcp
```

Do not ship production user bundles with a private URL such as:

```text
http://192.168.0.114:8765/mcp
```

unless every target user's agent can actually reach it.

## Server Environment

```bash
export PATH=$HOME/bin:$PATH
export MAIL_RAW_ROOT=/data
export MAIL_INDEX_ROOT=$HOME/email-analysis/index_v2
export MAIL_LOG_ROOT=$HOME/email-analysis/logs
export MAIL_PERMISSIONS_FILE=$HOME/email-analysis/index/permissions.json
export SERVER_APP_ROOT=$HOME/email-analysis/mcp_email_server
export MAIL_API_HOST=0.0.0.0
export MAIL_API_PORT=8765
```

## 1. Discover Mailboxes

Discover all department/account mailbox ids:

```bash
cd ~/email-analysis/mcp_email_server
python3 batch_mail_ops.py discover --departments caigou yingxiao
```

Expected ids look like:

```text
caigou/hqsc_gd3
yingxiao/<account>
```

## 2. Initial Backfill By Department

Do not start with every department at once. Backfill `caigou` first, then `yingxiao`.

```bash
cd ~/email-analysis/mcp_email_server
python3 batch_mail_ops.py index --mode backfill --departments caigou --max-groups 5000
```

If a mailbox reports `partial`, resume or run another batch for the remaining work. After `caigou` is healthy, run:

```bash
python3 batch_mail_ops.py index --mode backfill --departments yingxiao --max-groups 5000
```

## 3. Automatic Incremental Indexing

After initial backfill, run incremental indexing on a timer. It compares file signatures and only sends changed/deleted paths to `mail_indexer.py`.

Manual run:

```bash
cd ~/email-analysis/mcp_email_server
python3 batch_mail_ops.py index --mode incremental --departments caigou yingxiao
```

Background helper:

```bash
cd ~/email-analysis/email-analysis-prototype
./mcp-server/run_incremental_all_mailboxes.sh --departments caigou yingxiao
```

Cron example, every 10 minutes:

```cron
*/10 * * * * export PATH=$HOME/bin:$PATH; export MAIL_RAW_ROOT=/data; export MAIL_INDEX_ROOT=$HOME/email-analysis/index_v2; export MAIL_LOG_ROOT=$HOME/email-analysis/logs; export SERVER_APP_ROOT=$HOME/email-analysis/mcp_email_server; cd $HOME/email-analysis/mcp_email_server && python3 batch_mail_ops.py index --mode incremental --departments caigou yingxiao >> $HOME/email-analysis/logs/cron_incremental.out 2>&1
```

## 4. Generate Department Permissions

Create department-level users and an admin user:

```bash
cd ~/email-analysis/mcp_email_server
python3 batch_mail_ops.py grant-departments \
  --departments caigou yingxiao \
  --create-department-users \
  --admin-user-id mail_admin \
  --admin-display-name 邮件问数管理员 \
  --allow-rebuild
```

This updates:

```text
$MAIL_PERMISSIONS_FILE
```

Generated users follow this pattern:

```text
caigou_all -> caigou/*
yingxiao_all -> yingxiao/*
mail_admin -> caigou/* + yingxiao/*
```

Use per-person users later if the permission boundary must be narrower than department.

## 5. Generate User Delivery Bundles

On a machine with Node.js, generate all user bundles from the permission file:

```bash
node client/generate_bulk_delivery.mjs \
  --permissions /path/to/permissions.json \
  --mcp-url https://mail-analysis.company.example/mcp
```

Each user gets:

```text
dist/platform-delivery/<user_id>/user/email_mcp_stdio.mjs
dist/platform-delivery/<user_id>/user/SKILL.md
dist/platform-delivery/<user_id>/user-test/USER_TEST_PROMPT.md
```

Platform admins can use:

```text
dist/platform-delivery/<user_id>/platform-admin/mcp-registration.json
```

## 6. Acceptance Test

For each pilot role, ask:

```text
我能访问哪些邮箱？
```

Then:

```text
查一下 caigou/hqsc_gd3 里和承认书有关的邮件，并展开一封相关邮件的证据原文。
```

Pass criteria:

```text
MCP is reachable from the user agent.
The user only sees authorized mailboxes.
search_threads returns results.
get_evidence returns original evidence.
```
