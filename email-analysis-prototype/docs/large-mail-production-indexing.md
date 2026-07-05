# 大邮件生产索引方案

本文定义本项目的默认生产索引方式。项目已确定面向大邮件库，因此不再区分“小规模方案”和“大邮件方案”；部署和运维都按大邮件生产模式执行。

## 结论

服务器 MCP 架构方向保持不变：原始邮件留在服务器，MCP 只读服务器索引，权限由 token 和 `permissions.json` 控制，用户侧不下载原始邮件。

生产索引必须采用：

```text
增量发现变化文件 -> indexed_files 状态表 -> parser worker -> mailbox/year_month 分片 -> rollup/thread index -> MCP 按权限查询索引
```

`mcp-server/server/mail_indexer.py` 已内置单机生产索引器骨架：支持 `--changed-list` 增量输入、`indexed_files.sqlite` 状态表、mailbox/year_month 分片、`index_jobs` checkpoint、dead-letter、rollup 摘要和 `thread_index.sqlite`。它可以用于服务器小范围真实邮箱验证和初始回填批次；日常生产仍必须由同步日志、文件事件或上游清单提供 changed set，不能把全邮件库周期性扫描当成调度方式。

## 包内生产索引器能力和边界

当前部署包内的 `mail_indexer.py` 已经实现本项目需要的单机生产索引骨架：

1. `--changed-list <file>`：只接收新增、变化、删除文件清单，避免日常调度扫描全库。
2. `$MAIL_INDEX_ROOT/<mailbox_id>/state/indexed_files.sqlite`：记录文件大小、mtime、parser_version、状态、evidence_id、thread_id、shard_id、run_id。
3. `$MAIL_INDEX_ROOT/<mailbox_id>/shards/YYYY/MM/evidence.jsonl`：按年月分片写 evidence，不再依赖整邮箱 `evidence_map.json`。
4. `$MAIL_INDEX_ROOT/<mailbox_id>/rollups/thread_index.sqlite`：MCP 用 evidence_id/thread_id 定位 shard。
5. `$MAIL_INDEX_ROOT/<mailbox_id>/state/index_jobs.sqlite` 内的 `index_jobs` 表：记录 job、cursor、running/succeeded/failed 状态。
6. `--resume-job-id <job_id>`：从 checkpoint manifest 继续处理未完成 group。
7. `state/dead_letter.jsonl`：记录失败 message group，不阻塞同一邮箱其他邮件。
8. MCP API 已优先读取 rollup/thread index 和 shard evidence，旧 `summary.json` / `threads.json` 仅作为兼容输出。

现场仍必须完成三件事：

1. 从邮件同步日志、对象存储清单、文件系统事件或调度平台生成 changed-list。
2. 对初始回填做分批、限速、监控，不把整个 50T 邮件库作为一个不可中断任务。
3. 在真实服务器上用小范围真实邮箱验证吞吐、IO、失败率、索引延迟和恢复流程。

受控全量扫描只允许用于初始回填、低频对账或修复。日常生产必须输入 changed-list。
## 目标架构

生产索引层拆成五个部分：

```text
MAIL_RAW_ROOT                  原始邮件，只读
  -> change discovery          发现新增、变化、删除
  -> indexed_files state       记录每个文件处理状态
  -> parser workers            只解析变化文件
  -> shard writer              写 mailbox + 年月分片
  -> rollup/index publisher    发布 MCP 查询用摘要、线程、证据索引
```

MCP 服务仍然只读索引目录，不直接暴露原始邮件路径。权限仍然由 `MAIL_PERMISSIONS_FILE` 校验。

## indexed_files 状态表

每个邮箱建立一个状态库，例如：

```text
$MAIL_INDEX_ROOT/<mailbox_id>/state/indexed_files.sqlite
```

建议字段：

