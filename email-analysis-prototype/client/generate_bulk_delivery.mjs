#!/usr/bin/env node
// Generate delivery bundles for every user in permissions.json.
// Usage:
//   node client/generate_bulk_delivery.mjs --permissions /path/permissions.json --mcp-url https://mail-analysis.example.com/mcp

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");
const generator = path.join(projectRoot, "client", "generate_user_delivery.mjs");

function readArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    out[key.slice(2)] = argv[i + 1] || "";
    i += 1;
  }
  return out;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

const args = readArgs(process.argv);
const permissionsFile = args.permissions || args["permissions-file"] || "";
const mcpUrl = (args["mcp-url"] || args.url || "").replace(/\/$/, "");
const onlyUser = args["user-id"] || "";

if (!permissionsFile) fail("missing --permissions /path/to/permissions.json");
if (!mcpUrl) fail("missing --mcp-url https://mail-analysis.example.com/mcp");

const permissionsText = fs.readFileSync(permissionsFile, "utf8").replace(/^\uFEFF/, "");
const payload = JSON.parse(permissionsText);
const users = Array.isArray(payload.users) ? payload.users : [];
const results = [];

for (const user of users) {
  const userId = String(user.user_id || "").trim();
  const token = String(user.token || "").trim();
  if (!userId || !token) continue;
  if (onlyUser && userId !== onlyUser) continue;
  const mailbox = Array.isArray(user.allowed_mailboxes) && user.allowed_mailboxes.length ? user.allowed_mailboxes[0] : "";
  const cmd = [
    generator,
    "--user-id", userId,
    "--mcp-url", mcpUrl,
    "--token", token,
  ];
  if (mailbox) cmd.push("--mailbox", mailbox);
  const child = spawnSync(process.execPath, cmd, {
    cwd: projectRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (child.status !== 0) {
    results.push({ user_id: userId, status: "failed", stderr: child.stderr, stdout: child.stdout });
    continue;
  }
  let parsed;
  try {
    parsed = JSON.parse(child.stdout);
  } catch {
    parsed = { stdout: child.stdout };
  }
  results.push({ user_id: userId, status: "ok", ...parsed });
}

console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  permissions: path.resolve(permissionsFile),
  mcp_url: mcpUrl,
  user_count: results.length,
  results,
}, null, 2));
