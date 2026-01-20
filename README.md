# NewsData_RSS

不依赖 FreshRSS 的 RSS 抓取方案：RSS 源来自飞书表，增量抓取 + 飞书主表 item_key 去重，可选 Vectorize 近似去重。

## 依赖安装

```powershell
pip install -r requirements.txt
```

## 表结构要求

### RSS 源表字段
需与 `config.py` 中的 RSS 字段名一致：

- name
- feed_url
- type
- description
- enabled
- status
- last_fetch_time
- last_fetch_status
- consecutive_fail_count
- last_item_guid
- last_item_pub_time
- item_id_strategy
- content_language

单选字段建议选项（需与你表里一致）：
- type：自行维护
- status：idle / ok / unstable / dead
- last_fetch_status：success / timeout / http_error / parse_error
- item_id_strategy：guid / link / title_pubdate / content_hash
- content_language：zh / en / jp / mixed / other

### 新闻主表字段
需与 `config.py` 中的新闻字段名一致：

- 标题
- AI打分
- 分类
- 总结
- 发布时间
- 来源
- 全文
- item_key

## 初始化（创建字段 + 导入 FreshRSS 订阅）

```powershell
python rss_bootstrap.py
```

## 运行

```powershell
python rss_ingest.py
```

## LLM 配置（可选）

默认使用 Gemini，可通过环境变量切换到 iFlow（OpenAI 兼容接口）。

### 使用 Gemini（默认）

必填：
- `GEMINI_API_KEY`

可选：
- `GEMINI_MODEL_NAME`（默认 `gemini-3-flash-preview`）

### 使用 iFlow

必填：
- `LLM_PROVIDER=iflow`
- `IFLOW_API_KEY`

可选：
- `IFLOW_MODEL`（默认 `qwen3-max`）
- `IFLOW_BASE_URL`（默认 `https://apis.iflow.cn/v1`）
- `IFLOW_TIMEOUT` / `IFLOW_RETRIES`

## 逻辑说明

- 增量筛选：优先使用 `last_item_pub_time`，否则用 `last_fetch_time`。
- 去重：飞书主表预取最近 500 条 `item_key` 做精确去重；可选 Vectorize 近似去重。
- 成功抓取会更新 RSS 源表的状态与时间字段。

## 失败提醒（多维表通知）

通过“提醒记录”表 + 飞书自动化实现个人通知。程序会在一次运行中记录首个根因，避免刷屏。

### 提醒记录表字段（建议）
- 事件
- 详情
- 说明
- 触发时间
- 已通知

### 需要的环境变量
- `FEISHU_NOTIFY_TABLE_ID`（提醒记录表 table_id）
- 可选：`NOTIFY_FIELD_EVENT` / `NOTIFY_FIELD_DETAIL` / `NOTIFY_FIELD_PLAIN` / `NOTIFY_FIELD_TRIGGER_TIME` / `NOTIFY_FIELD_NOTIFIED`

### 默认会触发的提醒类型
- 鉴权失败（401/403 或缺 Key）
- 限流/配额不足（429）
- 上游服务异常（5xx）
- 网络超时
- 输出解析失败
- 关键配置缺失

## GitHub Actions Secrets

运行工作流需在仓库 `Settings → Secrets and variables → Actions` 配置：

基础必填：
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_APP_TOKEN`
- `FEISHU_NEWS_TABLE_ID` / `FEISHU_RSS_TABLE_ID`

LLM：
- Gemini：`GEMINI_API_KEY`
- iFlow：`LLM_PROVIDER` / `IFLOW_API_KEY` / `IFLOW_MODEL`（可选）

Vectorize（可选）：
- `CF_API_TOKEN` / `CF_ACCOUNT_ID` / `CF_VECTORIZE_INDEX`

提醒记录（可选）：
- `FEISHU_NOTIFY_TABLE_ID`

## 重要配置

- `config.py`：读取环境变量（飞书 app_id/secret、app_token、表 table_id、Gemini key、Cloudflare 配置、字段名映射）
