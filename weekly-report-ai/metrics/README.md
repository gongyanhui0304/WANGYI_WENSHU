# 指标可追溯体系

本项目所有 PPT 指标必须实现全链路可追溯。任何出现在 PPT 上的数字，都必须引用唯一 Metric ID，并能定位到 SQL、CSV、JSON 和原始数据明细。

## 标准链路

```text
PostgreSQL / SQL Server
    ↓
SQL
    ↓
DataFrame
    ↓
CSV / JSON
    ↓
AI分析
    ↓
PPT
```

## 产物目录

运行时产物统一写入：

```text
data/metrics/<run_id>/<metric_id>_<metric_name>/
  metric.json
  query.sql
  result.csv
  result.json
  summary.md
```

运行级汇总文件：

```text
data/metrics/<run_id>/registry.json
```

## 强制规则

- 每个指标必须有唯一编号，例如 `M001`。
- AI 分析必须显式引用 Metric ID，例如 `AI应用需求82项（Metric=M004，来源=result.csv）`。
- 禁止 AI 引用没有来源的数据。
- 禁止 PPT 出现无法追溯的数字。
- 新增指标必须先注册到 `metric_registry.json`，再在生成流程中落盘追溯产物。
- 对暂时无法追溯的历史硬编码值，只能通过 `record_manual` 标记为 `manual_legacy`，并应尽快替换为 SQL-backed metric。

## 排查示例

领导询问：“AI应用为什么是82？”

应按以下路径定位：

```text
PPT 页面
↓
Metric=M004
↓
data/metrics/<run_id>/M004_AI应用需求数/query.sql
↓
data/metrics/<run_id>/M004_AI应用需求数/result.csv
↓
82 条 Issue 明细
↓
对应 Redmine Issue 编号
```
