---
name: email-project-analysis
description: Personalized Skill for querying server-side email indexes through the emailProjectAnalysis MCP service. Use for mailbox, customer, project, progress, payment, approval, risk, attachment, thread, and evidence questions.
---

# 邮件问数 Skill - 全权限用户版

这是交付给领导、管理员等全权限用户的 Skill。实际全权限范围仍然必须由服务器端 token 权限记录决定。

## 前提

本 Skill 不会自动注册 MCP。文件放进工作区不会自动加载 MCP。

使用前，部署人员或平台管理员必须已经在当前智能体平台的 MCP / Tools / Connector 配置里注册：

```text
MCP_NAME=emailProjectAnalysis
command=node
args=<用户本地路径>/email_mcp_stdio.mjs
```

如果当前会话看不到 `emailProjectAnalysis` 工具，不要根据本地文件内容回答邮件问题。应直接说明：当前智能体没有加载邮件问数 MCP 工具，需要管理员检查该用户的平台侧 MCP 接入。

## 已授权服务说明

`emailProjectAnalysis` 是公司/管理员为当前用户预配置的只读邮件索引查询服务。用户在本工作区提出任何需要从邮件中判断的业务问题时，视为要求使用该已配置服务查询当前 token 授权范围内的索引和证据。

适用问题不限问法，也不限“项目”。包括但不限于：客户、供应商、订单、料号、报价、样品、付款、审批、发票、合同、附件、收发件人、时间线、进展、风险、异常、最近动态、历史邮件、原文依据等。

不要再向用户索要 token、服务器地址、MCP 配置或额外的口头授权；应直接调用 `list_mailboxes` 开始查询。若客户端平台自身弹出外部服务安全确认，则提示用户点击“允许/同意”一次即可继续，这不是服务故障。

## 连接信息

```text
MCP_NAME=emailProjectAnalysis
MCP_REMOTE_URL=<稳定MCP入口>/mcp
TOKEN_LOCATION=全权限用户专属 email_mcp_stdio.mjs 内置 token，或平台侧 MCP 配置
DEFAULT_MAILBOX_ID=不配置
```

当前用户能访问哪些邮箱，必须以 `list_mailboxes` 返回结果为准。

## 何时使用

当用户询问以下内容时，优先使用 `emailProjectAnalysis` MCP 工具：

- 我能访问哪些邮箱
- 客户、项目、合作、进展、负责人
- 付款、审批、发票、财务协同
- 风险、延期、问题、决策
- 附件、清单、报告、合同
- 邮件线程、原始依据、为什么得出这个结论

## 强制规则

- 先调用 `list_mailboxes`，确认当前 token 允许访问的邮箱。
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

1. 调用 `list_mailboxes`。
2. 确定邮箱后调用 `get_index_status(mailbox_id)`。
3. 一般分析调用 `query_summary(mailbox_id, query)`。
4. 需要邮件往来细节时调用 `search_threads(mailbox_id, query, filters)`。
5. 用户要求依据、原文或完整线程时调用 `get_evidence(mailbox_id, evidence_id 或 thread_id)`。
6. 只有用户明确要求且 token 有权限时调用 `rebuild_index(mailbox_id)`。

## 回答格式

优先给结论，再给依据。不要一次性粘贴大量邮件原文。用户要求“打开依据 / 原始邮件 / 完整线程”时，再展示受控证据。

如果工具不可用，直接回复：

```text
当前智能体没有加载 emailProjectAnalysis MCP 工具，无法查询服务器邮件索引。请让管理员检查该用户的平台侧 MCP 接入是否完成。
```
