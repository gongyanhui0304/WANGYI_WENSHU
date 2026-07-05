# 邮件问数项目部署交接说明

本文档用于交给部署同事。部署同事拿到项目包后，在最终服务器上完成部署、权限分配、大邮件生产索引接入和用户交付文件生成。部署完成后，只返回给业务方每个用户对应的交付文件。

## 一句话结论

本项目已确定面向大邮件库。部署时默认按“大邮件生产模式”处理：原始邮件留在服务器，MCP 服务只读服务器索引，索引层必须使用增量、分片、可恢复任务，不使用高频全量扫描 cron 作为生产索引方式。

本地只能准备代码包、部署脚本、Skill 模板、桥接文件模板、部署说明和用户交付文件生成器。

真正可用的邮箱索引、用户 token、权限文件、生产索引任务和 MCP 服务，必须在最终服务器上完成。

原因是：

- token 必须写入服务器端权限文件，服务器才能校验；
- 索引必须读取服务器上的真实邮件目录；
- 生产索引必须靠服务器上的增量任务、分片状态和断点恢复运行；
- MCP 服务必须运行在用户智能体能访问到的稳定地址上。

## 最终交付给用户什么

每个用户生成一个专属交付目录，但要按角色使用：

```text
dist/user-delivery/<user-id>/
├── user/
│   ├── email_mcp_stdio.mjs
│   └── SKILL.md
└── it/
    ├── IT_INSTALL.md
    ├── mcp-config.codex.toml
    └── mcp-config.generic.json
```

- `user/` 是该用户专属文件，包含该用户 token 对应的桥接文件和 Skill。
- `it/` 是部署人员或平台管理员使用的安装说明和 MCP 配置片段。
- 最终用户不应该靠“提醒智能体读取 mjs 和 Skill”来使用；部署人员必须先在目标智能体平台注册 `emailProjectAnalysis` MCP。
- 文件放进工作区不会自动加载 MCP。只要用户还需要手动提醒，就说明平台侧 MCP 没注册成功，或当前会话没有加载该工具。
- 用户不接触服务器路径、原始邮件、索引目录、权限文件或部署脚本。

如果用户权限不同，就生成不同的 `email_mcp_stdio.mjs`。`SKILL.md` 可以按同一个模板生成，但为了交付简单，也按用户一起生成。

## 本地能做什么

本地可以完成：

- 整理项目源码；
- 生成服务器部署压缩包；
- 准备 Skill 模板；
- 准备桥接文件模板；
- 准备部署说明；
- 准备用户交付文件生成脚本。

本地不能最终完成：

- 读取最终服务器上的真实邮件；
- 建立最终可用索引；
- 生成最终有效 token；
- 验证某个用户实际能访问哪些邮箱；
- 配置生产增量索引任务；
- 启动长期可访问的 MCP 服务。

## 服务器上必须完成什么

部署同事需要在最终服务器上完成：

1. 放置或挂载原始邮件目录。
2. 创建索引目录。
3. 创建日志目录。
4. 解压项目包。
5. 配置环境变量。
6. 启动 MCP HTTP 服务。
7. 为不同用户生成 token 和邮箱权限。
8. 按 `docs/large-mail-production-indexing.md` 接入大邮件生产索引任务。
9. 完成初始回填、增量调度、失败重试和索引状态监控。
10. 为每个用户生成专属交付目录，并确认目标智能体平台已注册 `emailProjectAnalysis` MCP。

## 最短执行清单

部署同事按这条主线执行：

1. 解压 `dist/email-analysis-prototype-server-hosted-stable.zip` 到服务器项目目录。
2. 设置 `MAIL_RAW_ROOT`、`MAIL_INDEX_ROOT`、`MAIL_LOG_ROOT`、`MAIL_PERMISSIONS_FILE`、`SERVER_APP_ROOT`。
3. 运行 `./server-hosted-deploy.sh` 启动 MCP HTTP 服务。
4. 用 `manage_permissions.py --file "$MAIL_PERMISSIONS_FILE" add-user ...` 为每个用户生成 token。
5. 用内置生产索引器按 `docs/large-mail-production-indexing.md` 接入 changed-list、`indexed_files` 状态表、mailbox/year_month 分片、断点恢复任务和 rollup 索引发布。
6. 完成生产索引初始回填和日常增量调度后，验证 `/mcp` 的 `tools/list` 和 `tools/call`。
7. 用 `client/generate_user_delivery.mjs` 生成每个用户的专属交付目录。
8. 用用户 token 调 `/mcp` 的 `tools/list` 或让用户问“我能访问哪些邮箱？”验证权限。

## 推荐服务器目录

可以按以下目录部署，也可以由管理员按内网规范调整：

```text
/opt/email-analysis/email-analysis-prototype        # 项目代码
/opt/email-analysis/mcp_email_server               # MCP 运行时目录
/data/mail-analysis/raw-mails                       # 原始邮件目录，只读
/data/mail-analysis/index                           # 生产索引目录
/data/mail-analysis/logs                            # 日志目录
```

