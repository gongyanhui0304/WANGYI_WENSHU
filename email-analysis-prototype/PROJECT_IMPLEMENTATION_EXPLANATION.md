# 邮件问数项目实现说明

本文基于当前仓库里的真实代码和文件整理，不把早期聊天里的想法、临时操作、或者已经废弃的本地静态邮件原型说成已实现功能。

当前项目目录：

```text
D:\重要资料勿删\桌面\codex\wangyi_wenshu\email-analysis-prototype
```

## 一句话结论

这个项目实现的是一套“服务器邮件索引 + MCP 工具 + Codex/其他智能体提问”的邮件问数原型。

用户在 Codex 里问“某个项目进展怎么样”“付款审批如何”“打开依据”等问题时，Codex 不直接读邮件文件，而是通过 `emailProjectAnalysis` MCP 工具访问服务器 API。服务器 API 先检查当前 token 有哪些邮箱权限，再查询服务器上的邮件索引；只有用户要求依据时，才按 `evidence_id` 或 `thread_id` 读取受控范围内的原始证据。

这个项目不是一个复杂的自研 Agent 系统。更准确地说：

```text
Codex 是智能体；
Skill 是给 Codex 的使用说明；
MCP 是工具协议和工具通道；
服务器 API 是权限和数据边界；
索引器把服务器原始邮件提前整理成可查询索引。
```

## 1. 项目实现了什么

当前仓库实现了这些东西：

1. 服务器端邮件 API

   文件：`mcp-server/server/mail_http_api.py`

   作用：提供邮箱问数接口，监听端口默认是 `8765`，由环境变量 `MAIL_API_PORT` 控制。它同时支持：

   - 远程 MCP 入口：`POST /mcp`
   - 兼容 HTTP 入口：`POST /list_mailboxes`
   - `POST /get_index_status`
   - `POST /query_summary`
   - `POST /search_threads`
   - `POST /get_evidence`
   - `POST /rebuild_index`

2. 服务器端邮件索引器

   文件：`mcp-server/server/mail_indexer.py`

   作用：扫描服务器上某个邮箱目录，提前生成结构化索引。它支持 `.eml`、文本、HTML、CSV、ICS，也支持从 `.docx` 邮件导出文件里提取正文和邮件头信息。PDF、Excel、图片、压缩包等文件不会被深度解析，主要作为附件记录。

3. 权限管理脚本

   文件：`mcp-server/server/manage_permissions.py`

   作用：生成或维护 token 与邮箱权限的映射。每个用户一个 token，token 对应允许访问的邮箱列表和权限列表。

4. MCP stdio bridge

   文件：`client/email_mcp_stdio.mjs`

   作用：给只支持本地 stdio MCP 的客户端使用。Codex 启动这个 `.mjs` 文件作为本地 MCP server，它再把工具调用转发到服务器 HTTP API。

5. Codex Skill / 用户说明文件

   文件：

   - `skills/email-project-analysis/SKILL.md`
   - `client/PER_USER_SKILL_TEMPLATE.md`
   - `client/LEADER_ALL_ACCESS_SKILL_TEMPLATE.md`

   作用：告诉 Codex 或其他智能体，遇到邮件、项目、客户、付款、风险、依据等问题时，要优先调用 `emailProjectAnalysis` MCP 工具，而不是读取本地邮件。

6. 配置模板和部署说明

   关键文件：

   - `mcp-server/config/server_hosted.env.example`
   - `mcp-server/config/permissions.example.json`
   - `mcp-server/config/remote_mcp.example.json`
   - `client/configs/codex-windows.config.toml.example`
   - `client/configs/codex-macos.config.toml.example`
   - `README.md`
   - `AGENTS.md`

## 2. 用户输入问题后，系统内部做了什么

以用户在 Codex 里问“王慧最近主要在处理什么？”为例，理想流程是：

1. Codex 看到这是邮件/项目/人员相关问题。

   依据：`skills/email-project-analysis/SKILL.md` 和用户交付的 Skill 文件会告诉 Codex：这类问题使用 `emailProjectAnalysis` MCP 工具。

2. Codex 先调用 `list_mailboxes`。

   作用：确认当前 token 能访问哪些邮箱。不能因为用户口头说“王慧邮箱”就默认有权限。

   服务器实现函数：`mail_http_api.py` 的 `list_mailboxes(user, payload)`。

