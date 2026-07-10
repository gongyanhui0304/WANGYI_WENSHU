# 第4页维护说明：BI低活跃报表治理

## 文件职责

page.md：定义第4页“BI低活跃报表治理（Top20）”的生成规则、统计口径、布局、追溯要求和禁止事项。

notes.md：记录本页维护注意事项、SQL复用要求、Metric要求和后续实现待办。

## 核心定位

本页不是展示 BI 成果，也不是访问量 Top20 页面。

本页只围绕一个问题展开：报表建了，但没人使用。

## SQL复用要求

SQL 统一从 knowledge/smartbi/sql/ 读取。

优先复用：

- 009_报表使用Woet20-SAP系统.sql
- 011_报表使用Top20-BI系统.sql
- 014_周维度-报表使用Woet20-SAP系统.sql
- 016_周维度-报表使用Top20-BI系统.sql
- 020_周维度-报表使用Top20-BI系统-备份.sql

注意：当前 020 文件实际名称带 “-备份”，配置中按实际文件名引用。

## Metric要求

本页固定使用 M401-M406。

新增数字前必须先判断是否能归入 M401-M406；不能归入时，先注册新 Metric，再进入 PPT。

## 调试输出

运行生成流程时必须写入：

output/debug/page_04_bi_low_activity/

该目录下的 CSV 是本页 Drill Down 的依据。

## 维护注意事项

- 不要把高活跃 Top20 放到本页。
- AI 分析必须控制在 100 字以内。
- AI 分析必须引用真实统计结果。
- Top20 必须按访问次数升序，而不是降序。
- 治理建议只允许：建议下线、建议优化、建议合并、建议推广。
- 所有报表行必须能追溯到 SQL 和访问日志。

## 本页特殊说明

本页固定使用 M401-M406。新增数字前必须先判断是否能归入 M401-M406；不能归入时，先注册新 Metric，再进入 PPT。

## 后续待办

- 实现 week_low_activity.sql 和 month_low_activity.sql 的程序化落盘。
- 生成 week_low_activity_top20.csv、month_low_activity_top20.csv、system_summary.csv、report_detail.csv。
- 将 Drill Down 交互与 report_detail.csv 关联。

