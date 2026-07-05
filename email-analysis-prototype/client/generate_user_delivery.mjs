#!/usr/bin/env node
// Generate per-user delivery files from the stable bridge and Skill template.
// Usage:
//   node client/generate_user_delivery.mjs --user-id leader --mcp-url https://mail-analysis.company.example/mcp --token xxx

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
const templateName = args["skill-template"] || "PER_USER_SKILL_TEMPLATE.md";

if (!userId) fail("missing --user-id");
if (!mcpUrl) fail("missing --mcp-url, for example https://mail-analysis.company.example/mcp");
if (!token) fail("missing --token");

const bridgeTemplatePath = path.join(__dirname, "email_mcp_stdio.mjs");
const skillTemplatePath = path.isAbsolute(templateName) ? templateName : path.join(__dirname, templateName);
const outDir = path.join(projectRoot, "dist", "user-delivery", userId);
const userDir = path.join(outDir, "user");
const itDir = path.join(outDir, "it");

const bridge = fs.readFileSync(bridgeTemplatePath, "utf8")
  .replaceAll("__MAIL_ANALYSIS_MCP_URL__", mcpUrl)
  .replaceAll("__MAIL_ANALYSIS_TOKEN__", token);

const stableBase = mcpUrl.endsWith("/mcp") ? mcpUrl.slice(0, -4) : mcpUrl;
const skill = fs.readFileSync(skillTemplatePath, "utf8")
  .replaceAll("<稳定MCP入口>/mcp", mcpUrl)
  .replaceAll("<稳定MCP入口>", stableBase);

const bridgeRelativeForIt = "../user/email_mcp_stdio.mjs";

const installDoc = `# 邮件问数 MCP 接入说明（部署/IT 使用）

这份文件给部署人员或平台管理员使用，不是给业务用户日常阅读的说明。

## 关键结论

- 文件放进工作区不会自动加载 MCP。
- \`SKILL.md\` 只告诉智能体什么时候使用邮件问数工具，不负责注册工具。
- \`email_mcp_stdio.mjs\` 只是本地 stdio 桥接程序，必须被智能体平台注册为 MCP server。
- 最终用户不需要手动提醒智能体读取 mjs 或 Skill；如果还需要提醒，说明平台侧 MCP 没接好，或当前会话没有加载该 Skill/工具。

## 本交付包结构

\`\`\`text
user/
  email_mcp_stdio.mjs       用户专属 MCP stdio 桥接文件，内置该用户 token
  SKILL.md                  邮件问数 Skill/使用规则
it/
  IT_INSTALL.md             本说明，给部署/平台管理员
  mcp-config.codex.toml     Codex MCP 配置片段
  mcp-config.generic.json   通用 MCP JSON 配置片段
\`\`\`

## 必须完成的接入动作

在目标智能体平台里注册 MCP server：

\`\`\`text
MCP name: emailProjectAnalysis
command: node
args: ${bridgeRelativeForIt}
\`\`\`

生产环境建议把 \`${bridgeRelativeForIt}\` 改成该机器上的绝对路径，例如：

\`\`\`text
D:/email-mcp/users/${userId}/user/email_mcp_stdio.mjs
/opt/email-mcp/users/${userId}/user/email_mcp_stdio.mjs
\`\`\`

如果平台支持远程 MCP connector，也可以由管理员在平台侧直接配置：

\`\`\`text
name: emailProjectAnalysis
url: ${mcpUrl}
authorization: Bearer <该用户 token>
\`\`\`

两种方式二选一即可。权限仍然只由服务器端 permissions.json 里的 token 记录决定。

## 验收步骤

1. 注册 MCP 后，重启智能体平台或新开会话。
2. 确认当前会话工具列表里有 \`emailProjectAnalysis\`。
3. 让智能体问：\`我能访问哪些邮箱？\`。
4. 如果回答里出现 \`list_mailboxes\` 的真实结果，说明接入成功。
5. 如果智能体说没有邮件工具、只会读取本地文件，或要求用户手动告诉它读 mjs/Skill，说明 MCP 没注册成功。
`;

const codexConfig = `[mcp_servers.emailProjectAnalysis]
command = "node"
args = ["${bridgeRelativeForIt}"]
startup_timeout_sec = 30
`;

const genericConfig = {
  mcpServers: {
    emailProjectAnalysis: {
      command: "node",
      args: [bridgeRelativeForIt],
    },
  },
};

const userFiles = [
  ["user/email_mcp_stdio.mjs", bridge],
  ["user/SKILL.md", skill],
];

const itFiles = [
  ["it/IT_INSTALL.md", installDoc],
  ["it/mcp-config.codex.toml", codexConfig],
  ["it/mcp-config.generic.json", JSON.stringify(genericConfig, null, 2) + "\n"],
];

fs.rmSync(outDir, { recursive: true, force: true });
for (const [name, content] of [...userFiles, ...itFiles]) {
  writeFileStrict(path.join(outDir, name), content);
}

console.log(JSON.stringify({
  user_id: userId,
  mcp_url: mcpUrl,
  output_dir: outDir,
  user_dir: userDir,
  it_dir: itDir,
  user_files: userFiles.map(([name]) => name),
  it_files: itFiles.map(([name]) => name),
}, null, 2));