3. 服务器 API 校验 token。

   服务器实现函数：

   - `_current_user(handler)`：从 `Authorization: Bearer <token>` 里取 token。
   - `_load_permissions()`：读取权限文件。
   - `_ensure_mailbox(user, mailbox_id)`：确认当前用户是否有权访问该邮箱。

4. Codex 确定邮箱后调用 `get_index_status(mailbox_id)`。

   作用：确认索引存在、是否损坏、是否比原始邮件旧。

   服务器实现函数：`get_index_status(user, payload)`。

5. Codex 调用 `query_summary(mailbox_id, query)`。

   作用：从该邮箱的 `summary.json` 或 `summary.md` 中拿摘要信息。

   服务器实现函数：`query_summary(user, payload)`。

6. 如果摘要不足，Codex 调用 `search_threads(mailbox_id, query, filters)`。

   作用：从 `threads.json` 中搜索相关邮件线程。

   服务器实现函数：`search_threads(user, payload)`。

7. 如果用户要求“打开依据”“看原始邮件”“完整线程”，Codex 调用 `get_evidence(mailbox_id, evidence_id 或 thread_id)`。

   作用：按证据 ID 或线程 ID 读取受控范围内的原始证据片段。

   服务器实现函数：`get_evidence(user, payload)`。

8. 服务器返回 JSON，Codex 把 JSON 组织成自然语言答案。

   重要结论应该说明依据来源，例如“服务器索引”“原始邮件证据”，并尽量引用 `evidence_id` 或 `thread_id`。

## 3. 邮件数据存在哪里，系统怎么查到对应邮件

当前代码不把邮件放在本地项目里。项目规则明确禁止使用本地 `emails/` 作为数据源。

服务器路径由环境变量控制，见 `mcp-server/config/server_hosted.env.example`：

```text
MAIL_RAW_ROOT=/path/to/raw-mails
MAIL_INDEX_ROOT=/path/to/mail-index
MAIL_LOG_ROOT=/path/to/mail-logs
MAIL_PERMISSIONS_FILE=/path/to/mail-index/permissions.json
MAIL_API_HOST=0.0.0.0
MAIL_API_PORT=8765
```

在实际部署讨论中使用过的服务器路径是：

```text
原始邮件目录：/data/ai_wenshu/data/emails
索引目录：/data/ai_wenshu/data/email_analysis_index
日志目录：/data/ai_wenshu/data/email_analysis_logs
API 端口：8765
```

这些路径不是写死在业务代码里的。`mail_http_api.py` 和 `mail_indexer.py` 都通过环境变量读取：

```python
RAW_ROOT = Path(required_env("MAIL_RAW_ROOT")).resolve()
INDEX_ROOT = Path(required_env("MAIL_INDEX_ROOT")).resolve()
LOG_ROOT = Path(required_env("MAIL_LOG_ROOT")).resolve()
```

系统查到对应邮件的方式不是“全盘搜索”，而是：

1. token 确定可访问邮箱。
2. 邮箱 ID 对应服务器目录：`MAIL_RAW_ROOT/<mailbox_id>`。
3. 索引器提前把该邮箱目录整理到：`MAIL_INDEX_ROOT/<mailbox_id>`。
4. 问答时先读索引文件。
5. 需要原文时，再通过 `evidence_map.json` 找到对应受控证据。

## 4. 为什么不用每次读取全部邮件

因为项目引入了服务器端索引。

索引器文件：`mcp-server/server/mail_indexer.py`

核心流程：

1. `build_mailbox(mailbox_id)`：为一个邮箱建立索引。
2. `iter_files(mailbox_root)`：遍历邮箱目录里的文件。
3. `collect_groups(mailbox_root)`：把同一个邮件导出目录下的正文、附件、压缩包等归为一组。
4. `group_to_record(...)`：把一组文件变成一条 evidence 记录，里面包含主题、发件人、收件人、日期、正文摘录、附件列表、关键字、线程 ID 等。
5. 写出索引文件。

每个邮箱会生成这些文件：

