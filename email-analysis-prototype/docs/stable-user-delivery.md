# 稳定入口与用户交付方案

目标：这次重新部署后，给不同智能体用户发出去的桥接文件和 Skill 文件尽量长期不变。以后更换服务器、迁移磁盘或调整服务位置时，不要求用户重新替换本地文件。

## 核心原则

1. 用户文件只写稳定入口，不写临时服务器 IP。
2. 用户权限只由服务器端 token 决定。
3. 每个用户一份自己的 bridge 文件，里面可内置该用户 token。
4. 所有用户可以共用同一个 Skill 说明，也可以拿到管理员预填好的单文件 Skill。
5. 后续服务器迁移时，保持稳定入口不变，通过 DNS、内网 VIP、网关或反向代理把流量转到新服务器。

## 推荐交付物

给每个用户：

- `email_mcp_stdio.mjs`：用户专属桥接文件，内置稳定 MCP URL 和该用户 token。
- `SKILL.md`：邮件问数使用说明，不包含服务器路径，不包含默认邮箱。

不要给普通用户：

- 原始邮件目录。
- 服务器索引目录。
- 权限文件 `permissions.json`。
- 管理员 token。
- 服务器部署脚本。

## 为什么不把服务器 IP 写进用户文件

如果用户文件写死 `http://120.26.219.216:8765/mcp`，以后换服务器时，每个用户都要重新拿文件、重新配置。

稳定入口应该像这样：

```text
https://mail-analysis.company.example/mcp
```

或者内网固定地址：

```text
http://mail-analysis.internal:8765/mcp
```

实际服务器换了，只需要把这个入口转发到新机器。

## 反向代理是什么意思

反向代理就是在用户和真实服务之间放一个固定入口。用户永远访问固定入口，固定入口再把请求转给后面的真实服务器。

```text
用户智能体
  -> https://mail-analysis.company.example/mcp
  -> 反向代理 / 网关 / Nginx
  -> 新服务器 10.x.x.x:8765/mcp
```

以后服务器从 A 换到 B，只改代理转发目标，用户文件不用换。

## 当前项目已经做好的准备

`client/email_mcp_stdio.mjs` 支持三种方式：

1. 环境变量：`MAIL_MCP_BASE_URL`、`MAIL_MCP_TOKEN`。
2. 文件内置：`EMBEDDED_MCP_URL`、`EMBEDDED_TOKEN`。
3. 兼容旧接口：既支持 `/mcp` 远程 MCP，也支持 `/list_mailboxes` 等旧 HTTP 接口。

管理员可以为每个用户复制一份 bridge，并替换：

```text
__MAIL_ANALYSIS_MCP_URL__ -> https://mail-analysis.company.example/mcp
__MAIL_ANALYSIS_TOKEN__   -> 该用户自己的 token
```

## 新服务器拿到后需要做什么

1. 部署本项目服务端代码。
2. 配好原始邮件目录、索引目录、日志目录。
3. 启动 `mail_http_api.py`，监听内部端口，如 `8765`。
4. 配置稳定入口，把 `/mcp` 转发到新服务器服务。
5. 迁移或重新生成 `permissions.json`。
6. 为用户生成 token。
7. 用同一份用户 bridge/Skill 模板生成用户文件。

## 迁移后用户是否需要换文件

如果用户文件里写的是稳定入口，并且 token 权限文件也迁移到了新服务器，用户不需要换文件。

如果用户文件里写的是临时 IP，迁移后就需要重新发文件。

## 最小测试

管理员部署后先测试：

```bash
curl -s -X POST https://mail-analysis.company.example/mcp \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_mailboxes","arguments":{}}}'
```

能返回邮箱列表，说明入口、token、MCP 都可用。