旧测试环境曾使用：

```text
/data/ai_wenshu/data/emails
/data/ai_wenshu/data/email_analysis_index
/data/ai_wenshu/data/email_analysis_logs
```

最终部署时不要依赖旧路径，按实际服务器环境配置。

## 服务器需要提供的信息

部署前需要确认：

- 原始邮件目录，例如 `/data/mail-analysis/raw-mails`。
- 索引目录，例如 `/data/mail-analysis/index`。
- 日志目录，例如 `/data/mail-analysis/logs`。
- MCP 服务监听地址和端口，例如 `0.0.0.0:8765`。
- 用户智能体可访问的 MCP 地址，例如 `https://mail-analysis.company.com/mcp`。
- 需要授权的用户列表。
- 每个用户能访问的邮箱列表。
- 是否允许某些用户触发重建索引。
- 生产索引任务运行方式：systemd timer、任务队列或调度平台。
- 是否需要通过 Nginx、网关或堡垒机反向代理。

## 部署包

本地交付部署包：

```text
dist/email-analysis-prototype-server-hosted-stable.zip
```

部署同事在服务器上解压：

```bash
mkdir -p /opt/email-analysis
cd /opt/email-analysis
unzip -q email-analysis-prototype-server-hosted-stable.zip
cd email-analysis-prototype
```

## 启动 MCP 服务

在服务器上按实际路径设置环境变量：

```bash
cd /opt/email-analysis/email-analysis-prototype

export MAIL_RAW_ROOT=/data/mail-analysis/raw-mails
export MAIL_INDEX_ROOT=/data/mail-analysis/index
export MAIL_LOG_ROOT=/data/mail-analysis/logs
export MAIL_PERMISSIONS_FILE=/data/mail-analysis/index/permissions.json
export SERVER_APP_ROOT=/opt/email-analysis/mcp_email_server
export MAIL_API_HOST=0.0.0.0
export MAIL_API_PORT=8765
```

启动部署脚本：

```bash
chmod +x server-hosted-deploy.sh
./server-hosted-deploy.sh
```

这个脚本会把运行时文件复制到 `$SERVER_APP_ROOT`，初始化权限文件，创建一个管理员 token，并启动 MCP HTTP 服务。管理员 token 会写到 `$MAIL_LOG_ROOT/admin_token_last_created.json`，应按敏感文件保护；如果不需要全权限管理员 token，部署后应删除或轮换。

服务启动后，MCP HTTP 服务会监听：

```text
http://<server-ip>:8765/mcp
```

生产环境建议用 HTTPS 反向代理，例如：

```text
https://mail-analysis.company.com/mcp
```

## 权限和 token

权限由服务器端 `permissions.json` 控制，不由 Skill 控制。

生成用户 token 示例：

```bash
cd "$SERVER_APP_ROOT"
python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id zhangsan \
  --display-name "张三" \
  --mailboxes 王慧 sherman
```

生成全权限用户示例：

```bash
cd "$SERVER_APP_ROOT"
python3 manage_permissions.py \
  --file "$MAIL_PERMISSIONS_FILE" \
  add-user \
  --user-id email_all \
  --display-name "Email All" \
  --mailboxes 王慧 sherman jackdong \
  --allow-rebuild
```

列出用户但不显示 token：

```bash
python3 manage_permissions.py --file "$MAIL_PERMISSIONS_FILE" list
```

脚本返回的 token 需要保存好。token 默认不会自动过期，除非后续执行 `add-user --rotate-token` 或 `remove-user`。

## 大邮件生产索引

生产索引必须按 `docs/large-mail-production-indexing.md` 执行。核心要求：

- 建立 `indexed_files` 状态表；
- 只处理新增、变化、删除的文件；
- 按 `mailbox_id/year_month` 写分片；
- 任务有 checkpoint、lease、失败重试和 dead-letter；
- rollup 摘要和线程索引发布给 MCP 读取；
- `query_summary`、`search_threads`、`get_evidence` 不依赖扫描原始邮件目录。

`mcp-server/server/mail_indexer.py` 已实现单机生产索引骨架，可直接用于服务器小范围真实邮箱验证：`--changed-list` 日常增量、`indexed_files.sqlite` 状态表、mailbox/year_month 分片、`index_jobs` checkpoint、dead-letter、rollup/thread index。不要把它作为全量邮件库的周期性扫描任务；日常生产必须由同步日志、文件事件或上游清单提供 changed-list。

## 生成用户交付文件

部署同事在服务器上为每个用户生成交付文件。这个脚本在项目源码目录运行，不是在 `$SERVER_APP_ROOT` 运行。

示例：

```bash
cd /opt/email-analysis/email-analysis-prototype
node client/generate_user_delivery.mjs \
  --user-id email_all \
  --mcp-url https://mail-analysis.company.com/mcp \
  --token '<该用户自己的token>'
```