```text
$MAIL_INDEX_ROOT/<mailbox_id>/summary.json
$MAIL_INDEX_ROOT/<mailbox_id>/summary.md
$MAIL_INDEX_ROOT/<mailbox_id>/threads.json
$MAIL_INDEX_ROOT/<mailbox_id>/evidence_map.json
$MAIL_INDEX_ROOT/<mailbox_id>/index_status.json
```

这样用户问普通问题时，只需要读取 `summary.json` 或 `threads.json`，不需要每次重新扫原始邮件。

索引器支持的关键格式：

- `.docx`：通过 `read_docx_text(path)` 从 Word 文档里提取文本。
- `.eml`：通过 `decode_eml(raw)` 解析邮件主题、发件人、收件人、正文和附件名。
- `.ics`：通过 `ics_field(text, key)` 提取会议字段。
- `.pdf`、`.xlsx`、图片：当前主要作为附件记录，不深度解析正文。
- `.zip`、`.rar`：记录为附件或跳过，不自动解压。

这就是为什么它适合做“先索引、后问数”的原型。

## 5. 当前所谓“智能体”到底是什么

当前项目里，“智能体”不是项目自己写的一个复杂 Agent 程序。

准确区分如下：

1. Codex 本身

   Codex 是真正和用户对话、理解自然语言、决定调用哪个工具的智能体。

2. Skill

   `SKILL.md` 是给 Codex 的说明书。它告诉 Codex：邮件问题要用 `emailProjectAnalysis`；先调用 `list_mailboxes`；不要读取本地邮件；不要绕过 MCP；结论要带依据。Skill 本身不执行代码，也不保存权限。

3. MCP

   MCP 是工具协议。它让 Codex 能看到并调用 `list_mailboxes`、`query_summary`、`search_threads` 这类工具。

4. 项目自己实现的“Agent”

   当前仓库没有实现一个独立的复杂 Agent 决策系统。`business-app/` 只是临时 Web 调试入口，不是主入口。真正的问答智能来自 Codex 或其他接入 MCP 的智能体。

一句话：

```text
Codex 负责思考和表达；
Skill 负责告诉 Codex 怎么查；
MCP 负责把工具暴露给 Codex；
服务器 API 负责权限、索引和证据。
```

## 6. 智能体和服务器是怎么连接的

### 是否真的有服务器

当前仓库包含完整的服务器端代码：

- `mcp-server/server/mail_http_api.py`
- `mcp-server/server/mail_indexer.py`
- `mcp-server/server/manage_permissions.py`
- `mcp-server/deploy_server_bootstrap.sh`
- `mcp-server/config/server_hosted.env.example`

代码层面已经实现服务器 API。是否正在某台机器上运行，要看部署环境。部署后 API 默认监听：

```text
0.0.0.0:8765
```

### 使用 HTTP、MCP、stdio，还是直接读取本地文件

当前项目支持两种连接方式：

1. 远程 MCP，推荐方式

   请求链路：

   ```text
   Codex / 其他智能体
     -> remote MCP: POST http://<server-host>:8765/mcp
     -> mcp-server/server/mail_http_api.py
     -> 权限校验
     -> MAIL_INDEX_ROOT/<mailbox_id>
     -> 必要时读取 MAIL_RAW_ROOT/<mailbox_id> 的受控证据
     -> 返回 JSON
     -> Codex 组织答案
   ```

   配置模板：`mcp-server/config/remote_mcp.example.json`、`client/configs/remote-mcp.example.json`。

2. 本地 stdio bridge，兼容方式

   请求链路：

   ```text
   Codex
     -> 启动本地 client/email_mcp_stdio.mjs
     -> stdio MCP: tools/list、tools/call
     -> email_mcp_stdio.mjs 用 HTTP POST 调服务器
     -> http://<server-host>:8765/list_mailboxes 等旧接口
     -> 服务器返回 JSON
     -> bridge 包装成 MCP 响应
     -> Codex 组织答案
   ```

   文件：`client/email_mcp_stdio.mjs`。它读取 `MAIL_MCP_BASE_URL` 和 `MAIL_MCP_TOKEN`，不读取本地邮件。

### 请求从哪里发出，经过哪些文件

远程 MCP 模式：