```text
mailbox_id
relative_path
file_size
mtime_ns
content_hash
parser_version
record_id
thread_id
evidence_id
shard_id
status              pending | indexed | failed | deleted
error_message
retry_count
first_seen_at
last_seen_at
indexed_at
run_id
```

判断文件是否需要重建索引的最小条件：`relative_path + file_size + mtime_ns + parser_version` 变化。对关键文件可补充 `content_hash`，但不要在每轮调度中对全量历史邮件重新计算 hash。

## 增量索引流程

1. 发现候选文件：来自同步日志、文件系统事件、上游清单，或低频对账扫描。
2. 和 `indexed_files` 比较，只把新增、大小变化、mtime 变化、解析器版本变化的文件放入任务队列。
3. parser worker 解析 `.docx`、`.eml`、`.ics`、文本文件，并记录附件。
4. 解析成功后写入对应 shard 的临时文件或 staging 表。
5. 同一事务更新 `indexed_files` 状态和 shard manifest。
6. 定期对比 `last_seen_at`，把原始目录已经不存在的文件标记为 `deleted`。
7. rollup 任务只重算受影响的 mailbox/month/thread，不重算整个邮箱。

变化发现优先使用上游同步日志或事件流；低频目录扫描只用于对账，不作为日常主调度。

## 分片策略

分片维度：

```text
mailbox_id / year_month
```

示例目录：

```text
$MAIL_INDEX_ROOT/<mailbox_id>/shards/2026/07/evidence.jsonl
$MAIL_INDEX_ROOT/<mailbox_id>/shards/2026/07/threads.jsonl
$MAIL_INDEX_ROOT/<mailbox_id>/shards/2026/07/manifest.json
$MAIL_INDEX_ROOT/<mailbox_id>/rollups/summary.json
$MAIL_INDEX_ROOT/<mailbox_id>/rollups/thread_index.sqlite
$MAIL_INDEX_ROOT/<mailbox_id>/index_status.json
```

`year_month` 优先取邮件发送时间；取不到时用文件 mtime；再取不到时进入 `unknown` 分片。MCP 查询如果有时间过滤，只读相关分片；没有时间过滤，优先读 rollup 摘要和线程索引，而不是扫全量 evidence。

## 可恢复任务设计

生产索引器需要任务表，例如：

```text
index_jobs
job_id
mailbox_id
job_type           backfill | incremental | compact | repair
shard_id
status             queued | running | succeeded | failed | canceled
cursor
lease_owner
lease_expires_at
started_at
finished_at
error_message
```

恢复规则：

1. 每个 worker 获取带 lease 的任务，超时任务可被其他 worker 接管。
2. 每处理一批文件就提交 checkpoint，不把一个邮箱作为单个不可中断任务。
3. shard 写入采用临时文件加原子 rename，避免半写文件被 MCP 读到。
4. evidence_id、thread_id 使用稳定输入生成，重复执行不产生重复记录。
5. 解析失败进入 `failed` 状态和死信清单，不阻塞整个邮箱。

## 初始回填与日常增量

初始回填：

1. 按邮箱分批。
2. 每个邮箱再按目录或年月切片生成 backfill job。
3. 限制并发和 IO，避免影响邮件服务器正常业务。
4. 每天输出 backfill 进度：已发现文件数、已索引文件数、失败数、剩余估算、最大索引延迟。

日常增量：

1. 频繁运行变化发现任务，但只处理 changed set。
2. parser worker 按队列消费，不重复解析未变化文件。
3. rollup 可以延迟几分钟合并，保证查询性能和写入成本平衡。
4. 定期 compact 旧分片，减少小文件和重复记录。

## MCP 读取兼容

生产索引保持现有工具契约：

```text
list_mailboxes
get_index_status
query_summary
search_threads
get_evidence
rebuild_index
```

内部读取路径升级为 shard/rollup 即可。`query_summary` 优先读 rollup；`search_threads` 查询 thread index；`get_evidence` 根据 evidence_id 定位到 shard 后返回受控摘录。对外不要返回服务器 `raw_path`。

