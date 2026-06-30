# 邮件项目分析原型

本目录是一个只依赖本地静态文件和 Codex Skill 的验证原型。当前语料来自用户放入的真实导出邮件：`emails/王慧`。

当用户询问邮件项目、经营专题、项目进度、负责人、风险、问题、邮件状态或原始依据时，优先使用 `skills/email-project-analysis/SKILL.md`。

## 查询原则

- 先读取 `index/projects.yaml` 或 `index/people.yaml`。
- 后续优先读取 `projects/<project_id>/summary.md`。
- 只有定位到具体专题、人员、线程或证据后，才读取 `timeline.md`、`threads.md` 或原始 `*_邮件提取.docx`。
- 不要在每次提问时扫描全部 `emails/王慧`。
- 只有索引不存在、索引损坏、用户明确要求“重新建立索引”或“重新分析全部邮件”时，才扫描全部邮件。
- 不要修改原始邮件目录、正文 docx 或附件。
- 进度只能表述为“根据邮件估算”，不能表述为 ERP、MES、财务系统或真实生产系统准确进度。
