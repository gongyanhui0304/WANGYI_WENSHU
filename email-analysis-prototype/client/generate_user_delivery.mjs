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
  "# emailProjectAnalysis 邮件问数",
  "",
  "`emailProjectAnalysis` 是公司/管理员为当前用户预配置的只读邮件索引查询服务。用户在本工作区提出任何需要从邮件中判断的业务问题时，视为要求使用该已配置服务查询当前 token 授权范围内的索引和证据。",
  "",
  "适用问题不限问法，也不限“项目”。包括但不限于：客户、供应商、订单、料号、报价、样品、付款、审批、发票、合同、附件、收发件人、时间线、进展、风险、异常、最近动态、历史邮件、原文依据等。",
  "",
  "不要再向用户索要 token、服务器地址、MCP 配置或额外的口头授权；应直接调用 `list_mailboxes` 开始查询。若客户端平台自身弹出外部服务安全确认，则提示用户点击“允许/同意”一次即可继续，这不是服务故障。",
  "",
  "优先模式：调用已配置的 MCP 工具 `list_mailboxes`、`query_summary`、`search_threads`、`get_evidence` 和 `get_index_status`。",
  "",
  "工作区兜底：如果当前会话没有加载 MCP 工具，才使用终端运行本文件旁边的 `email_mcp_stdio.mjs`：",
  "",
  "node ./email_mcp_stdio.mjs list_mailboxes \"{}\"",
  "node ./email_mcp_stdio.mjs query_summary '{\"mailbox_id\":\"MAILBOX_ID\",\"query\":\"QUERY\"}'",
  "node ./email_mcp_stdio.mjs get_index_status '{\"mailbox_id\":\"MAILBOX_ID\"}'",
  "node ./email_mcp_stdio.mjs search_threads '{\"mailbox_id\":\"MAILBOX_ID\",\"query\":\"QUERY\"}'",
  "node ./email_mcp_stdio.mjs get_evidence '{\"mailbox_id\":\"MAILBOX_ID\",\"evidence_id\":\"EVIDENCE_ID\"}'",
  "",
  "解析 JSON 输出并基于证据回答。不要只查看源文件，不要搜索无关本地项目文件。",
  "",
  "强制规则：",
  "- 先调用 `list_mailboxes`，确认当前 token 允许访问的邮箱。",
  "- 只使用 `list_mailboxes` 返回的邮箱。",
  "- 如果用户没有指定邮箱，先用 `query_summary` 或 `search_threads` 在可访问邮箱中查找最相关结果；只有结果仍然不明确时才让用户选择邮箱。",
  "- 不读取本地邮件文件，不要求用户上传邮件，不直接访问服务器原始邮件路径。",
  "- 不根据用户口头说的邮箱名假设有权限；所有权限以 MCP Server 对 token 的校验为准。",
  "- 重要结论尽量附 `evidence_id` 或 `thread_id`。",
  "- 查询不到时，明确说没有索引证据匹配，不要编造。",
  "",
  "通用查询策略：",
  "- 先从用户原话提取关键词：客户名、公司名、人名、邮箱、料号、订单号、主题词、时间、金额、附件名、业务动作等。",
  "- 如果用户问得很宽泛，例如“最近有什么情况 / 最近在忙什么 / 有哪些进行中的事”，先 `list_mailboxes`，再按可访问邮箱搜索 `最近 进行 进展 跟进 客户 订单 审批 样品 报价 付款 风险 异常` 等词，汇总有证据的事项。",
  "- 如果用户问具体对象，用对象名、料号、收发件人、主题词查 `query_summary`，再用 `search_threads` 展开线程。",
  "- “打开依据 / 原文 / 完整线程”：调用 `get_evidence`。",
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

