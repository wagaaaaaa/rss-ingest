# RSS-Ingest 并发队列与精选流程设计

**目标**：参考 `rss-ingest-local`，将并发 LLM 队列与精选流程引入 `rss-ingest` 主流程；保持默认模型为 qwen（`LLM_PROVIDER=nvidia`）。不包含 deep_analysis。

**范围**
- 修改：`config.py`、`rss_ingest.py`
- 可选修改：`README.md`
- 不包含：`deep_analysis.py` 及相关逻辑

## 设计概览
主流程保持「抓取 → 去重 → LLM 处理 → 写入表」不变，新增两处阶段：
1) **队列拆分与并发执行**：把待处理记录构建为队列，并发调用 LLM。
2) **精选流程**：从本次新增记录中抽取候选，统一调用精选 LLM，写回“精选”字段。

默认模型仍为 qwen，仅在设置覆盖环境变量时更换摘要/精选模型。

## 配置与兼容性
新增或扩展配置项（默认不破坏现有行为）：
- `LLM_CONCURRENCY=4`：并发线程数，默认 4，可通过 env 覆盖。
- `PROGRESS_BAR_WIDTH=20`：进度条宽度（可选）。
- `NEWS_FIELD_FEATURED="精选"`：精选字段名（新增）。
- 可选覆盖：
  - `QWEN_MODEL_NAME_SUMMARY` 默认回落到主模型
  - `QWEN_MODEL_NAME_PRO` 默认回落到主模型

> 说明：`LLM_PROVIDER` 默认仍为 `nvidia`（qwen 模型）。

## 关键流程
### 1. 队列拆分
- 遍历源，生成 `queue`（每个 item 包含 record_id、source、retry_budget 等）。
- 统计：`queue_total / sources_processed / sources_skipped`。

### 2. 并发执行
- 使用 `ThreadPoolExecutor(max_workers=LLM_CONCURRENCY)`。
- 每个任务独立 try/except：失败仅影响该条；重试预算耗尽则标记失败。
- 每完成一个任务，刷新进度条：`[====.....] done/total`。

### 3. 精选流程
- LLM 处理完成后，符合条件的记录进入 `featured_candidates`。
- 队列结束后一次性调用精选 LLM：
  - `build_featured_prompt(...)`
  - `call_featured_llm(...)`
  - `parse_featured_ids(...)`
  - `apply_featured(...)`（仅勾选新增记录，不取消已有精选）

## 错误处理
- 队列任务失败：记录日志 + 重试，耗尽预算后继续后续任务。
- 精选失败：仅记录与告警，不影响主流程写入。
- 进度条：成功/失败都推进，避免卡死。

## 测试建议（最小集）
- `tests/test_rss_ingest_queue.py`：队列拆分与重试预算。
- `tests/test_rss_ingest_progress.py`：进度条渲染。
- `tests/test_featured_parse.py`：精选 ID 解析鲁棒性。

## 验收标准
- 默认 `LLM_PROVIDER=nvidia` 和默认模型不变。
- 设置 `LLM_CONCURRENCY` 后并发生效，进度条可见。
- 精选流程可正确勾选 `NEWS_FIELD_FEATURED`。
