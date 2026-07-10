#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal server-side mail data API for the Codex email analysis prototype.

This is intentionally small and dependency-free. It is not a general file API.
It exposes only mailbox-scoped operations and denies arbitrary path reads.
"""

import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value

RAW_ROOT = Path(required_env("MAIL_RAW_ROOT")).resolve()
INDEX_ROOT = Path(required_env("MAIL_INDEX_ROOT")).resolve()
LOG_ROOT = Path(required_env("MAIL_LOG_ROOT")).resolve()
PERMISSIONS_FILE = Path(os.environ.get("MAIL_PERMISSIONS_FILE", str(INDEX_ROOT / "permissions.json")))
HOST = os.environ.get("MAIL_API_HOST", "0.0.0.0")
PORT = int(os.environ.get("MAIL_API_PORT", "8765"))


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _empty_response(handler: BaseHTTPRequestHandler, status: int) -> None:
    handler.send_response(status)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def _load_permissions() -> Dict[str, Dict[str, Any]]:
    if not PERMISSIONS_FILE.exists():
        return {}
    data = json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
    users = data.get("users", [])
    return {str(user.get("token")): user for user in users if user.get("token")}


def _current_user(handler: BaseHTTPRequestHandler) -> Optional[Dict[str, Any]]:
    auth = handler.headers.get("Authorization", "")
    token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else auth.strip()
    if not token:
        return None
    return _load_permissions().get(token)


def _audit(user: Dict[str, Any], tool: str, payload: Dict[str, Any], status: str) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user.get("user_id"),
            "tool": tool,
            "mailbox_id": payload.get("mailbox_id"),
            "status": status,
            "query": payload.get("query"),
            "evidence_id": payload.get("evidence_id"),
            "thread_id": payload.get("thread_id"),
        },
        ensure_ascii=False,
    )
    with (LOG_ROOT / "access_audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _ensure_mailbox(user: Dict[str, Any], mailbox_id: str) -> Tuple[bool, str]:
    allowed = set(user.get("allowed_mailboxes", []))
    if mailbox_id not in allowed:
        return False, "forbidden"
    return True, "ok"


def _safe_mailbox_path(root: Path, mailbox_id: str) -> Path:
    path = (root / mailbox_id).resolve()
    if root not in path.parents and path != root:
        raise ValueError("mailbox path escapes root")
    return path


def _read_text_if_exists(paths: List[Path]) -> Optional[str]:
    for path in paths:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return None


def _index_dir(mailbox_id: str) -> Path:
    return _safe_mailbox_path(INDEX_ROOT, mailbox_id)


def _raw_dir(mailbox_id: str) -> Path:
    return _safe_mailbox_path(RAW_ROOT, mailbox_id)




def _rollup_summary_path(mailbox_id: str) -> Path:
    return _index_dir(mailbox_id) / "rollups" / "summary.json"


def _thread_index_path(mailbox_id: str) -> Path:
    return _index_dir(mailbox_id) / "rollups" / "thread_index.sqlite"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _thread_rows_from_rollup(mailbox_id: str, query: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    db = _thread_index_path(mailbox_id)
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        lowered = query.lower().strip()
        if lowered:
            rows = conn.execute(
                "select * from threads where mailbox_id = ? and search_text like ? order by last_updated_at desc limit ?",
                (mailbox_id, f"%{lowered}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "select * from threads where mailbox_id = ? order by last_updated_at desc limit ?",
                (mailbox_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "thread_id": row["thread_id"],
                    "subject": row["subject"] or "",
                    "status": "indexed",
                    "participants": json.loads(row["participants_json"] or "[]"),
                    "started_at": row["started_at"],
                    "last_updated_at": row["last_updated_at"],
                    "message_count": row["message_count"],
                    "evidence_ids": json.loads(row["evidence_ids_json"] or "[]"),
                    "summary": row["summary"] or "",
                }
            )
        return result
    finally:
        conn.close()


def _evidence_locators(mailbox_id: str, evidence_id: Any, thread_id: Any) -> Optional[List[Dict[str, str]]]:
    db = _thread_index_path(mailbox_id)
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        if evidence_id:
            rows = conn.execute(
                "select evidence_id, thread_id, shard_id from evidence_locator where mailbox_id = ? and evidence_id = ? limit 20",
                (mailbox_id, str(evidence_id)),
            ).fetchall()
        elif thread_id:
            rows = conn.execute(
                "select evidence_id, thread_id, shard_id from evidence_locator where mailbox_id = ? and thread_id = ? limit 20",
                (mailbox_id, str(thread_id)),
            ).fetchall()
        else:
            return []
        return [{"evidence_id": row["evidence_id"], "thread_id": row["thread_id"], "shard_id": row["shard_id"]} for row in rows]
    finally:
        conn.close()


def _read_sharded_evidence(mailbox_id: str, locators: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    if not locators:
        return []
    wanted = {item["evidence_id"] for item in locators}
    by_shard: Dict[str, set[str]] = {}
    for item in locators:
        by_shard.setdefault(item["shard_id"], set()).add(item["evidence_id"])
    evidence = []
    for shard_id, ids in by_shard.items():
        path = _index_dir(mailbox_id) / "shards" / Path(shard_id) / "evidence.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("evidence_id") in ids and record.get("evidence_id") in wanted:
                item = dict(record)
                item.pop("raw_path", None)
                evidence.append(item)
                if len(evidence) >= 20:
                    return evidence
    return evidence

def list_mailboxes(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailboxes = []
    for mailbox_id in user.get("allowed_mailboxes", []):
        mailboxes.append(
            {
                "mailbox_id": mailbox_id,
                "display_name": mailbox_id,
                "permissions": user.get("permissions", []),
            }
        )
    return {"mailboxes": mailboxes}


def get_index_status(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailbox_id = str(payload.get("mailbox_id", ""))
    ok, reason = _ensure_mailbox(user, mailbox_id)
    if not ok:
        return {"mailbox_id": mailbox_id, "status": reason, "is_stale": None}
    idx = _index_dir(mailbox_id)
    raw = _raw_dir(mailbox_id)
    if not raw.exists():
        return {"mailbox_id": mailbox_id, "status": "raw_missing", "is_stale": None}
    if not idx.exists():
        return {"mailbox_id": mailbox_id, "status": "missing", "is_stale": None}
    index_mtime = idx.stat().st_mtime
    raw_mtime = raw.stat().st_mtime
    status_file = idx / "index_status.json"
    status_payload: Dict[str, Any] = {}
    if status_file.exists():
        try:
            status_payload = json.loads(status_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"mailbox_id": mailbox_id, "status": "corrupted", "is_stale": None}
    return {
        "mailbox_id": mailbox_id,
        "status": status_payload.get("status", "ready"),
        "index_updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(index_mtime)),
        "mail_sync_updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(raw_mtime)),
        "is_stale": raw_mtime > index_mtime,
    }


def query_summary(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailbox_id = str(payload.get("mailbox_id", ""))
    query = str(payload.get("query", ""))
    ok, reason = _ensure_mailbox(user, mailbox_id)
    if not ok:
        return {"answer_basis": "permission", "summary": "current user is not allowed to access this mailbox", "status": reason}
    rollup_summary = _rollup_summary_path(mailbox_id)
    if rollup_summary.exists():
        data = _load_json(rollup_summary)
        return {"answer_basis": "server_index", "query": query, **data}
    idx = _index_dir(mailbox_id)
    summary = _read_text_if_exists([idx / "summary.md", idx / "summary.txt"])
    summary_json = idx / "summary.json"
    if summary_json.exists():
        data = _load_json(summary_json)
        return {"answer_basis": "server_index", "query": query, **data}
    if not summary:
        return {"answer_basis": "server_index", "summary": "mailbox summary index has not been generated", "status": "missing_summary_index"}
    return {"answer_basis": "server_index", "query": query, "summary": summary[:4000]}

def search_threads(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailbox_id = str(payload.get("mailbox_id", ""))
    query = str(payload.get("query", ""))
    ok, reason = _ensure_mailbox(user, mailbox_id)
    if not ok:
        return {"answer_basis": "permission", "threads": [], "status": reason}
    rollup_threads = _thread_rows_from_rollup(mailbox_id, query)
    if rollup_threads is not None:
        return {"answer_basis": "server_index", "threads": rollup_threads[:20]}
    idx = _index_dir(mailbox_id)
    threads_json = idx / "threads.json"
    if threads_json.exists():
        threads = json.loads(threads_json.read_text(encoding="utf-8"))
        lowered = query.lower()
        if lowered:
            threads = [t for t in threads if lowered in json.dumps(t, ensure_ascii=False).lower()]
        return {"answer_basis": "server_index", "threads": threads[:20]}
    threads_md = _read_text_if_exists([idx / "threads.md", idx / "threads.txt"])
    if not threads_md:
        return {"answer_basis": "server_index", "threads": [], "status": "missing_thread_index"}
    return {"answer_basis": "server_index", "threads": [{"thread_id": "threads_text", "summary": threads_md[:4000]}]}

def get_evidence(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailbox_id = str(payload.get("mailbox_id", ""))
    evidence_id = payload.get("evidence_id")
    thread_id = payload.get("thread_id")
    ok, reason = _ensure_mailbox(user, mailbox_id)
    if not ok:
        return {"answer_basis": "permission", "evidence": [], "status": reason}
    if "read_evidence" not in user.get("permissions", []):
        return {"answer_basis": "permission", "evidence": [], "status": "missing_read_evidence_permission"}
    locators = _evidence_locators(mailbox_id, evidence_id, thread_id)
    if locators is not None:
        return {"answer_basis": "server_index", "mailbox_id": mailbox_id, "evidence": _read_sharded_evidence(mailbox_id, locators)}
    idx = _index_dir(mailbox_id)
    evidence_map_path = idx / "evidence_map.json"
    if not evidence_map_path.exists():
        return {"answer_basis": "original_evidence", "evidence": [], "status": "missing_evidence_map"}
    evidence_map = json.loads(evidence_map_path.read_text(encoding="utf-8"))
    records = evidence_map.get("evidence", [])
    selected = []
    for record in records:
        if evidence_id and record.get("evidence_id") == evidence_id:
            selected.append(record)
        if thread_id and record.get("thread_id") == thread_id:
            selected.append(record)
    safe_records = []
    raw_root = _raw_dir(mailbox_id)
    for record in selected[:20]:
        item = dict(record)
        raw_path = item.pop("raw_path", None)
        if raw_path:
            path = Path(raw_path).resolve()
            if raw_root in path.parents and path.exists() and path.is_file():
                item["excerpt"] = path.read_text(encoding="utf-8", errors="replace")[:4000]
            else:
                item["excerpt"] = item.get("excerpt", "evidence path failed safety validation or does not exist")
        safe_records.append(item)
    return {"answer_basis": "original_evidence", "mailbox_id": mailbox_id, "evidence": safe_records}

def rebuild_index(user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    mailbox_id = str(payload.get("mailbox_id", ""))
    reason = str(payload.get("reason", ""))
    ok, deny_reason = _ensure_mailbox(user, mailbox_id)
    if not ok:
        return {"mailbox_id": mailbox_id, "status": deny_reason}
    if "request_rebuild" not in user.get("permissions", []):
        return {"mailbox_id": mailbox_id, "status": "missing_request_rebuild_permission"}
    allowed_reasons = {
        "index_missing",
        "index_corrupted",
        "user_explicit_rebuild_request",
        "admin_explicit_rebuild_request",
        "stale_index_confirmed_by_status_check",
    }
    if reason not in allowed_reasons:
        return {"mailbox_id": mailbox_id, "status": "invalid_rebuild_reason"}
    job_id = "job_" + time.strftime("%Y%m%d_%H%M%S")
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    (LOG_ROOT / "rebuild_jobs.jsonl").open("a", encoding="utf-8").write(
        json.dumps({"job_id": job_id, "mailbox_id": mailbox_id, "reason": reason, "status": "queued"}, ensure_ascii=False) + "\n"
    )
    return {
        "job_id": job_id,
        "mailbox_id": mailbox_id,
        "status": "queued",
        "message": "已记录重建请求。实际索引器需要由管理员接入。",
    }



MCP_TOOLS = [
    {
        "name": "list_mailboxes",
        "description": "Enterprise mail-index only. Return authorized mailbox_id values such as caigou/hqsc_gd3 or yingxiao/xxx. Use this instead of Gmail for company mailbox paths, project mail, approval, quotation, sample, customer, supplier, order, attachment, evidence, and thread questions.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_index_status",
        "description": "Enterprise mail-index only. Return server-side index status for an authorized mailbox_id such as caigou/hqsc_gd3. Do not use Gmail for these mailbox_id paths.",
        "inputSchema": {"type": "object", "properties": {"mailbox_id": {"type": "string"}}, "required": ["mailbox_id"]},
    },
    {
        "name": "query_summary",
        "description": "Enterprise mail-index only. Query project, customer, people, owner, risk, progress, payment, approval, quotation, sample, order, attachment, and evidence summaries from the server index. Use for caigou/... and yingxiao/... mailbox_id queries; do not use Gmail.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "query": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["mailbox_id", "query"],
        },
    },
    {
        "name": "search_threads",
        "description": "Enterprise mail-index only. Search authorized company mailbox thread indexes by mailbox_id and query. Use for caigou/... and yingxiao/... paths; do not use Gmail labels.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "query": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["mailbox_id", "query"],
        },
    },
    {
        "name": "smart_search",
        "description": "Enterprise mail-index only. One-step search for user questions like '查一下 caigou/hqsc_gd3 里和审批/报价/样品有关的邮件'. Requires mailbox_id and query; never use Gmail labels.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "query": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["mailbox_id", "query"],
        },
    },
    {
        "name": "get_evidence",
        "description": "Enterprise mail-index only. Return original indexed evidence by evidence_id or thread_id within an authorized company mailbox_id. Do not use Gmail.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "evidence_id": {"type": "string"}, "thread_id": {"type": "string"}},
            "required": ["mailbox_id"],
        },
    },
    {
        "name": "rebuild_index",
        "description": "Enterprise mail-index only. Request server-side index rebuild for an authorized mailbox_id when explicitly allowed. Do not use Gmail.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["mailbox_id", "reason"],
        },
    },
]


def _mcp_success(message_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _mcp_error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _mcp_text_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}


def _handle_mcp_message(user: Dict[str, Any], message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        return _mcp_success(
            message_id,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "emailProjectAnalysis", "version": "0.2.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _mcp_success(message_id, {})
    if method == "tools/list":
        return _mcp_success(message_id, {"tools": MCP_TOOLS})
    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _mcp_error(message_id, -32602, "tool arguments must be an object")
        if tool_name not in TOOLS:
            return _mcp_error(message_id, -32601, f"unknown tool: {tool_name}")
        try:
            result = TOOLS[tool_name](user, arguments)
            _audit(user, tool_name, arguments, str(result.get("status", "ok")))
            return _mcp_success(message_id, _mcp_text_result(result))
        except Exception as exc:
            _audit(user, tool_name, arguments, "error")
            return _mcp_error(message_id, -32000, str(exc))
    return _mcp_error(message_id, -32601, f"unknown method: {method}")


def _handle_mcp_payload(user: Dict[str, Any], payload: Any) -> Optional[Any]:
    """Handle stateless JSON-RPC MCP messages over HTTP POST /mcp.

    This keeps user clients from needing the local stdio bridge when their
    agent supports remote MCP/HTTP directly. The same token permission model
    and same tool functions are used as the legacy HTTP endpoints.
    """
    if isinstance(payload, list):
        responses = []
        for message in payload:
            if isinstance(message, dict):
                response = _handle_mcp_message(user, message)
                if response is not None:
                    responses.append(response)
            else:
                responses.append(_mcp_error(None, -32600, "invalid MCP message"))
        return responses if responses else None
    if isinstance(payload, dict):
        return _handle_mcp_message(user, payload)
    return _mcp_error(None, -32600, "invalid MCP message")


PUBLIC_MCP_METHODS = {"initialize", "notifications/initialized", "ping", "tools/list"}


def _mcp_payload_requires_auth(payload: Any) -> bool:
    messages = payload if isinstance(payload, list) else [payload]
    return any(
        not isinstance(message, dict) or message.get("method") not in PUBLIC_MCP_METHODS
        for message in messages
    )


TOOLS = {
    "list_mailboxes": list_mailboxes,
    "get_index_status": get_index_status,
    "query_summary": query_summary,
    "search_threads": search_threads,
    "smart_search": search_threads,
    "get_evidence": get_evidence,
    "rebuild_index": rebuild_index,
}


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MailApiHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.strip("/")
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            _json_response(self, 400, {"error": "invalid_json"})
            return

        user = _current_user(self)
        if path == "mcp":
            if not user and _mcp_payload_requires_auth(payload):
                _json_response(self, 401, {"error": "unauthorized"})
                return
            response = _handle_mcp_payload(user or {}, payload)
            if response is None:
                _empty_response(self, 202)
                return
            _json_response(self, 200, response)
            return

        if not user:
            _json_response(self, 401, {"error": "unauthorized"})
            return

        tool = path
        if tool not in TOOLS:
            _json_response(self, 404, {"error": "unknown_tool", "tool": tool})
            return
        try:
            result = TOOLS[tool](user, payload)
            _audit(user, tool, payload, str(result.get("status", "ok")))
            _json_response(self, 200, result)
        except Exception as exc:  # Keep API errors explicit and auditable.
            _audit(user, tool, payload, "error")
            _json_response(self, 500, {"error": "internal_error", "message": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.strip("/")
        if path == "mcp":
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        _json_response(self, 405, {"error": "method_not_allowed", "message": "Use POST."})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def main() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), MailApiHandler)
    print(f"mail data API listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()