```text
Codex 工具调用
  -> POST /mcp
  -> mail_http_api.py 的 MailApiHandler.do_POST()
  -> _current_user()
  -> _handle_mcp_payload()
  -> _handle_mcp_message()
  -> TOOLS[tool_name](user, arguments)
  -> list_mailboxes / query_summary / search_threads / get_evidence
  -> JSON-RPC result
```

stdio bridge 模式：

```text
Codex
  -> client/email_mcp_stdio.mjs
  -> handle(message)
  -> tools/list 或 tools/call
  -> callHttpTool(name, args)
  -> POST http://<server-host>:8765/<tool-name>
  -> mail_http_api.py
  -> JSON result
```

## 7. “mIS 文件”可能是哪一个

项目里没有发现叫 `mIS` 的文件。结合当前代码，最可能是把 `.mjs` 看成了 “mIS”。

### 最可能的文件：`client/email_mcp_stdio.mjs`

路径：

```text
email-analysis-prototype/client/email_mcp_stdio.mjs
```

作用：这是一个 Node.js 写的本地 stdio MCP bridge。Codex 如果不能直接连远程 MCP，就可以在本地启动这个 `.mjs` 文件。它向 Codex 暴露 MCP 工具，再把工具调用转发给服务器 HTTP API。

谁读取它：Codex 客户端或其他支持 stdio MCP 的智能体。配置示例见 `client/configs/codex-windows.config.toml.example`。

主要字段/变量：

```javascript
const BASE_URL = (process.env.MAIL_MCP_BASE_URL || "http://127.0.0.1:8765").replace(/\/$/, "");
const TOKEN = process.env.MAIL_MCP_TOKEN || "";
```

- `MAIL_MCP_BASE_URL`：服务器 API 地址，例如 `http://<server-host>:8765`。
- `MAIL_MCP_TOKEN`：当前用户的 token。

它暴露的工具：`list_mailboxes`、`get_index_status`、`query_summary`、`search_threads`、`get_evidence`、`rebuild_index`。

它如何连接 Codex 和服务器：

```text
Codex stdio MCP
  -> email_mcp_stdio.mjs
  -> HTTP POST 到服务器
  -> mail_http_api.py
```

### 其他相关配置文件

1. `mcp-server/config/remote_mcp.example.json`

   远程 MCP 示例配置：

   ```json
   {
     "name": "emailProjectAnalysis",
     "transport": "http",
     "url": "http://<mcp-server-host>:<port>/mcp",
     "headers": {
       "Authorization": "Bearer <user-specific-token>"
     }
   }
   ```

   字段含义：`name` 是工具名，`transport` 是连接方式，`url` 是远程 MCP endpoint，`headers.Authorization` 是用户 token。

2. `client/configs/codex-windows.config.toml.example`

   给不支持远程 MCP、但支持本地 stdio MCP 的 Codex 客户端使用。

   注意：Windows 路径在 TOML 里不要写成普通双引号里的单反斜杠，例如 `"D:\desktop\..."`，因为 `\d` 不是合法转义。推荐用正斜杠 `D:/desktop/...`，或者 TOML 单引号 `'D:\desktop\...'`。

3. `skills/email-project-analysis/SKILL.md`

   这是 Skill 文件，不是 MCP 启动配置。它告诉 Codex 要怎么使用工具，但它本身不会把 MCP 工具注册进 Codex。

## 8. AGENTS.md、SKILL.md、MCP、Agent 的区别

### AGENTS.md

路径：`email-analysis-prototype/AGENTS.md`、`email-analysis-prototype/client/AGENTS.md`。

作用：给在这个代码仓库里工作的 Codex 看的项目规则。比如不使用本地 `emails/`、不直接扫描服务器原始邮件、查询邮件只能通过 MCP、最终用户只拿个性化 Skill 文件。

### SKILL.md

路径：`email-analysis-prototype/skills/email-project-analysis/SKILL.md`。

作用：给 Codex 的能力说明书。它告诉 Codex 用户问邮件项目时，要用 `emailProjectAnalysis` MCP 工具，并规定查询顺序、证据规则、代词处理和回答格式。

### MCP

MCP 是工具协议。在这个项目里，MCP 把服务器 API 变成 Codex 可以调用的工具。远程 MCP 由 `mail_http_api.py` 的 `/mcp` endpoint 实现。本地 stdio MCP 由 `email_mcp_stdio.mjs` 实现。

