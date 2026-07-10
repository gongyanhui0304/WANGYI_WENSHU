# 第4页：BI低活跃报表治理（Top20）

## 页面目标

本页用于识别 SmartBI 中长期低活跃、无人访问或价值较低的报表。

面向管理层展示：

- 哪些系统存在大量低活跃报表
- 哪些报表长期无人使用
- 哪些报表建议下线、优化或推广
- BI资源投入是否合理

重点体现：

“报表建了，但没人使用。”

---

## 页面类型

BI低活跃报表治理 / low_activity_governance

---

## 数据来源

SmartBI SQL Server 数据库。

SQL 统一从以下目录读取：

knowledge/smartbi/sql/

优先复用项目已有 SQL：

- 009_报表使用Woet20-SAP系统.sql
- 011_报表使用Top20-BI系统.sql
- 014_周维度-报表使用Woet20-SAP系统.sql
- 016_周维度-报表使用Top20-BI系统.sql
- 020_周维度-报表使用Top20-BI系统-备份.sql

禁止重新编写统计逻辑。

优先沿用已有 SQL。

---

## 统计周期

必须支持：

1. 周统计
2. 月统计

默认展示：本周。

支持切换：周 / 月。

周统计和月统计必须保持统计口径一致。

---

## 低活跃判定规则

默认规则：

- 近30天访问次数 <= 5 次
- 或近7天访问次数 = 0

如果 SQL 已有低活跃定义，优先采用 SQL 定义。

---

## 页面布局

### 顶部：四个 KPI

1. 报表总数
2. 低活跃报表数
3. 近7天零访问报表数
4. 低活跃占比

每个 KPI 展示：

- 当前值
- 较上周变化
- 上升/下降箭头

### 左侧：各系统低活跃报表数量

统计系统：

- SAP
- BI
- PLM
- MOM
- OA
- AI应用
- 其它

展示方式：横向柱状图，按数量降序。

### 中间：低活跃报表 Top20

字段：

| 字段 | 说明 |
| --- | --- |
| 排名 | 按访问次数升序 |
| 所属系统 | SAP / BI / PLM / MOM / OA / AI应用 / 其它 |
| 报表编码 | 来源 SQL |
| 报表名称 | 来源 SQL |
| 近7天访问次数 | 来源周统计 |
| 近30天访问次数 | 来源月/滚动统计 |
| 最近访问时间 | 来源访问日志 |
| 建议治理方式 | 由规则生成 |

建议治理方式仅允许：

- 建议下线
- 建议优化
- 建议合并
- 建议推广

### 右侧：治理建议分布

统计：

- 建议下线
- 建议优化
- 建议合并
- 建议推广

展示方式：环形图。

### 右侧下方：报表明细穿透示例

点击报表名称后，应能查看：

- 报表编码
- 所属系统
- 维护部门
- 负责人
- 近7天访问
- 近30天访问
- 最近访问时间
- 建议治理方式

---

## AI分析

控制在 100 字以内。

必须引用真实统计结果。

示例表达：

本周共识别低活跃报表58张，占全部报表12.6%。SAP系统低活跃报表最多，共18张，占31%。其中22张建议下线，建议优先治理连续四周无人访问报表。

禁止固定模板。

禁止 AI 编造访问次数。

---

## 穿透查询（必须实现）

所有报表必须支持 Drill Down。

点击：报表名称

↓

查看：报表详情

↓

查看：访问日志

↓

查看：访问用户

↓

查看：访问时间

↓

查看：来源 SQL

↓

查看：报表维护人

↓

查看：所属部门

---

## 可追溯要求

本页所有指标必须生成追溯文件。

目录：

output/debug/page_04_bi_low_activity/

输出：

- metrics.json
- ai_summary.md
- week_low_activity.sql
- month_low_activity.sql
- week_low_activity_top20.csv
- month_low_activity_top20.csv
- system_summary.csv
- report_detail.csv

---

## 指标说明

| Metric | 指标名称 | 说明 |
| --- | --- | --- |
| M401 | 报表总数 | 本页统计范围内的 SmartBI 报表总数 |
| M402 | 低活跃报表数量 | 满足低活跃判定规则的报表数量 |
| M403 | 近7天零访问数量 | 近7天访问次数为 0 的报表数量 |
| M404 | 低活跃占比 | 低活跃报表数量 / 报表总数 |
| M405 | 系统低活跃统计 | 按系统聚合的低活跃报表数量 |
| M406 | 低活跃Top20 | 低活跃报表 Top20 明细 |

所有 Metric 必须能够追溯：

PPT → Metric → SQL → CSV → 访问日志 → 原始数据库

---

## 禁止事项

- 禁止统计访问量 Top20。
- 禁止展示高活跃报表。
- 禁止 AI 编造访问次数。
- 禁止没有 SQL 来源的数据进入 PPT。
- 禁止把本页做成 BI 成果展示页。

所有分析必须围绕“低活跃治理”展开。

本页目标不是展示 BI 成果，而是帮助管理层发现资源浪费和优化空间。

---

## 输出要求

最终输出第4页 PPT 内容。

页面必须严格围绕“BI低活跃报表治理（Top20）”展开。

所有 KPI、Top20、治理建议分布和 Drill Down 字段必须来自 SQL、CSV 或 Metric Registry。

不得输出高活跃报表展示页。
---

## 验收标准

✓ 四个 KPI 均有 Metric ID

✓ 低活跃 Top20 来源于 CSV 明细

✓ 系统低活跃统计来源于 system_summary.csv

✓ AI 分析引用 M401-M406 的真实结果

✓ Drill Down 能定位到报表、访问日志、访问用户、访问时间和来源 SQL

✓ 所有输出文件写入 output/debug/page_04_bi_low_activity/

✓ 页面不展示高活跃报表
---

## 统一页面开发规范

本页必须遵循：[ppt/spec/page_standard.md](../../spec/page_standard.md)。

### 页面级标准声明

- DataSource：SmartBI SQLServer；knowledge/smartbi/sql/；MetricRegistry
- SQL：knowledge/smartbi/sql/
- Metric：M401 报表总数；M402 低活跃报表数量；M403 近7天零访问数量；M404 低活跃占比；M405 系统低活跃统计；M406 低活跃Top20
- Debug目录：output/debug/page_04_bi_low_activity/
- Debug输出：metrics.json；ai_summary.md；week_low_activity.sql；month_low_activity.sql；week_low_activity_top20.csv；month_low_activity_top20.csv；system_summary.csv；report_detail.csv；execution.log
- DrillDown：所有报表名称、图表和 KPI 必须支持 PPT -> Metric -> SQL -> CSV -> 访问日志 -> SmartBI 原始记录。
- AI分析：AI 分析必须引用 M401-M406。

### 追溯验收

任何出现在本页 PPT 上的数字，必须在 30 秒内定位到：PPT → Metric → SQL/人工来源 → CSV/JSON → 明细 → 原始记录。

如果本页声明无 SQL、无 CSV 或无需 DrillDown，必须在 Debug 日志中写明原因。

