# 第2页：总览

## 页面目标

生成本期周报总览页，概括信息中心本周整体运行态势。

---

## 页面类型

summary

---

## 输入数据

Metric Registry、核心指标CSV/JSON、人工补充说明、ppt/pages/02_summary/example.png。

---

## 固定内容（禁止修改）

模板版式、标题区、页脚、主色、卡片布局。

不得重新设计模板结构。

不得删除公司模板固定元素。

不得新增与本页目标无关的装饰元素。

---

## 动态内容

核心结论、关键指标、趋势判断、重点风险提示。

所有动态数字必须引用 Metric ID 或明确标注人工来源。

---

## 禁止事项

- 禁止使用没有来源的数字。
- 禁止 AI 编造项目、系统、人员、需求数量。
- 禁止改动模板固定布局和品牌视觉。
- 禁止把历史周报旧数据当成本期数据。

---

## 输出要求

最终输出第2页 PPT 内容。

页面内容必须服务于“总览”主题，并与 example.png 保持视觉一致。

---

## 验收标准

所有数字必须绑定Metric ID，结论必须有数据来源，不能出现无法追溯的指标。

✓ 页面主题明确

✓ 数字可追溯

✓ 布局与模板一致

✓ 无额外无关元素
---

## 统一页面开发规范

本页必须遵循：[ppt/spec/page_standard.md](../../spec/page_standard.md)。

### 页面级标准声明

- DataSource：Redmine PostgreSQL；MetricRegistry；ManualInput
- SQL：knowledge/redmine/sql/
- Metric：M201 总需求数；M202 本周新增需求；M203 本周完成需求；M204 风险提示数
- Debug目录：output/debug/page_02_summary/
- Debug输出：metrics.json；ai_summary.md；redmine_summary.sql；redmine_summary.csv；redmine_summary.json；execution.log
- DrillDown：总览 KPI 和趋势结论必须支持 PPT -> Metric -> SQL -> CSV/JSON -> Issue 明细 -> Redmine 原始记录。
- AI分析：AI 分析必须引用 M201-M204 或明确人工来源。

### 追溯验收

任何出现在本页 PPT 上的数字，必须在 30 秒内定位到：PPT → Metric → SQL/人工来源 → CSV/JSON → 明细 → 原始记录。

如果本页声明无 SQL、无 CSV 或无需 DrillDown，必须在 Debug 日志中写明原因。


