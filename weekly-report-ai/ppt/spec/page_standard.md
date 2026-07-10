# PPT页面开发统一规范

## 适用范围

本规范适用于 `ppt/pages/` 下所有页面目录。

任何新增页面必须先引用本文件，再编写自己的业务规则。

每个页面仍然保留自己的业务目标、数据来源、布局和验收标准；本文件只定义统一的数据追溯、Metric、Debug、Drill Down 和 AI 分析规范。

---

## 1. 数据来源规范

所有页面必须在 `page.md` 和 `config.json` 中声明 `DataSource`。

允许的数据来源类型包括：

- Redmine
- SmartBI
- PostgreSQL
- SQLServer
- SystemDate
- API
- ManualInput
- MetricRegistry

禁止来源未知的数据进入 PPT。

如果页面使用人工补充内容，必须标注为 `ManualInput`，并在 Debug 日志中记录来源说明。

---

## 2. SQL规范

每个页面必须声明本页 SQL 位置。

示例：

- Redmine SQL：`knowledge/redmine/sql/`
- SmartBI SQL：`knowledge/smartbi/sql/`

如果本页无需 SQL，必须明确写明：

`SQL：无。`

禁止在页面生成阶段临时编造统计 SQL。

优先复用 `knowledge/` 目录中已有 SQL。

---

## 3. Metric规范

所有页面必须声明并生成 Metric。

Metric 编号必须全项目唯一。

推荐按页面分段：

- 第1页：M101-M199
- 第2页：M201-M299
- 第3页：M301-M399
- 第4页：M401-M499
- 第5页：M501-M599
- 第6页：M601-M699
- 第7页：M701-M799
- 第8页：M801-M899
- 第9页：M901-M999
- 第10页：M1001-M1099

任何新增 Metric 必须注册到 `metrics/metric_registry.json`。

所有 Metric 至少保存：

- 指标编号
- 指标名称
- 统计口径
- 数据源
- SQL 或无 SQL 说明
- 执行时间
- DataFrame 输出说明
- CSV 输出说明
- JSON 输出说明
- AI 分析引用
- PPT 引用页面

---

## 4. Debug规范

所有页面必须生成 Debug 目录：

`output/debug/page_xx/`

至少输出：

- `metrics.json`
- `ai_summary.md`
- `execution.log`
- 本页使用的所有 SQL 文件副本
- 本页产生的 CSV 文件
- 本页产生的 JSON 文件

如果页面无需 SQL 或无需 CSV，必须在 `execution.log` 中明确说明原因。

---

## 5. Drill Down规范

所有图表必须支持 Drill Down。

统一链路：

PPT图表
↓
Metric
↓
SQL
↓
CSV
↓
明细
↓
数据库记录

如果本页没有图表，必须明确说明：

`无需 DrillDown。`

---

## 6. AI分析规范

AI 不得引用没有来源的数据。

AI 分析必须引用 Metric ID。

禁止 AI 编造数字、系统、项目、人员、需求、报表和趋势结论。

当数据缺失时，只能输出：

`暂无数据，需补充配置。`

或：

`待接入 Metric。`

---

## 7. 验收规范

任何出现在 PPT 上的数字，必须在 30 秒内定位到：

PPT
↓
Metric
↓
SQL 或人工来源说明
↓
CSV / JSON
↓
明细记录
↓
数据库原始记录

如果无法完成追溯，该数字不得进入 PPT。
