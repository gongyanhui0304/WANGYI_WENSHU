# 📊 信息中心周报智能生成系统

基于 AI 的企业信息中心周报自动化生成系统。自动从 SmartBI 和 Redmine 抽取数据，结合历史周报风格和人工补充内容，通过 DeepSeek 大模型生成专业周报。

## 功能概览

- ✅ **数据源配置** — SQL Server (SmartBI) + PostgreSQL (Redmine) + DeepSeek API
- ✅ **基础映射维护** — 系统、模块、项目、负责人、团队及映射关系
- ✅ **SmartBI 指标抽取** — 报表使用情况、访问量、活跃度、低活跃/无人使用报表
- ✅ **Redmine 指标抽取** — 需求创建、完成、延期、积压、按多维度统计
- ✅ **历史周报 PDF 导入** — 上传 PDF 并提取文本作为 AI 生成参考
- ✅ **人工补充信息** — 重点项目进展、风险事项、下周计划、数据建设计划
- ✅ **AI 周报生成** — 调用 DeepSeek 生成管理层版和明细版两版周报
- ✅ **多格式导出** — 支持 Markdown 和 Word (docx) 导出

## 技术架构

| 层次 | 技术 |
|------|------|
| 前端 | Streamlit |
| 后端 API | FastAPI |
| ORM | SQLAlchemy |
| 本地存储 | SQLite |
| 外部数据库 | SQL Server (SmartBI) + PostgreSQL (Redmine) |
| AI 引擎 | DeepSeek (OpenAI-compatible API) |
| PDF 处理 | PyMuPDF / PyPDF |
| Word 导出 | python-docx |

## 快速开始

### 1. 环境要求

- Python >= 3.10
- pip

### 2. 安装依赖

```bash
cd weekly-report-ai
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制配置文件
copy .env.example .env     # Windows
cp .env.example .env        # Linux/Mac

# 编辑 .env 文件，填写真实的数据库和 API 配置
```

必须填写的配置项：
- `SMARTBI_SQLSERVER_*` — SmartBI 的 SQL Server 数据库连接信息
- `REDMINE_POSTGRES_*` — Redmine 的 PostgreSQL 数据库连接信息
- `DEEPSEEK_API_KEY` — DeepSeek API 密钥

### 4. 启动系统

**方式 A：Streamlit UI（推荐）**

```bash
cd weekly-report-ai
streamlit run app/ui/streamlit_app.py
```

默认打开 http://localhost:8501

**方式 B：FastAPI 后端**

```bash
cd weekly-report-ai
python -m app.main
```

API 文档: http://localhost:8000/docs

### 5. 使用流程

1. **配置数据源** — 编辑 `.env` 文件，在 UI 中测试连接
2. **维护映射关系** — 在「基础映射维护」页面添加系统、模块、项目、负责人等
3. **上传历史周报** — 在「历史周报管理」页面上传历史 PDF 周报
4. **填写补充信息** — 在「本周补充信息」页面填写项目进展和风险
5. **预览指标** — 在「指标抽取与预览」页面查看 SmartBI 和 Redmine 数据
6. **生成周报** — 在「周报生成」页面一键生成两版周报
7. **导出周报** — 在「周报预览与导出」页面导出 Markdown 或 Word

## 项目结构

```text
weekly-report-ai/
  app/
    __init__.py
    main.py                      # FastAPI 入口
    config.py                    # 配置管理
    db/
      __init__.py
      sqlite.py                  # SQLite 本地数据库
      sqlserver.py               # SQL Server 连接
      postgres.py                # PostgreSQL 连接
    models/
      __init__.py
      mapping.py                 # 基础映射模型
      report.py                  # 周报相关模型
      supplemental.py            # 人工补充模型
    services/
      __init__.py
      smartbi_service.py         # SmartBI 数据服务
      redmine_service.py         # Redmine 数据服务
      pdf_service.py             # PDF 处理服务
      ai_service.py              # AI 调用服务
      report_service.py          # 周报生成服务
      export_service.py          # 导出服务
    prompts/
      __init__.py
      weekly_report_prompt.py    # AI 提示词模板
    sql_templates/
      smartbi_report_usage_week.sql
      smartbi_report_usage_last_week.sql
      redmine_issues_week.sql
      redmine_issues_last_week.sql
      redmine_overdue_issues.sql
      redmine_backlog_issues.sql
    ui/
      __init__.py
      streamlit_app.py           # Streamlit UI
  data/
    uploads/                     # PDF 上传目录
    exports/                     # 导出文件目录
    sqlite/                      # SQLite 数据库文件
  .env.example
  requirements.txt
  README.md
```

## SQL 模板说明

SQL 模板文件位于 `app/sql_templates/`，包含通用查询示例。接入真实数据库时，请根据实际表结构修改：