### Agent

这里的 Agent 主要指 Codex、Claude、Cursor、Cline 等能调用工具的智能体。当前仓库没有实现一个复杂自研 Agent。`business-app/` 是临时 Web 调试入口，不是推荐主入口。

## 9. 最关键文件清单

1. `mcp-server/server/mail_http_api.py`：服务器 API 主文件，负责 token 校验、邮箱权限、MCP endpoint、HTTP endpoint、索引读取、证据读取和审计日志。
2. `mcp-server/server/mail_indexer.py`：邮件索引器，负责把服务器原始邮箱目录整理成 `summary.json`、`threads.json`、`evidence_map.json` 等索引文件。
3. `mcp-server/server/manage_permissions.py`：权限管理脚本，负责生成用户 token、绑定邮箱权限、列出或删除用户。
4. `client/email_mcp_stdio.mjs`：本地 stdio MCP bridge，给不支持远程 MCP 的客户端使用。
5. `skills/email-project-analysis/SKILL.md`：Codex Skill，定义邮件问数时的行为规则。
6. `client/PER_USER_SKILL_TEMPLATE.md`：普通用户交付模板，管理员填入该用户的 MCP URL 和 token 后交付。
7. `client/LEADER_ALL_ACCESS_SKILL_TEMPLATE.md`：领导/全权限用户交付模板，真正权限仍由服务器 token 控制。
8. `mcp-server/config/server_hosted.env.example`：服务器环境变量模板，定义原始邮件、索引、日志、权限文件、端口等路径。
9. `mcp-server/config/permissions.example.json`：权限文件示例，展示 token 如何映射到邮箱权限。
10. `mcp-server/config/remote_mcp.example.json`：远程 MCP 接入示例，适合支持 remote MCP 的智能体。
11. `config/data_sources.yaml`：数据源策略说明。当前文件里有字面量 `` `r`n `` 的格式瑕疵，更适合作为说明文件，不建议当作严格 YAML 解析依赖。
12. `.gitignore`：明确忽略本地邮件、项目产物、敏感 env 文件。

## 10. 真实问题演示：“星云项目现在怎么样？”

这个问题需要特别说明，因为早期原型里曾经有“星云项目 / P001 / 本地静态邮件”的设想，但当前项目已经改成服务器 MCP 数据源。

当前仓库里没有作为主数据源的：

```text
emails/P001
projects/P001
index/projects.yaml
index/people.yaml
```

所以当前系统不会按旧本地静态文件去读“星云项目”。真实流程应该是：

1. 用户问：`星云项目现在怎么样？`
2. Codex 根据 `skills/email-project-analysis/SKILL.md` 判断这是项目进展问题。
3. Codex 调用 `list_mailboxes()`，服务器根据 token 返回当前可访问邮箱。
4. 如果返回多个邮箱，且用户没说是哪个邮箱里的星云项目，Codex 应该先问用户要查哪个邮箱。
5. 确定邮箱后，Codex 调用 `get_index_status(mailbox_id)`，服务器读取 `$MAIL_INDEX_ROOT/<mailbox_id>/index_status.json`。
6. Codex 调用 `query_summary(mailbox_id, "星云项目现在怎么样？")`，服务器优先读取 `$MAIL_INDEX_ROOT/<mailbox_id>/summary.json`，没有时尝试 `summary.md` 或 `summary.txt`。
7. 如果摘要里没有足够信息，Codex 调用 `search_threads(mailbox_id, "星云")`，服务器读取 `$MAIL_INDEX_ROOT/<mailbox_id>/threads.json`。
8. 如果用户继续问“打开依据”，Codex 调用 `get_evidence(mailbox_id, evidence_id 或 thread_id)`，服务器读取 `$MAIL_INDEX_ROOT/<mailbox_id>/evidence_map.json`，并只在路径安全校验通过时读取 `$MAIL_RAW_ROOT/<mailbox_id>/...`。
9. 如果服务器索引里没有“星云项目”，正确回答是“当前服务器索引中没有找到星云项目的明确记录”，不能编造旧 P001 静态原型里的内容。

## 已实现与未实现边界

### 已实现

