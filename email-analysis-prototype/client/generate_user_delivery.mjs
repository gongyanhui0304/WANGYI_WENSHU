#!/usr/bin/env node
// Generate platform-managed stdio delivery files for one user or group token.
// Usage:
//   node client/generate_user_delivery.mjs --user-id caigou_test --mcp-url https://mail-analysis.company.example/mcp --token xxx

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
const mailboxHint = args["mailbox"] || args["mailbox-id"] || "caigou/hqsc_gd3";

if (!userId) fail("missing --user-id");
if (!mcpUrl) fail("missing --mcp-url, for example https://mail-analysis.company.example/mcp");
if (!token) fail("missing --token");

const outDir = path.join(projectRoot, "dist", "platform-delivery", userId);
const adminDir = path.join(outDir, "platform-admin");
const userDir = path.join(outDir, "user");
const userTestDir = path.join(outDir, "user-test");

const installPath = `C:\\email-mcp\\${userId}\\email_mcp_stdio.mjs`;

const platformConfig = {
  name: "emailProjectAnalysis",
  command: "node",
  args: [installPath],
};

const remotePlatformConfig = {
  name: "emailProjectAnalysis",
  transport: "streamable-http",
  url: mcpUrl,
  headers: {
    Authorization: `Bearer ${token}`,
  },
};

const bridgeTemplatePath = path.join(projectRoot, "client", "email_mcp_stdio.mjs");
const bridgeTemplate = fs.readFileSync(bridgeTemplatePath, "utf8");
const userBridge = bridgeTemplate
  .replace("__MAIL_ANALYSIS_MCP_URL__", mcpUrl)
  .replace("__MAIL_ANALYSIS_TOKEN__", token);

const platformAdminDoc = [
  "# Platform Admin Setup: emailProjectAnalysis",
  "",
  "Users do not configure MCP themselves. Prefer the per-user remote MCP registration on platforms that support Streamable HTTP.",
  "",
  "## Preferred: Remote MCP",
  "",
  "Register platform-admin/remote-mcp-registration.json for this user. It contains the public MCP endpoint and the user's dedicated bearer token.",
  "",
  "## Fallback: Stdio MCP",
  "",
  `Copy email_mcp_stdio.mjs and SKILL.md to C:\\email-mcp\\${userId}\\, then register:`,
  "",
  "name: emailProjectAnalysis",
  "command: node",
  `args: ${installPath}`,
  "",
  "The user must never edit MCP configuration, token, endpoint, or bridge files. Never share one user's registration or bridge with another user.",
  "",
  "## Acceptance",
  "",
  "Open a new agent session. Confirm that list_mailboxes, search_threads, get_evidence, and get_index_status are available under emailProjectAnalysis.",
  `The MCP endpoint is ${mcpUrl}.`,
  "",
].join("\n");

const userTestDoc = [
  "# Email Analysis Acceptance Test",
  "",
  "The user does not configure MCP. The platform administrator must load emailProjectAnalysis before this test.",
  "",
  "Ask the agent to list all accessible mailboxes. Then ask it to search relevant mail and expand one evidence item.",
  `Mailbox hint: ${mailboxHint}`,
  "",
  "If emailProjectAnalysis or list_mailboxes is unavailable, report that MCP was not loaded into the current agent session.",
  "",
].join("\n");

const userSkillDoc = [
  "# emailProjectAnalysis Mail Analysis",
  "",
  "For every mail question, use emailProjectAnalysis. The user only asks questions and never configures tools.",
  "",
  "Preferred mode: call the configured MCP tools list_mailboxes, search_threads, get_evidence, and get_index_status.",
  "",
  "Workspace fallback: if those MCP tools are not loaded, use the terminal to run the email_mcp_stdio.mjs file located beside this SKILL.md:",
  "",
  "node ./email_mcp_stdio.mjs list_mailboxes \"{}\"",
  "node ./email_mcp_stdio.mjs get_index_status '{\"mailbox_id\":\"MAILBOX_ID\"}'",
  "node ./email_mcp_stdio.mjs search_threads '{\"mailbox_id\":\"MAILBOX_ID\",\"query\":\"QUERY\"}'",
  "node ./email_mcp_stdio.mjs get_evidence '{\"mailbox_id\":\"MAILBOX_ID\",\"evidence_id\":\"EVIDENCE_ID\"}'",
  "",
  "Parse the JSON output and answer the user from that evidence. Do not merely inspect the source file and do not search unrelated local project files.",
  "Always list mailboxes before selecting one. Never ask the user for a token, endpoint, MCP configuration, server path, or raw mail files.",
  "Only use mailboxes returned by list_mailboxes. Clearly distinguish indexed results from mailboxes that are still indexing.",
  "",
].join("\n");
const adminFiles = [
  ["platform-admin/PLATFORM_ADMIN_SETUP.md", platformAdminDoc],
  ["platform-admin/mcp-registration.json", JSON.stringify(platformConfig, null, 2) + "\n"],
  ["platform-admin/remote-mcp-registration.json", JSON.stringify(remotePlatformConfig, null, 2) + "\n"],
];

const userFiles = [
  ["user/email_mcp_stdio.mjs", userBridge],
  ["user/SKILL.md", userSkillDoc],
  ["user-test/USER_TEST_PROMPT.md", userTestDoc],
];

fs.rmSync(outDir, { recursive: true, force: true });
for (const [name, content] of [...adminFiles, ...userFiles]) {
  writeFileStrict(path.join(outDir, name), content);
}

console.log(JSON.stringify({
  user_id: userId,
  mcp_url: mcpUrl,
  output_dir: outDir,
  platform_admin_dir: adminDir,
  user_dir: userDir,
  user_test_dir: userTestDir,
  delivery_mode: "platform_managed_stdio_bridge_with_embedded_remote_mcp",
  user_side_manual_config_required: false,
  platform_admin_files: adminFiles.map(([name]) => name),
  user_files: userFiles.map(([name]) => name),
}, null, 2));

