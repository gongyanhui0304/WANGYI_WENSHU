---
name: email-project-analysis
description: Analyze local static exported email data in email-analysis-prototype. Use when a user asks in Codex about email-based project/topic progress, owners, people, unresolved issues, risks, reply status, evidence, raw emails, or full email threads from the local emails/王慧 corpus.
---

# 邮件项目分析

使用本 Skill 分析 `email-analysis-prototype/` 下的本地静态邮件数据。当前原始语料是用户提供的真实导出邮件，不使用虚拟邮件。

## 数据入口

- 项目/专题索引：`index/projects.yaml`
- 人员索引：`index/people.yaml`
- 专题摘要：`projects/<project_id>/summary.md`
- 专题时间线：`projects/<project_id>/timeline.md`
- 线程摘要：`projects/<project_id>/threads.md`
- 原始邮件：`emails/王慧/**/**/*_邮件提取.docx`

## 总规则

1. 先查索引，不要直接全量读取 `emails/王慧`。
2. 不要在每次提问时重建索引。
3. 只有索引不存在、索引损坏、用户明确要求“重新建立索引”或“重新分析全部邮件”时，才扫描全部邮件。
4. 不要修改原始邮件、附件或导出目录。
5. 不要编造邮件中没有的信息。
6. 证据不足时明确说明，并列出已经读取的依据。
7. 所有重要结论附上证据 ID 或原始邮件路径。
8. 进度只能写作“根据邮件估算”，不能称为 ERP、MES、财务系统或真实生产系统准确进度。
9. 回答优先给结论，用户要求依据时再展开原始邮件内容。

## 查询流程

### 查询具体专题

1. 读取 `index/projects.yaml`。
2. 根据专题名称、别名、客户、负责人或关键词识别 `project_id`。
3. 读取该专题 `summary.md`。
4. 如果摘要足够，直接回答。
5. 如果用户询问具体时间、人员、邮件内容、线程过程、客户/对方是否回复、为什么得出结论或查看依据，再读取 `timeline.md`、`threads.md` 和必要原始邮件。

### 查询具体人员

1. 读取 `index/people.yaml`。
2. 找到此人的专题列表。
3. 读取相关专题摘要。
4. 必要时只在对应专题的 `search_terms` 范围内搜索此人的发件人、收件人、抄送或正文记录。
5. 不要为了一个人员问题读取全部原始邮件。

### 查询全部专题

对“哪些专题高风险”“哪些事项可能延期/阻塞”“所有专题进度如何”等问题：

1. 读取 `index/projects.yaml`。
2. 只读取各专题 `summary.md`。
3. 不直接读取所有原始邮件。

### 查询原始依据

当用户说“查看依据”“打开这封邮件”“为什么得出这个结论”“查看完整沟通过程”：

1. 使用最近一次回答中引用的证据 ID、线程 ID、专题、人员、问题或风险。
2. 读取对应 `threads.md` 或原始 `*_邮件提取.docx`。
3. 如果需要读取 docx 正文，可使用 Codex 本地文件能力或临时命令提取 `word/document.xml` 文本；不要创建持久脚本，不要修改原文件。
4. 展示必要邮件元数据和正文摘要；用户要求完整邮件时再展示完整正文。

## 上下文和代词

- “这个项目”“这个专题”“它”指向最近一次明确识别的项目/专题。
- “他/她”指向最近一次明确识别的人员。
- “这封邮件”指向最近一次展示的邮件。
- “这个问题/风险”指向最近一次讨论的问题或风险。
- 无法唯一判断时，不要猜测；说明歧义并列出可能对象。

## 项目/专题状态回答格式

```markdown
## 项目概况
- 项目：<专题名称>
- 负责人：<负责人>
- 当前阶段：<阶段>
- 邮件估算进度：<百分比>（根据邮件估算）
- 可信度：<高/中/低>
- 风险等级：<高/中/低>
项目进度：[██████░░░░] 60%

## 总结
...

## 已完成
- ...

## 正在进行
- ...

## 未解决问题
- ...

## 当前风险
- ...

## 关键依据
- S001 `<原始邮件路径>`
```

进度条按十分格近似显示。