- 服务器端 HTTP API。
- 远程 MCP `/mcp` endpoint。
- 本地 stdio MCP bridge。
- token 到邮箱权限的校验。
- `list_mailboxes`、`get_index_status`、`query_summary`、`search_threads`、`get_evidence`、`rebuild_index` 工具。
- 文档型邮件索引器。
- `.docx` 邮件导出文本提取。
- `.eml` 解析。
- 附件记录。
- 证据 ID / 线程 ID 的受控读取。
- 审计日志 `access_audit.jsonl`。
- 用户 Skill 模板。

### 未实现或只做了轻量原型

- 没有真正的企业登录 SSO。
- 没有完整 Web 产品界面；`business-app/` 只是临时调试入口。
- 没有向量数据库。
- 没有 ERP、MES、PLM 接入。
- 没有自动邮件增量同步服务。
- PDF、Excel、图片内容没有深度解析，只记录附件信息。
- `rebuild_index` 在 API 中主要是排队记录，真正重建需要管理员脚本或外部调度执行。
- Skill 不能替代 MCP 权限控制。权限最终必须由服务器 API 校验。

## 30 秒介绍话术

这个项目是一个服务器邮件问数原型。我们把原始邮件留在服务器上，不让用户下载，也不让 Codex 直接扫文件。服务器先用索引器把每个邮箱整理成摘要、线程和证据索引。用户在 Codex 里自然语言提问时，Codex 通过 `emailProjectAnalysis` MCP 工具访问服务器，服务器根据 token 判断他能看哪些邮箱，再返回对应索引和证据。这样既能问项目进展、付款审批、风险和邮件依据，又能做到不同用户只看自己有权限的邮箱。

## 2 分钟介绍话术

这个项目解决的是“用 Codex 问服务器存量邮件”的问题。我们最初做过本地静态邮件原型，但现在主数据源已经改成服务器。原始邮件目录由服务器环境变量 `MAIL_RAW_ROOT` 指定，索引输出到 `MAIL_INDEX_ROOT`，日志写到 `MAIL_LOG_ROOT`。

系统分三层。第一层是 Codex，它负责理解用户问题和组织答案。第二层是 Skill 和 MCP，Skill 告诉 Codex 邮件问题要先查 `list_mailboxes`，再查索引，必要时取证据；MCP 把这些操作暴露成工具。第三层是服务器 API，代码在 `mcp-server/server/mail_http_api.py`，它负责 token 权限校验、索引查询和原始证据受控读取。

为了避免每次都扫大量邮件，服务器上有一个索引器 `mail_indexer.py`。它会按邮箱生成 `summary.json`、`threads.json`、`evidence_map.json`、`index_status.json`。普通问题优先读摘要和线程索引，只有用户要“打开依据”时，才按 `evidence_id` 或 `thread_id` 读取受控原文。

权限上，每个用户有自己的 token，token 对应允许访问的邮箱和权限。Skill 可以写连接地址和 token，但不决定权限。真正权限由服务器的 `MAIL_PERMISSIONS_FILE` 和 API 校验决定。

## 技术实现话术

技术上，服务器端是一个轻量 Python HTTP 服务，入口是 `mcp-server/server/mail_http_api.py`。服务启动时读取 `MAIL_RAW_ROOT`、`MAIL_INDEX_ROOT`、`MAIL_LOG_ROOT`、`MAIL_PERMISSIONS_FILE`，默认监听 `0.0.0.0:8765`。

它的 `MailApiHandler.do_POST()` 处理请求。如果路径是 `/mcp`，进入 `_handle_mcp_payload()`，支持 MCP JSON-RPC 的 `initialize`、`tools/list`、`tools/call`。如果路径是 `/list_mailboxes`、`/query_summary` 这类旧 HTTP endpoint，就直接调用 `TOOLS` 字典里的函数。

权限由 `_current_user()` 从 `Authorization: Bearer <token>` 取 token，再通过 `_load_permissions()` 读取权限文件。每个邮箱访问都会经过 `_ensure_mailbox()`。原始证据读取还会通过 `_safe_mailbox_path()` 和路径父目录检查，避免用户通过路径越权。

索引器 `mail_indexer.py` 负责把邮箱目录转成结构化索引。它用 `read_docx_text()` 解析 Word 邮件导出，用 `decode_eml()` 解析 EML，用 `collect_groups()` 把同目录正文和附件归组，用 `group_to_record()` 生成 evidence 记录，最后写出 `summary.json`、`threads.json`、`evidence_map.json`。

