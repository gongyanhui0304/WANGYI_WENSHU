# 第3页：指标总览

## 页面目标

生成可追溯核心指标总览页，作为后续页面的指标入口。

---

## 页面类型

metrics

---

## 输入数据

metrics/metric_registry.json、data/metrics/<run_id>/registry.json、各指标result.csv/result.json。

---

## 固定内容（禁止修改）

模板版式、标题区、页脚、字体体系、颜色体系。

不得重新设计模板结构。

不得删除公司模板固定元素。

不得新增与本页目标无关的装饰元素。

---

## 动态内容

Metric ID、指标名称、指标值、数据源、关联页面、追溯状态。

所有动态数字必须引用 Metric ID 或明确标注人工来源。

---

## 禁止事项

- 禁止使用没有来源的数字。
- 禁止 AI 编造项目、系统、人员、需求数量。
- 禁止改动模板固定布局和品牌视觉。
- 禁止把历史周报旧数据当成本期数据。

---

## 输出要求

最终输出第3页 PPT 内容。

页面内容必须服务于“指标总览”主题，并与 example.png 保持视觉一致。

---

## 验收标准

每个指标均有Metric ID、CSV/JSON来源和PPT引用页；禁止硬编码数字。

✓ 页面主题明确

✓ 数字可追溯

✓ 布局与模板一致

✓ 无额外无关元素
---

## 统一页面开发规范

本页必须遵循：[ppt/spec/page_standard.md](../../spec/page_standard.md)。

### 页面级标准声明

- DataSource：MetricRegistry；data/metrics/<run_id>/
- SQL：无直接业务 SQL；读取已注册 Metric 产物。
- Metric：M301 已注册指标数；M302 已生成 CSV 指标数；M303 已生成 JSON 指标数；M304 待接入指标数
- Debug目录：output/debug/page_03_metrics/
- Debug输出：metrics.json；ai_summary.md；metric_registry_snapshot.json；metric_status.csv；execution.log
- DrillDown：指标清单必须支持 PPT -> Metric Registry -> metric.json -> result.csv/result.json -> 来源 SQL 或来源说明。
- AI分析：AI 只能总结 Metric Registry 中已登记的指标状态。

### 追溯验收

任何出现在本页 PPT 上的数字，必须在 30 秒内定位到：PPT → Metric → SQL/人工来源 → CSV/JSON → 明细 → 原始记录。

如果本页声明无 SQL、无 CSV 或无需 DrillDown，必须在 Debug 日志中写明原因。

