#!/usr/bin/env node
// Local stdio MCP bridge for MCP-capable agents. Dependency-free; uses Node
// built-ins only. The agent runs this process as an MCP server over stdio.
// It forwards tool calls to the server-side mail HTTP/MCP API and never reads
// local mail files.

// Stable user delivery:
// - Admins may embed the service URL/token into a per-user copy of this file.
// - Environment variables still override the embedded values for development.
// - The URL may be either a remote MCP endpoint ending with /mcp, or the legacy
//   HTTP base URL that exposes /list_mailboxes, /query_summary, etc.
const EMBEDDED_MCP_URL = "__MAIL_ANALYSIS_MCP_URL__";
const EMBEDDED_TOKEN = "__MAIL_ANALYSIS_TOKEN__";

function configuredValue(...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text && !text.includes("__MAIL_ANALYSIS_")) return text;
  }
  return "";
}

const BASE_URL = configuredValue(process.env.MAIL_MCP_BASE_URL, EMBEDDED_MCP_URL, "http://127.0.0.1:8765").replace(/\/$/, "");
const TOKEN = configuredValue(process.env.MAIL_MCP_TOKEN, EMBEDDED_TOKEN);

const tools = [
  {
    name: "list_mailboxes",
    description: "Enterprise mail-index only. Return authorized mailbox_id values such as caigou/hqsc_gd3 or yingxiao/xxx. Use this instead of Gmail for company mailbox paths, project mail, approval, quotation, sample, customer, supplier, order, attachment, evidence, and thread questions.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "get_index_status",
    description: "Enterprise mail-index only. Return server-side index status for an authorized mailbox_id such as caigou/hqsc_gd3. Do not use Gmail for these mailbox_id paths.",
    inputSchema: { type: "object", properties: { mailbox_id: { type: "string" } }, required: ["mailbox_id"] },
  },
  {
    name: "query_summary",
    description: "Enterprise mail-index only. Query project, customer, people, owner, risk, progress, payment, approval, quotation, sample, order, attachment, and evidence summaries from the server index. Use for caigou/... and yingxiao/... mailbox_id queries; do not use Gmail.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, query: { type: "string" }, filters: { type: "object" } },
      required: ["mailbox_id", "query"],
    },
  },
  {
    name: "search_threads",
    description: "Enterprise mail-index only. Search authorized company mailbox thread indexes by mailbox_id and query. Use for caigou/... and yingxiao/... paths; do not use Gmail labels.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, query: { type: "string" }, filters: { type: "object" } },
      required: ["mailbox_id", "query"],
    },
  },
  {
    name: "smart_search",
    description: "Enterprise mail-index only. One-step search for user questions like '查一下 caigou/hqsc_gd3 里和审批/报价/样品有关的邮件'. Requires mailbox_id and query; never use Gmail labels.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, query: { type: "string" }, filters: { type: "object" } },
      required: ["mailbox_id", "query"],
    },
  },
  {
    name: "get_evidence",
    description: "Enterprise mail-index only. Return original indexed evidence by evidence_id or thread_id within an authorized company mailbox_id. Do not use Gmail.",
    inputSchema: {
      type: "object",
      properties: { mailbox_id: { type: "string" }, evidence_id: { type: "string" }, thread_id: { type: "string" } },
      required: ["mailbox_id"],
    },
  },
  {
    name: "rebuild_index",
    description: "Enterprise mail-index only. Request server-side index rebuild for an authorized mailbox_id when explicitly allowed. Do not use Gmail.",
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
  const remoteName = name === "smart_search" ? "search_threads" : name;
  try {
    const isRemoteMcp = BASE_URL.endsWith("/mcp");
    const url = isRemoteMcp ? BASE_URL : `${BASE_URL}/${remoteName}`;
    const body = isRemoteMcp
      ? {
          jsonrpc: "2.0",
          id: Date.now(),
          method: "tools/call",
          params: { name: remoteName, arguments: payload },
        }
      : payload;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${TOKEN}`,
      },
      body: JSON.stringify(body),
    });
    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    if (!response.ok) return { error: "http_error", status: response.status, body: data };
    if (isRemoteMcp && data && data.result && Array.isArray(data.result.content)) {
      const textItem = data.result.content.find((item) => item && item.type === "text");
      if (textItem && typeof textItem.text === "string") {
        try {
          return JSON.parse(textItem.text);
        } catch {
          return { text: textItem.text };
        }
      }
    }
    if (isRemoteMcp && data && data.error) return { error: "remote_mcp_error", body: data.error };
    return data;
  } catch (err) {
    return { error: "connection_error", message: String(err && err.message ? err.message : err), base_url: BASE_URL };
  }
}

async function runCli() {
  const command = process.argv[2] || "";
  if (!command) return false;
  if (command === "--help" || command === "help") {
    process.stdout.write(`${JSON.stringify({ tools: tools.map((tool) => tool.name), usage: "node email_mcp_stdio.mjs <tool-name> '<json-arguments>'" }, null, 2)}\n`);
    return true;
  }
  if (!tools.some((tool) => tool.name === command)) {
    process.stderr.write(`unknown tool: ${command}\n`);
    process.exitCode = 2;
    return true;
  }
  let args = {};
  const rawArgs = process.argv[3] || "{}";
  try {
    args = JSON.parse(rawArgs);
  } catch (err) {
    process.stderr.write(`invalid JSON arguments: ${String(err && err.message ? err.message : err)}\n`);
    process.exitCode = 2;
    return true;
  }
  const data = await callHttpTool(command, args);
  process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
  if (data && data.error) process.exitCode = 1;
  return true;
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

if (process.argv.length > 2) {
  runCli().catch((err) => {
    process.stderr.write(`${String(err && err.message ? err.message : err)}\n`);
    process.exitCode = 1;
  });
} else {
  process.stdin.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    processBuffer().catch((err) => writeMessage(error(null, -32000, String(err && err.message ? err.message : err))));
  });
}
