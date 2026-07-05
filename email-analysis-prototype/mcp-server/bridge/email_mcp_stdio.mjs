#!/usr/bin/env node
// Local stdio MCP bridge for Codex. Dependency-free; uses Node built-ins only.
// Codex runs this process as an MCP server. It forwards tool calls to the
// server-side mail HTTP data API and never reads local mail files.

const BASE_URL = (process.env.MAIL_MCP_BASE_URL || "http://127.0.0.1:8765").replace(/\/$/, "");
const TOKEN = process.env.MAIL_MCP_TOKEN || "";

const tools = [
  {
    name: "list_mailboxes",
    description: "Return mailboxes authorized for the current Codex user.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "get_index_status",
    description: "Return server-side index status for an authorized mailbox.",
    inputSchema: { type: "object", properties: { mailbox_id: { type: "string" } }, required: ["mailbox_id"] },
  },
  {
    name: "query_summary",
    description: "Query project, customer, people, risk, progress, payment, approval, and other summaries from the server index.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, query: { type: "string" }, filters: { type: "object" } },
      required: ["mailbox_id", "query"],
    },
  },
  {
    name: "search_threads",
    description: "Search authorized mailbox thread indexes.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, query: { type: "string" }, filters: { type: "object" } },
      required: ["mailbox_id", "query"],
    },
  },
  {
    name: "get_evidence",
    description: "Return original evidence by evidence_id or thread_id within an authorized mailbox.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, evidence_id: { type: "string" }, thread_id: { type: "string" } },
      required: ["mailbox_id"],
    },
  },
  {
    name: "rebuild_index",
    description: "Request server-side index rebuild for an authorized mailbox when explicitly allowed.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, reason: { type: "string" } },
      required: ["mailbox_id", "reason"],
    },
  },
];

let buffer = Buffer.alloc(0);
let outputMode = "line";

function writeMessage(message) {
  const json = JSON.stringify(message);
  if (outputMode === "content-length") {
    const body = Buffer.from(json, "utf8");
    process.stdout.write(`Content-Length: ${body.length}\r\n\r\n`);
    process.stdout.write(body);
    return;
  }
  process.stdout.write(`${json}\n`);
}

function success(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function error(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

async function callHttpTool(name, args) {
  if (!TOKEN) return { error: "missing_MAIL_MCP_TOKEN" };
  const payload = { ...(args || {}) };
  try {
    const response = await fetch(`${BASE_URL}/${name}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${TOKEN}`,
      },
      body: JSON.stringify(payload),
    });
    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    if (!response.ok) return { error: "http_error", status: response.status, body: data };
    return data;
  } catch (err) {
    return { error: "connection_error", message: String(err && err.message ? err.message : err), base_url: BASE_URL };
  }
}

async function handle(message) {
  const { id, method } = message;
  const params = message.params || {};
  if (method === "initialize") {
    return success(id, {
      protocolVersion: params.protocolVersion || "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "emailProjectAnalysis", version: "0.1.0" },
    });
  }
  if (method === "notifications/initialized") return null;
  if (method === "ping") return success(id, {});
  if (method === "tools/list") return success(id, { tools });
  if (method === "tools/call") {
    const name = params.name;
    const args = params.arguments || {};
    if (!tools.some((tool) => tool.name === name)) return error(id, -32601, `unknown tool: ${name}`);
    const data = await callHttpTool(name, args);
    return success(id, { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] });
  }
  return error(id, -32601, `unknown method: ${method}`);
}

async function processBuffer() {
  while (true) {
    const sep = buffer.indexOf("\r\n\r\n");
    if (sep === -1) break;
    const header = buffer.slice(0, sep).toString("ascii");
    const match = header.match(/Content-Length:\s*(\d+)/i);
    if (!match) {
      buffer = buffer.slice(sep + 4);
      continue;
    }
    const length = Number(match[1]);
    const start = sep + 4;
    const end = start + length;
    if (buffer.length < end) return;
    outputMode = "content-length";
    const body = buffer.slice(start, end).toString("utf8");
    buffer = buffer.slice(end);
    let message;
    try {
      message = JSON.parse(body);
    } catch (err) {
      writeMessage(error(null, -32700, "parse error"));
      continue;
    }
    const response = await handle(message);
    if (response) writeMessage(response);
  }

  while (true) {
    const newline = buffer.indexOf("\n");
    if (newline === -1) return;
    outputMode = "line";
    const line = buffer.slice(0, newline).toString("utf8").trim();
    buffer = buffer.slice(newline + 1);
    if (!line) continue;
    let message;
    try {
      message = JSON.parse(line);
    } catch (err) {
      writeMessage(error(null, -32700, "parse error"));
      continue;
    }
    const response = await handle(message);
    if (response) writeMessage(response);
  }
}

process.stdin.on("data", (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  processBuffer().catch((err) => writeMessage(error(null, -32000, String(err && err.message ? err.message : err))));
});

