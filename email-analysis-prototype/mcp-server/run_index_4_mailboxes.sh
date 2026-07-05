#!/usr/bin/env bash
set -euo pipefail

# Deprecated compatibility wrapper. Use run_index_docx_mailboxes.sh instead.
# Examples:
#   MAIL_RAW_ROOT=/path/to/raw-mails \
#   MAIL_INDEX_ROOT=/path/to/mail-index \
#   MAIL_LOG_ROOT=/path/to/mail-logs \
#   SERVER_APP_ROOT=/opt/email-analysis/mcp_email_server \
#   CHANGED_LIST=/path/to/changed-files.txt ./run_index_docx_mailboxes.sh mailbox_a mailbox_b

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$script_dir/run_index_docx_mailboxes.sh" "$@"

