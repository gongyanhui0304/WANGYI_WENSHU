#!/usr/bin/env node
// Generate platform-managed MCP delivery files for one user or group token.
// Usage:
//   node client/generate_user_delivery.mjs --user-id Benson --mcp-url https://mail-analysis.company.example/mcp --token xxx

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");

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

function writeFileStrict(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, { encoding: "utf8", mode: 0o600 });
}

const args = readArgs(process.argv);
const userId = args["user-id"] || args.user || "";
const displayName = args["display-name"] || userId;
const mcpUrl = (args["mcp-url"] || args.url || "").replace(/\/$/, "");
const token = args.token || "";

if (!userId) fail("missing --user-id");
if (!mcpUrl) fail("missing --mcp-url, for example https://mail-analysis.company.example/mcp");
if (!token) fail("missing --token");

const outDir = path.join(projectRoot, "dist", "platform-delivery", userId);
const adminDir = path.join(outDir, "platform-admin");
const userDir = path.join(outDir, "user");
const installPath = `C:\\email-mcp\\${userId}\\email_mcp_stdio.mjs`;

const stdioPlatformConfig = {
  name: "emailProjectAnalysis",
  description: `Email analysis stdio bridge for ${displayName}.`,
  command: "node",
  args: [installPath],
};

const remotePlatformConfig = {
  name: "emailProjectAnalysis",
  description: `Remote email analysis MCP registration for ${displayName}.`,
  transport: "http",
  url: mcpUrl,
  headers: {
    Authorization: `Bearer ${token}`,
  },
};

const bridgeTemplate = fs.readFileSync(path.join(projectRoot, "client", "email_mcp_stdio.mjs"), "utf8");
const userBridge = bridgeTemplate
  .replace("__MAIL_ANALYSIS_MCP_URL__", mcpUrl)
  .replace("__MAIL_ANALYSIS_TOKEN__", token);

const userSkillDoc = fs.readFileSync(path.join(projectRoot, "client", "PER_USER_SKILL_TEMPLATE.md"), "utf8");

const platformAdminDoc = [
  "# Platform Admin Setup: emailProjectAnalysis",
  "",
  "Users do not configure MCP themselves. Each user receives a dedicated stdio bridge and a dedicated remote MCP registration manifest.",
  "",
  "## Server-side permission rule",
  "",
  "Mailbox access is enforced only by the server-side token permissions file. The client bridge and SKILL.md do not grant mailboxes by themselves.",
  "",
  "## Remote MCP registration manifest",
  "",
  "Register `platform-admin/remote-mcp.per-user.json` only for this user. It contains the public MCP endpoint and this user's dedicated bearer token.",
  "",
  "Never share one user's registration manifest, token, or bridge file with another user.",
  "",
  "## Standard stdio MCP bridge",
  "",
  `Copy the two user package files to C:\\email-mcp\\${userId}\\, then register stdio MCP with:`,
  "",
  "name: emailProjectAnalysis",
  "command: node",
  `args: ${installPath}`,
  "",
  "The user package must contain only:",
  "",
  "- email_mcp_stdio.mjs",
  "- SKILL.md",
  "",
  "## Acceptance",
  "",
  "Open a new agent session. Confirm that `list_mailboxes`, `search_threads`, `get_evidence`, and `get_index_status` are available under `emailProjectAnalysis`.",
  `The MCP endpoint is ${mcpUrl}.`,
  "",
].join("\n");

const adminFiles = [
  ["platform-admin/PLATFORM_ADMIN_SETUP.md", platformAdminDoc],
  ["platform-admin/mcp-registration.stdio.json", JSON.stringify(stdioPlatformConfig, null, 2) + "\n"],
  ["platform-admin/remote-mcp.per-user.json", JSON.stringify(remotePlatformConfig, null, 2) + "\n"],
];

const userFiles = [
  ["user/email_mcp_stdio.mjs", userBridge],
  ["user/SKILL.md", userSkillDoc],
];

fs.rmSync(outDir, { recursive: true, force: true });
for (const [name, content] of [...adminFiles, ...userFiles]) {
  writeFileStrict(path.join(outDir, name), content);
}

console.log(JSON.stringify({
  user_id: userId,
  display_name: displayName,
  mcp_url: mcpUrl,
  output_dir: outDir,
  platform_admin_dir: adminDir,
  user_dir: userDir,
  delivery_mode: "per_user_stdio_bridge_with_separate_remote_manifest",
  user_side_manual_config_required: false,
  platform_admin_files: adminFiles.map(([name]) => name),
  user_files: userFiles.map(([name]) => name),
}, null, 2));