- **SmartBI 报表查询**: `smartbi_report_usage_week.sql` / `smartbi_report_usage_last_week.sql`
  - 需要 `smartbi_report`（报表信息表）和 `smartbi_access_log`（访问日志表）
  - 查询报表访问人数、次数、最近访问时间等

- **Redmine 需求查询**: `redmine_issues_week.sql` / `redmine_issues_last_week.sql`
  - 基于 Redmine 标准表结构：`issues`, `issue_statuses`, `projects`, `users` 等
  - 如需按自定义字段统计，请自行扩展 SQL

- **延期需求**: `redmine_overdue_issues.sql`
- **积压需求**: `redmine_backlog_issues.sql`

## 数据缺口处理

系统设计为优雅降级：

- 外部数据库未配置时，不会报错，而是提示"暂无数据 / 需补充配置"
- AI API 不可用时，会展示错误原因
- 数据缺失部分会在生成的周报中标注"**暂无数据**"

## License

内部使用项目

## 项目目录说明

当前项目保留原有 `app/`、`data/`、`knowledge/`、`output/`、`prompts/`、`scripts/`、`tests/` 等目录，现有周报生成、Prompt、SQL、PPT 脚本和导出流程继续按原路径运行。

为支持后续“一页一页独立生成 PPT”，新增 `ppt/` 目录作为 PPT 页面级资产和配置入口：

```text
weekly-report-ai/
  ppt/
    template/
    pages/
      01_cover/
        page.md
        config.json
        example.png
        notes.md
      02_summary/
        page.md
        config.json
        example.png
        notes.md
      03_bi/
      04_system/
      05_redmine/
      06_project/
      07_risk/
      08_plan/
      09_appendix/
    style/
      font.json
      color.json
      layout.json
```

### 页面目录约定

`ppt/pages/` 下每一个子目录对应 PPT 的一页。以后新增页面时，只需要新增一个页面目录，并放入同样的四类文件，不需要修改现有 Prompt，也不需要影响其他页面。

- `page.md`：保存这一页的 AI 生成规则，例如页面名称、输入数据、输出内容、固定内容、禁止修改内容、允许 AI 生成内容、页面布局要求和字体要求。
- `config.json`：保存程序可读取的页面配置，例如页码、模板页、标题、是否可编辑、动态字段和固定元素。
- `example.png`：保存模板截图，供以后 AI 生成或人工维护时参考。
- `notes.md`：记录这一页的特殊说明，例如 Logo 不可修改、标题必须居中、日期自动生成等。

### 样式目录约定

`ppt/style/` 用于统一保存所有页面共享的样式配置：

- `font.json`：标题字体、正文字体、字号等字体规则。
- `color.json`：主色、辅助色、风险色、成功色、背景色、正文色等颜色规则。
- `layout.json`：页面尺寸、页边距、标题位置、正文位置、图表位置、页脚位置等布局规则。

### 后续规划

后续每个页面将采用独立生成流程：

```text
读取 page.md
↓
读取 config.json
↓
读取 example.png
↓
读取数据
↓
AI 生成这一页内容
↓
写入模板 PPT
```

每一页完全独立：封面、总览、BI、系统活跃、Redmine、项目、风险、计划、附录都可以单独调整规则、配置和示例图。这样新增或修改某一页时，不需要改全局 Prompt，不需要改其他页面，也不需要重写现有 PPT 生成流程。

## 指标可追溯规范

所有出现在 PPT 上的数字都必须具备全链路追溯能力，并统一引用唯一 Metric ID。标准链路如下：

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

运行时追溯产物写入：

```text
data/metrics/<run_id>/<metric_id>_<metric_name>/
  metric.json
  query.sql
  result.csv
  result.json
  summary.md
```

运行级汇总文件为：

```text
data/metrics/<run_id>/registry.json
```

新增指标必须先登记到 `metrics/metric_registry.json`，再通过 `app.metrics.MetricRegistry` 生成追溯产物。AI 分析和 PPT 页面禁止引用没有 Metric ID、没有 SQL、没有 CSV/JSON 来源的数据。禁止当前 PPT 生成流程引用硬编码值或旧脚本数据。

## 当前脚本入口

当前 PPT 生成以 `ppt/pages/` 页面契约为准：

- `scripts/validate_ppt_pages.py`：校验每一页的 `config.json`、`page.md`、`notes.md`、`example.png` 是否完整且一致。
- `scripts/generate_contract_ppt.py`：读取所有 `enabled=true` 且具备有效 `example.png` 的页面，按页面目录顺序生成 PPT。

生成 PPT 前必须先通过页面契约校验，禁止绕过 `ppt/pages/<page>/page.md` 和 `config.json` 直接输出页面。

