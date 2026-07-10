---
name: email-project-analysis
description: Personalized Skill for querying server-side email indexes through the emailProjectAnalysis MCP service. Use for mailbox, customer, project, progress, payment, approval, risk, attachment, thread, and evidence questions.
---

# 邮件问数个人 Skill

这是交付给单个用户的 Skill。用户实际能访问哪些邮箱，不由本文件决定，只由服务器端 token 权限记录决定。

## 前提

`emailProjectAnalysis` 应由公司统一部署为受信任 MCP 连接器。用户侧不需要配置 MCP，不需要提供 token，不需要额外口头授权。

如果当前会话看不到 `emailProjectAnalysis` 工具，说明该智能体环境尚未完成统一连接器部署；不要向用户索要授权或要求用户手动配置，直接说明连接器未加载。

## 已部署服务说明

`emailProjectAnalysis` 是公司为当前用户统一预配置的只读邮件索引查询服务。用户在本工作区提出任何需要从邮件中判断的业务问题时，直接使用该已配置服务查询当前 token 可访问范围内的索引和证据。

适用问题不限问法，也不限“项目”。包括但不限于：客户、供应商、订单、料号、报价、样品、付款、审批、发票、合同、附件、收发件人、时间线、进展、风险、异常、最近动态、历史邮件、原文依据等。

不要再向用户索要 token、服务器地址、MCP 配置或额外的口头授权；应直接调用 `list_mailboxes` 开始查询。

## 连接信息

```text
MCP_NAME=emailProjectAnalysis
MCP_REMOTE_URL=<稳定MCP入口>/mcp
TOKEN_LOCATION=公司统一受信任连接器内置或平台侧托管
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

- 绝对不要使用 Gmail / Google Mail / 个人邮箱工具回答公司邮件索引问题。
- 出现 `caigou/...`、`yingxiao/...`、`hqsc_...`、公司邮箱路径、项目/客户/订单/审批/报价/样品/附件/证据查询时，只能使用 `emailProjectAnalysis`。
- `caigou/hqsc_gd3` 这类字符串是企业邮件索引的 `mailbox_id`，不是 Gmail 标签，不要去 Gmail 里按标签搜索。
- 用户给出明确 `mailbox_id` 和关键词时，优先调用 `smart_search` 或 `search_threads`，不要调用 Gmail。
- 先调用 `list_mailboxes`，确认当前 token 可访问的邮箱。
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
4. 需要邮件往来细节时调用 `smart_search(mailbox_id, query, filters)` 或 `search_threads(mailbox_id, query, filters)`。
5. 用户要求依据、原文或完整线程时调用 `get_evidence(mailbox_id, evidence_id 或 thread_id)`。
6. 只有用户明确要求且 token 有权限时调用 `rebuild_index(mailbox_id)`。

## 回答格式

优先给结论，再给依据。不要一次性粘贴大量邮件原文。用户要求“打开依据 / 原始邮件 / 完整线程”时，再展示受控证据。

如果工具不可用，直接回复：

```text
当前智能体环境没有加载受信任连接器 emailProjectAnalysis，无法查询服务器邮件索引。请联系部署侧检查统一 MCP 连接器是否已启用。
```
