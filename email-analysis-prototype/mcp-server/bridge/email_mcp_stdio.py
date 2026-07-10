#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local stdio MCP bridge for Codex.

Codex runs this process as an MCP server. The bridge forwards tool calls to the
server-side mail HTTP data API. It never reads local mail files.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = os.environ.get("MAIL_MCP_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
TOKEN = os.environ.get("MAIL_MCP_TOKEN", "")

TOOLS = [
    {
        "name": "list_mailboxes",
        "description": "Return mailboxes authorized for the current Codex user.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_index_status",
        "description": "Return server-side index status for an authorized mailbox.",
        "inputSchema": {"type": "object", "properties": {"mailbox_id": {"type": "string"}}, "required": ["mailbox_id"]},
    },
    {
        "name": "query_summary",
        "description": "Query project, customer, people, risk, progress, payment, approval, and other summaries from the server index.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "query": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["mailbox_id", "query"],
        },
    },
    {
        "name": "search_threads",
        "description": "Search authorized mailbox thread indexes.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "query": {"type": "string"}, "filters": {"type": "object"}},
            "required": ["mailbox_id", "query"],
        },
    },
    {
        "name": "get_evidence",
        "description": "Return original evidence by evidence_id or thread_id within an authorized mailbox.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "evidence_id": {"type": "string"}, "thread_id": {"type": "string"}},
            "required": ["mailbox_id"],
        },
    },
    {
        "name": "rebuild_index",
        "description": "Request server-side index rebuild for an authorized mailbox when explicitly allowed.",
        "inputSchema": {
            "type": "object",
            "properties": {"mailbox_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["mailbox_id", "reason"],
        },
    },
]


def read_message() -> Optional[Dict[str, Any]]:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii", errors="replace").partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(message: Dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def call_http_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not TOKEN:
        return {"error": "missing_MAIL_MCP_TOKEN"}
    request = urllib.request.Request(
        f"{BASE_URL}/{name}",
        data=json.dumps(arguments, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": "http_error", "status": exc.code, "body": exc.read().decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"error": "connection_error", "message": str(exc), "base_url": BASE_URL}


def success(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        return success(
            request_id,
            {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "emailProjectAnalysis", "version": "0.1.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return success(request_id, {})
    if method == "tools/list":
        return success(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        tool_names = {tool["name"] for tool in TOOLS}
        if name not in tool_names:
            return error(request_id, -32601, f"unknown tool: {name}")
        data = call_http_tool(name, arguments)
        return success(request_id, {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]})
    return error(request_id, -32601, f"unknown method: {method}")


def main() -> None:
    while True:
        message = read_message()
        if message is None:
            break
        response = handle(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    main()