客户端如果支持远程 MCP，就直接连 `POST http://<server-host>:8765/mcp`。如果只支持 stdio MCP，就用 `client/email_mcp_stdio.mjs`，这个 Node 脚本作为本地 MCP server 启动，然后把工具调用转发到服务器 HTTP endpoint。

## 可能追问及回答

1. 问：邮件会不会被下载到用户电脑？

   答：按当前设计不会。用户通过 MCP 查服务器索引，原始邮件仍在服务器。只有请求证据时，服务器返回受控片段。

2. 问：为什么不直接让 Codex SSH 到服务器搜索邮件？

   答：那样权限边界不清楚，也不好审计。现在把权限放在服务器 API 和 token 上，Codex 只能调用受控工具。

3. 问：不同用户怎么隔离？

   答：`manage_permissions.py` 给每个用户生成 token，token 对应 `allowed_mailboxes`。服务器每次请求都校验 token。

4. 问：Skill 里写了 token，是不是 Skill 控制权限？

   答：不是。Skill 只是携带连接信息和使用说明。真正权限由服务器 `MAIL_PERMISSIONS_FILE` 和 `mail_http_api.py` 校验。

5. 问：MCP 是不是服务器？

   答：MCP 是协议和工具通道。服务器是 `mail_http_api.py` 提供的 HTTP 服务。这个服务同时实现了 `/mcp` 远程 MCP endpoint。

6. 问：`.mjs` 文件是干什么的？

   答：`email_mcp_stdio.mjs` 是本地 stdio MCP bridge。它让只支持本地 MCP 的 Codex 客户端也能调用服务器邮件 API。

7. 问：为什么浏览器打开 `http://服务器:8765` 显示 405 或 501？

   答：因为这个 API 主要接收 POST 请求，不是网页。浏览器 GET 报错不代表服务不可用。

8. 问：索引更新怎么做？

   答：索引器可以由管理员手动或定时运行。API 里的 `rebuild_index` 只做受控重建请求记录，实际调度要由服务器侧安排。

9. 问：PDF、Excel 能不能直接分析正文？

   答：当前索引器主要记录它们的文件名和路径作为附件，不做深度解析。后续可以扩展解析器。

10. 问：问“星云项目”为什么不能直接回答旧原型内容？

    答：当前主数据源已经不是本地 P001 静态邮件，而是服务器索引。服务器索引里有证据才回答，没有证据就说明找不到。

## 推荐代码阅读顺序

1. `README.md`：先看项目定位和用户交付方式。
2. `AGENTS.md`：看开发和使用边界，尤其是不要读本地邮件、不要绕过 MCP。
3. `skills/email-project-analysis/SKILL.md`：看 Codex 被要求如何处理邮件问题。
4. `mcp-server/server/mail_http_api.py`：看服务器 API、权限校验、MCP endpoint 和工具函数。
5. `mcp-server/server/mail_indexer.py`：看索引怎么生成，支持哪些文件类型。
6. `mcp-server/server/manage_permissions.py`：看 token 和邮箱权限怎么生成。
7. `client/email_mcp_stdio.mjs`：看本地 stdio MCP bridge 如何转发到服务器。
8. `mcp-server/config/server_hosted.env.example`：看服务器部署需要哪些环境变量。
9. `mcp-server/config/remote_mcp.example.json`：看远程 MCP 如何接入。
10. `client/PER_USER_SKILL_TEMPLATE.md`：看最终给普通用户的单文件 Skill 长什么样。
11. `client/LEADER_ALL_ACCESS_SKILL_TEMPLATE.md`：看给领导/全权限用户的 Skill 模板。

## 最后要牢记的边界

不要把它讲成“我们自己写了一个复杂智能体自动读所有邮件”。准确说法是：

```text
我们把邮件留在服务器，
用索引器提前整理，
用服务器 API 控制权限和证据读取，
用 MCP 把查询能力暴露给 Codex，
再用 Skill 告诉 Codex 按正确流程调用工具。
```

这套系统的核心价值是：不下载原始邮件、不每次全量扫描、权限可控、证据可追溯。