生成位置：

```text
dist/user-delivery/email_all/
├── user/
│   ├── email_mcp_stdio.mjs
│   └── SKILL.md
└── it/
    ├── IT_INSTALL.md
    ├── mcp-config.codex.toml
    └── mcp-config.generic.json
```

部署人员或平台管理员按 `it/IT_INSTALL.md` 把 `emailProjectAnalysis` 注册到目标智能体平台。注册成功后，业务用户正常提问即可，不需要每次提醒智能体读取桥接文件或 Skill。

## 用户侧怎么使用

部署人员完成平台侧 MCP 注册后，用户直接在自己的智能体里提问，例如：

```text
我能访问哪些邮箱？
StreamView 这个项目现在进展如何？
最近一个月有哪些项目以及对应负责人是谁？
```

如果用户的智能体仍然说没有 `emailProjectAnalysis` 工具，或需要用户手动提醒它读取 `email_mcp_stdio.mjs` / `SKILL.md`，说明平台侧 MCP 没接好，不是服务器索引问题。

## 日志和审计

MCP 查询审计日志：

```text
<MAIL_LOG_ROOT>/access_audit.jsonl
```

可以查看哪个 user_id 在什么时间调用了哪个工具、查询了哪个 mailbox、查询文本是什么、是否成功。

服务日志：

```text
<MAIL_LOG_ROOT>/mail_http_api.out
```

生产索引日志按 `docs/large-mail-production-indexing.md` 接入，至少应包含任务状态、失败文件、队列长度、index lag 和分片发布记录。

## 安全原则

- 原始邮件只留在服务器。
- 用户不能直接访问原始邮件路径。
- 用户只能通过 MCP 工具查询授权邮箱。
- 一个用户一个 token。
- 不共享 token。
- 不把管理员 token 发给普通用户。
- token 写入专属桥接文件后，该文件视为敏感文件。
- 权限变更在服务器端 `permissions.json` 完成。
- 离职或权限变更时，删除或轮换对应 token。
- 禁止给智能体配置任意文件读取、shell、SSH 或通用服务器路径访问工具。

## 部署同事最终需要返回什么

部署完成后，返回给业务方：

```text
用户A/
├── email_mcp_stdio.mjs
└── SKILL.md

用户B/
├── email_mcp_stdio.mjs
└── SKILL.md
```

同时告知 MCP 服务地址、已配置邮箱、每个用户权限、生产索引任务状态、日志目录、如何新增用户、如何回收权限。

不要返回原始邮件、`permissions.json` 全量文件、管理员 token、服务器私钥或部署环境变量中的敏感信息。

## 常见问题

### 我能不能现在就把桥接文件和 Skill 给用户？

可以给模板，但不能保证可用。真正可用的桥接文件必须包含最终服务器 MCP 地址和有效 token。

### token 能不能本地生成？

不建议。token 必须写入服务器端权限文件才有效。最好由服务器上的 `manage_permissions.py` 生成。

### Skill 能不能控制权限？

不能。Skill 只是提示智能体怎么调用工具。最终权限必须由 MCP Server 校验。

### 为什么不能只给用户一个 Skill？

因为 Skill 不能自己建立 MCP 连接。用户的智能体仍然需要一个 MCP 工具入口。当前方案用 `email_mcp_stdio.mjs` 作为本地桥接入口。

### 生产索引能不能靠 cron 反复跑全量扫描？

不能。本项目已确定是大邮件库，生产索引必须走 changed-list 增量、分片、可恢复任务。内置脚本默认会拒绝无模式启动；只有设置 `ALLOW_BACKFILL_SCAN=1` 时才允许受控初始回填、对账或修复。

### 以后如果 MCP 平台支持远程 MCP，可以不用 mjs 吗？

可以。如果智能体平台原生支持远程 MCP URL 和 token，就可以直接配置远程 MCP，不再需要本地 stdio 桥接文件。

## 交付检查清单

- [ ] 原始邮件目录存在且服务用户只读。
- [ ] 索引目录可写。
- [ ] 日志目录可写。
- [ ] MCP 服务可访问。
- [ ] `/mcp` 接口支持 `tools/list` 和 `tools/call`。
- [ ] `manage_permissions.py --file "$MAIL_PERMISSIONS_FILE" add-user` 命令已在服务器上验证。
- [ ] 每个用户都有独立 token。
- [ ] 普通用户不能访问未授权邮箱。
- [ ] 全权限用户仅给指定领导或管理员。
- [ ] 已按 `docs/large-mail-production-indexing.md` 接入生产增量索引。
- [ ] `indexed_files` 状态表、分片目录、rollup、checkpoint、失败重试和 index lag 监控已验证。
- [ ] 审计日志能记录查询。
- [ ] 每个用户已生成独立交付包，并已在目标智能体平台配置 `emailProjectAnalysis` MCP。