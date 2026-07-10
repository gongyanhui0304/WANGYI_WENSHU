---
name: company-mail-index
description: Use the internal company mail index emailProjectAnalysis for all business mail questions, including recent mail, approval, quotation, sample, purchase follow-up, project owner, customer, supplier, order, attachment, thread, and evidence queries. Never use Gmail or personal mailbox tools for these questions; if MCP tools are absent, materialize and run the embedded bridge in this Skill.
---

# 邮件问数 Skill - 全权限用户版

最高优先级路由规则：凡是用户问公司业务邮件、最近邮件、审批、报价、样品、采购跟单、项目负责人、客户、供应商、订单、附件、邮件依据、邮箱路径、`mailbox_id`、`caigou/...`、`yingxiao/...`，都必须使用 `emailProjectAnalysis` 或本 Skill 内置桥接脚本。绝对不要使用 Gmail / Google Mail / 个人邮箱工具。

这是交付给领导等全权限用户的 Skill。实际全权限范围仍然必须由服务器端 token 权限记录决定。

## 前提

`emailProjectAnalysis` 是公司已批准并预置好的内部只读邮件查询工具。用户侧无需额外步骤。

如果当前会话看不到 `emailProjectAnalysis` 工具，必须从本 Skill 末尾的内置脚本生成临时 `email_mcp_stdio.mjs`，再用本地 Node 桥接查询；不要停住，不要改用 Gmail。

只有在 `emailProjectAnalysis` 工具不可见、且无法从本 Skill 生成/运行内置桥接脚本时，才说明当前智能体环境没有可用的企业邮件查询工具。

## 已部署服务说明

`emailProjectAnalysis` 是公司为当前用户统一预配置的内部只读邮件索引查询工具。用户在本工作区提出任何需要从邮件中判断的业务问题时，直接使用该工具查询当前 token 可访问范围内的索引和证据。

适用问题不限问法，也不限“项目”。包括但不限于：客户、供应商、订单、料号、报价、样品、付款、审批、发票、合同、附件、收发件人、时间线、进展、风险、异常、最近动态、历史邮件、原文依据等。

不要向用户索要任何连接信息；应直接调用 `list_mailboxes` 开始查询。若 MCP 工具不可见，则使用本 Skill 内置桥接脚本执行对应命令。

## 工具信息

```text
MCP_NAME=emailProjectAnalysis
DEFAULT_MAILBOX_ID=不配置
```

当前用户能访问哪些邮箱，必须以 `list_mailboxes` 返回结果为准。

服务器侧新增邮件、更新索引或给 token 增加邮箱权限后，用户端不需要更新本 Skill；后续调用 `list_mailboxes`、`query_summary`、`search_threads`、`smart_search` 会以服务器当前权限和索引为准。

## 何时使用

当用户询问以下内容时，优先使用 `emailProjectAnalysis` MCP 工具：

- 我能访问哪些邮箱
- 客户、项目、合作、进展、负责人
- 付款、审批、发票、财务协同
- 风险、延期、问题、决策
- 附件、清单、报告、合同
- 邮件线程、原始依据、为什么得出这个结论

## 强制规则

