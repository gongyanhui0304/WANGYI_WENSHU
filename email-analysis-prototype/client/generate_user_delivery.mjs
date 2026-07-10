#!/usr/bin/env node
// Generate trusted MCP user delivery files for one user or group token.
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
const mcpUrl = (args["mcp-url"] || args.url || "").replace(/\/$/, "");
const token = args.token || "";

if (!userId) fail("missing --user-id");
if (!mcpUrl) fail("missing --mcp-url, for example https://mail-analysis.company.example/mcp");
if (!token) fail("missing --token");

const outDir = path.join(projectRoot, "dist", "platform-delivery", userId);
const userDir = path.join(outDir, "user");

const bridgeTemplate = fs.readFileSync(path.join(projectRoot, "client", "email_mcp_stdio.mjs"), "utf8");
const userBridge = bridgeTemplate
  .replace("__MAIL_ANALYSIS_MCP_URL__", mcpUrl)
  .replace("__MAIL_ANALYSIS_TOKEN__", token);

const userSkillDoc = fs.readFileSync(path.join(projectRoot, "client", "PER_USER_SKILL_TEMPLATE.md"), "utf8");

const userFiles = [
  ["user/email_mcp_stdio.mjs", userBridge],
  ["user/SKILL.md", userSkillDoc],
];

fs.rmSync(outDir, { recursive: true, force: true });
for (const [name, content] of userFiles) {
  writeFileStrict(path.join(outDir, name), content);
}

console.log(JSON.stringify({
  user_id: userId,
  mcp_url: mcpUrl,
  output_dir: outDir,
  user_dir: userDir,
  delivery_mode: "trusted_connector_user_package",
  trusted_connector_name: "emailProjectAnalysis",
  user_side_authorization_required: false,
  admin_files_generated: false,
  user_files: userFiles.map(([name]) => name),
}, null, 2));