## 安全边界

1. 原始邮件仍只在服务器上，用户侧不下载邮件目录。
2. 用户仍只能通过 MCP token 查询授权邮箱。
3. evidence 默认只返回受控摘录、主题、发件人、收件人、时间、附件名和 evidence_id。
4. 大段原文、附件正文、批量导出必须另设权限和审计，不作为普通查询默认能力。
5. 所有工具调用继续写入 `access_audit.jsonl`，生产环境建议再接入集中日志或 SIEM。
6. 禁止新增任意 `read_file(path)`、`list_dir(path)`、shell、SSH 或通用文件系统 MCP 工具。

## 运维要求

生产环境至少需要：

1. systemd service/timer 或任务队列，替代高频全量扫描。
2. 单邮箱、单分片并发限制，避免回填挤爆磁盘 IO。
3. index lag 指标：最后发现时间、最后索引时间、失败文件数、队列长度。
4. 磁盘容量预估和索引保留策略。
5. 索引目录备份或可重建策略。
6. parser_version 管理：解析规则变更后只重建受影响分片。
7. 权限文件备份和 token 轮换流程。
8. 异常文件隔离：损坏 docx、乱码 eml、超大附件、压缩包不阻塞任务。

## 服务器验证步骤

### 1. 日常增量验证

准备 changed-list，每行是相对 mailbox 根目录的文件路径：

```text
2026/07/streamview/message.eml
2026/07/streamview/attachments/quote.pdf
```

运行：

```bash
CHANGED_LIST=/data/mail-analysis/changed/2026-07-04.txt \
MAILBOX_IDS="mailbox_a" \
./mcp-server/run_index_docx_mailboxes.sh
```

验证输出：

```text
$MAIL_INDEX_ROOT/mailbox_a/state/indexed_files.sqlite
$MAIL_INDEX_ROOT/mailbox_a/shards/YYYY/MM/evidence.jsonl
$MAIL_INDEX_ROOT/mailbox_a/rollups/summary.json
$MAIL_INDEX_ROOT/mailbox_a/rollups/thread_index.sqlite
$MAIL_INDEX_ROOT/mailbox_a/index_status.json
```

### 2. 初始回填验证

初始回填必须分邮箱、分时间段、限速执行。只有在明确控制范围时才允许：

```bash
ALLOW_BACKFILL_SCAN=1 \
MAILBOX_IDS="mailbox_a" \
MAX_GROUPS=10000 \
./mcp-server/run_index_docx_mailboxes.sh
```

如果 `index_status.json` 返回 `status: partial`，记录 `job_id` 后继续：

```bash
RESUME_JOB_ID=<job_id> \
MAILBOX_IDS="mailbox_a" \
./mcp-server/run_index_docx_mailboxes.sh
```

### 3. MCP 查询验证

索引完成后，用用户 token 调 `query_summary`、`search_threads`、`get_evidence`。MCP 应读取 rollup/shard，不应读取原始邮件目录。
## 验收标准

1. 新增一封邮件后，只解析该邮件相关文件，不重扫整个邮箱。
2. 修改解析器版本后，只重建受影响的文件或分片。
3. 索引进程被 kill 后，可以从 checkpoint 继续。
4. 单个坏文件不导致整个邮箱失败。
5. 旧文件删除后，查询结果能通过 tombstone 或 rollup 更新反映删除。
6. MCP 权限行为和当前服务一致：未授权邮箱返回 forbidden。
7. `query_summary`、`search_threads`、`get_evidence` 不需要读取原始目录才能回答。
8. 审计日志能追踪 user_id、tool、mailbox_id、query、evidence_id/thread_id、status。

## 部署文档中的要求

`docs/deployment-handoff-for-admin.md` 已按大邮件生产模式编写。正式生产部署前，应在服务器用小范围真实邮箱验证 changed-list 增量、受控回填、分片写入、断点恢复、失败文件记录和 MCP 查询链路。