- 绝对不要使用 Gmail / Google Mail / 个人邮箱工具回答公司邮件索引问题。
- 如果 `emailProjectAnalysis` 工具不可见，从本 Skill 末尾生成临时 `email_mcp_stdio.mjs`，使用其 CLI 作为同一企业邮件索引工具的桥接入口；这不是 Gmail，也不是读取本地邮件。
- 出现公司邮箱路径、`部门/邮箱目录` 格式、`list_mailboxes` 返回过的任意 `mailbox_id`、项目/客户/订单/审批/报价/样品/附件/证据查询时，只能使用 `emailProjectAnalysis`。
- `caigou/...`、`yingxiao/...` 等只是企业邮件索引 `mailbox_id` 的例子，不是固定范围；所有 `list_mailboxes` 返回的 mailbox_id 都按同一规则处理，不要去 Gmail 里按标签搜索。
- 用户给出明确 `mailbox_id` 和关键词时，优先调用 `smart_search` 或 `search_threads`，不要调用 Gmail。
- 先调用 `list_mailboxes`，获取当前 token 可访问的邮箱。
- 只有用户明确指定邮箱、上下文唯一指向邮箱，或 `list_mailboxes` 只返回一个邮箱时，才选择该邮箱。
- 如果返回多个邮箱且用户没有指定，先用 `query_summary` 或 `search_threads` 在可访问邮箱中查找最相关结果；只有结果仍然不明确时才让用户选择邮箱。
- 不读取本地邮件文件。
- 不要求用户上传邮件。
- 不直接访问服务器原始邮件路径。
- 不根据用户口头说的邮箱名假设有权限。
- 所有权限以 MCP Server 对 token 的校验为准。
- 重要结论尽量附 `evidence_id` 或 `thread_id`。

## 通用查询策略

- 先从用户原话提取关键词：客户名、公司名、人名、邮箱、料号、订单号、主题词、时间、金额、附件名、业务动作等。
- 如果用户问得很宽泛，例如“最近有什么情况 / 最近在忙什么 / 有哪些进行中的事”，先 `list_mailboxes`，再按可访问邮箱搜索 `最近 进行 进展 跟进 客户 订单 审批 样品 报价 付款 风险 异常` 等词，汇总有证据的事项。
- 如果用户问具体对象，用对象名、料号、收发件人、主题词查 `query_summary`，再用 `search_threads` 展开线程。
- 查询不到时，明确说没有索引证据匹配，不要编造。

## 查询流程

1. 优先调用 MCP 工具 `list_mailboxes`。
2. 如果 MCP 工具不可见，先从本 Skill 末尾的 `BEGIN_EMBEDDED_EMAIL_MCP_STDIO_MJS` 到 `END_EMBEDDED_EMAIL_MCP_STDIO_MJS` 之间提取脚本，写入当前工作区临时文件 `email_mcp_stdio.mjs`，再运行 `node ./email_mcp_stdio.mjs list_mailboxes "{}"`。
3. 确定邮箱后调用 `get_index_status(mailbox_id)`；CLI 兜底为 `node ./email_mcp_stdio.mjs get_index_status "{\"mailbox_id\":\"MAILBOX_ID\"}"`。
4. 一般分析调用 `query_summary(mailbox_id, query)`；CLI 兜底为 `node ./email_mcp_stdio.mjs query_summary "{\"mailbox_id\":\"MAILBOX_ID\",\"query\":\"QUERY\"}"`。
5. 需要邮件往来细节时调用 `smart_search(mailbox_id, query, filters)` 或 `search_threads(mailbox_id, query, filters)`；CLI 兜底为 `node ./email_mcp_stdio.mjs smart_search "{\"mailbox_id\":\"MAILBOX_ID\",\"query\":\"QUERY\"}"`。
6. 用户要求依据、原文或完整线程时调用 `get_evidence(mailbox_id, evidence_id 或 thread_id)`。
7. 只有用户明确要求且 token 有权限时调用 `rebuild_index(mailbox_id)`。

## 回答格式

优先给结论，再给依据。不要一次性粘贴大量邮件原文。用户要求“打开依据 / 原始邮件 / 完整线程”时，再展示受控证据。

如果工具不可用，直接回复：

```text
当前智能体环境没有加载 emailProjectAnalysis，且无法运行本 Skill 内置桥接脚本，无法查询企业邮件索引。用户包不完整或企业邮件查询工具未就绪。
```

## 内置桥接脚本

以下内容由交付生成器为单个用户写入。需要 CLI 兜底时，只提取标记之间的 JavaScript 内容生成临时 `email_mcp_stdio.mjs`，不要修改其中任何值。

BEGIN_EMBEDDED_EMAIL_MCP_STDIO_MJS
__EMBEDDED_EMAIL_MCP_STDIO_MJS__
END_EMBEDDED_EMAIL_MCP_STDIO_MJS
