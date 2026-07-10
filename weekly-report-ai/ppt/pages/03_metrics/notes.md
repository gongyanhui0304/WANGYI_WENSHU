# 第3页维护说明：指标总览

## 文件职责

page.md：给 AI 或页面生成程序读取，描述这一页的生成规则、输入数据、动态内容、禁止事项和验收标准。

notes.md：给维护人员阅读，记录这一页的特殊注意事项、口径风险和后续待办。

## 维护注意事项

- 修改页面规则时，优先改 page.md。
- 修改程序读取字段时，同步检查 config.json。
- 替换视觉参考时，保留 example.png 作为本页唯一视觉样例。
- 页面出现任何数字时，必须能在 Metric Registry 或人工补充来源中找到依据。

## 本页特殊说明

每个指标均有 Metric ID、CSV/JSON 来源和 PPT 引用页；禁止硬编码数字。

## 后续待办

- 如本页新增指标，先注册到 metrics/metric_registry.json。
- 如本页新增参考图，按 reference_XX.png 命名。
- 如本页页码发生变化，只同步更新 config.json 的 page。

