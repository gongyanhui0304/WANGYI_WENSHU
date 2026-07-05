#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal business web gateway for the mail analysis service.

This app is intentionally small and dependency-free. It is not the permission
boundary. It only maps an authenticated business user to that user's MCP token,
then calls the existing mail MCP HTTP API. Tokens are never sent to the browser.

Recommended production auth mode is `trusted_header`, where an enterprise
gateway/SSO layer injects a trusted user header after login.
"""

from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


APP_HOST = os.environ.get("BUSINESS_APP_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("BUSINESS_APP_PORT", "8780"))
MCP_BASE_URL = required_env("MAIL_MCP_BASE_URL").rstrip("/")
USER_TOKEN_FILE = Path(required_env("BUSINESS_USER_TOKEN_FILE"))
AUTH_MODE = os.environ.get("BUSINESS_AUTH_MODE", "trusted_header")
AUTH_HEADER = os.environ.get("BUSINESS_AUTH_HEADER", "X-Authenticated-User")
COOKIE_NAME = os.environ.get("BUSINESS_SESSION_COOKIE_NAME", "mail_user")


def load_user_map() -> Dict[str, Dict[str, Any]]:
    data = json.loads(USER_TOKEN_FILE.read_text(encoding="utf-8"))
    users = data.get("users", [])
    return {str(user.get("user_id")): user for user in users if user.get("user_id") and user.get("mcp_token")}


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler: BaseHTTPRequestHandler, status: int, body: str) -> None:
    encoded = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def parse_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    return json.loads(raw or "{}")


def current_user_id(handler: BaseHTTPRequestHandler) -> Optional[str]:
    if AUTH_MODE == "trusted_header":
        return handler.headers.get(AUTH_HEADER) or None

    if AUTH_MODE == "demo_cookie":
        raw_cookie = handler.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(raw_cookie)
        morsel = jar.get(COOKIE_NAME)
        return morsel.value if morsel else None

    return None


def current_user(handler: BaseHTTPRequestHandler) -> Optional[Dict[str, Any]]:
    user_id = current_user_id(handler)
    if not user_id:
        return None
    return load_user_map().get(user_id)


def call_mcp(user: Dict[str, Any], tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{MCP_BASE_URL}/{tool}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {user['mcp_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": "mcp_http_error", "status": exc.code, "detail": detail}
    except Exception as exc:  # Keep UI failures explicit.
        return {"error": "mcp_unavailable", "message": str(exc)}


PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>閭欢闂暟鍔╂墜</title>
  <style>
    :root { color-scheme: light; font-family: Arial, "Microsoft YaHei", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2933; }
    header { padding: 18px 24px; background: #172033; color: white; }
    main { max-width: 1080px; margin: 0 auto; padding: 24px; }
    .toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
    select, textarea, button { font: inherit; }
    select { min-width: 220px; padding: 8px; }
    textarea { width: 100%; min-height: 120px; padding: 12px; box-sizing: border-box; resize: vertical; }
    button { padding: 9px 16px; border: 0; background: #2563eb; color: white; cursor: pointer; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .panel { background: white; border: 1px solid #d9dee7; padding: 16px; margin-top: 16px; }
    pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
    .muted { color: #697386; }
    .error { color: #b42318; }
  </style>
</head>
<body>
  <header><h1>閭欢闂暟鍔╂墜</h1></header>
  <main>
    <div id="user" class="muted">姝ｅ湪璇诲彇鐧诲綍淇℃伅...</div>
    <div class="toolbar">
      <label>閭 <select id="mailbox"></select></label>
      <button id="refresh">鍒锋柊閭</button>
    </div>
    <textarea id="question" placeholder="渚嬪锛氭渶杩戜富瑕佸湪澶勭悊浠€涔堬紵浠樻瀹℃壒鐜板湪鎬庝箞鏍凤紵鍝簺椤圭洰鏈夐闄╋紵"></textarea>
    <div class="toolbar">
      <button id="ask">鎻愰棶</button>
      <button id="threads">鏌ョ浉鍏崇嚎绋?/button>
    </div>
    <div class="panel"><pre id="answer">绛夊緟鎻愰棶銆?/pre></div>
  </main>
  <script>
    const mailbox = document.querySelector("#mailbox");
    const user = document.querySelector("#user");
    const answer = document.querySelector("#answer");
    const question = document.querySelector("#question");
    const ask = document.querySelector("#ask");
    const threads = document.querySelector("#threads");
    const refresh = document.querySelector("#refresh");

    function show(data) {
      answer.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    }

    async function api(path, body) {
      const response = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: {"Content-Type": "application/json"},
        body: body ? JSON.stringify(body) : undefined
      });
      const data = await response.json();
      if (!response.ok) throw data;
      return data;
    }

    async function loadMe() {
      const me = await api("/api/me");
      user.textContent = `褰撳墠鐢ㄦ埛锛?{me.display_name || me.user_id}`;
      mailbox.innerHTML = "";
      for (const box of me.mailboxes || []) {
        const option = document.createElement("option");
        option.value = box.mailbox_id;
        option.textContent = box.display_name || box.mailbox_id;
        mailbox.appendChild(option);
      }
    }

    async function run(tool) {
      ask.disabled = true;
      threads.disabled = true;
      try {
        const data = await api(`/api/${tool}`, {
          mailbox_id: mailbox.value,
          query: question.value.trim()
        });
        show(data);
      } catch (err) {
        show(err);
      } finally {
        ask.disabled = false;
        threads.disabled = false;
      }
    }

    refresh.onclick = () => loadMe().catch(show);
    ask.onclick = () => run("ask");
    threads.onclick = () => run("threads");
    loadMe().catch(show);
  </script>
</body>
</html>
"""


class BusinessHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/index.html"):
            html_response(self, 200, PAGE)
            return

        if AUTH_MODE == "demo_cookie" and self.path.startswith("/login?user_id="):
            user_id = self.path.split("user_id=", 1)[1].split("&", 1)[0]
            self.send_response(302)
            self.send_header("Set-Cookie", f"{COOKIE_NAME}={html.escape(user_id)}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if self.path == "/api/me":
            user = current_user(self)
            if not user:
                json_response(self, 401, {"error": "not_logged_in"})
                return
            mailboxes = call_mcp(user, "list_mailboxes", {}).get("mailboxes", [])
            json_response(
                self,
                200,
                {
                    "user_id": user.get("user_id"),
                    "display_name": user.get("display_name"),
                    "mailboxes": mailboxes,
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        user = current_user(self)
        if not user:
            json_response(self, 401, {"error": "not_logged_in"})
            return

        payload = parse_json(self)
        mailbox_id = str(payload.get("mailbox_id") or "")
        query = str(payload.get("query") or "")

        if self.path == "/api/ask":
            json_response(self, 200, call_mcp(user, "query_summary", {"mailbox_id": mailbox_id, "query": query, "filters": {}}))
            return
        if self.path == "/api/threads":
            json_response(self, 200, call_mcp(user, "search_threads", {"mailbox_id": mailbox_id, "query": query, "filters": {}}))
            return

        json_response(self, 404, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def main() -> None:
    if not USER_TOKEN_FILE.exists():
        raise RuntimeError(f"BUSINESS_USER_TOKEN_FILE does not exist: {USER_TOKEN_FILE}")
    server = ThreadingHTTPServer((APP_HOST, APP_PORT), BusinessHandler)
    print(f"business web app listening on {APP_HOST}:{APP_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

