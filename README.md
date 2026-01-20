# Feishu RSS Digest

把 RSS 源放进飞书多维表，系统会定时抓取并生成“分类、评分、摘要、要点”，自动写回你的飞书新闻主表。你只需要维护源列表，其余交给系统处理。

## 快速开始（10 分钟跑通）

### 1) 你需要准备的账号

- 飞书开放平台（Bitable）
- LLM（默认 Gemini；可选 iFlow）
- Cloudflare（可选，用于 Vectorize 近似去重）

### 2) 你需要设置的 Secrets（GitHub Actions）

在仓库 `Settings → Secrets and variables → Actions` 里新增：

基础必填：
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_APP_TOKEN`
- `FEISHU_NEWS_TABLE_ID`
- `FEISHU_RSS_TABLE_ID`

LLM（二选一）：
- Gemini：`GEMINI_API_KEY`
- iFlow：`LLM_PROVIDER=iflow`、`IFLOW_API_KEY`

可选（Vectorize 近似去重）：
- `CF_API_TOKEN`
- `CF_ACCOUNT_ID`
- `CF_VECTORIZE_INDEX`

可选（失败提醒记录表）：
- `FEISHU_NOTIFY_TABLE_ID`

### 3) 运行方式

GitHub Actions（推荐）：
- 打开 Actions → `rss-ingest` → `Run workflow`
- 或等待定时触发（见 `.github/workflows/rss-ingest.yml`）

本地运行：
```powershell
pip install -r requirements.txt
python rss_ingest.py
```

### 4) 你会看到的结果

- “新闻主表”新增记录（标题/摘要/分类/分数/全文等）
- “RSS 源表”字段被更新（抓取状态与时间）

## 表结构与模板

> 建议先创建空表，再按以下字段配置。  
> [TODO: 贴出“表模板链接”或截图说明]

### RSS 源表字段（必须与 `config.py` 字段名一致）

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

### 新闻主表字段（必须与 `config.py` 字段名一致）

- 标题
- AI打分
- 分类
- 总结
- 发布时间
- 来源
- 全文
- item_key

### 提醒记录表字段（可选）

建议字段：
- 事件
- 详情
- 说明
- 触发时间
- 已通知

[TODO: 如果字段名不同，请在下方“环境变量”里说明映射]

## 环境变量配置（完整清单）

### 飞书基础

- `FEISHU_APP_ID`：飞书 App ID
- `FEISHU_APP_SECRET`：飞书 App Secret
- `FEISHU_APP_TOKEN`：Bitable App Token
- `FEISHU_NEWS_TABLE_ID`：新闻主表 ID
- `FEISHU_RSS_TABLE_ID`：RSS 源表 ID

### LLM（默认 Gemini）

Gemini：
- `GEMINI_API_KEY`
- `GEMINI_MODEL_NAME`（可选，默认 `gemini-3-flash-preview`）

iFlow（OpenAI 兼容）：
- `LLM_PROVIDER=iflow`
- `IFLOW_API_KEY`
- `IFLOW_MODEL`（可选，默认 `qwen3-max`）
- `IFLOW_BASE_URL`（可选，默认 `https://apis.iflow.cn/v1`）
- `IFLOW_TIMEOUT` / `IFLOW_RETRIES`（可选）

### 去重（Vectorize，可选）

- `CF_API_TOKEN`
- `CF_ACCOUNT_ID`
- `CF_VECTORIZE_INDEX`
- `CF_VECTORIZE_TOP_K`（可选）
- `CF_VECTORIZE_SIM_THRESHOLD`（可选）

### 提醒记录（可选）

- `FEISHU_NOTIFY_TABLE_ID`
- `NOTIFY_FIELD_EVENT`（默认 `事件`）
- `NOTIFY_FIELD_DETAIL`（默认 `详情`）
- `NOTIFY_FIELD_PLAIN`（默认 `说明`）
- `NOTIFY_FIELD_TRIGGER_TIME`（默认 `触发时间`）
- `NOTIFY_FIELD_NOTIFIED`（默认 `已通知`）

## 运行逻辑说明（你关心的点）

- 系统会优先用 `last_item_pub_time` 做增量过滤，避免重复抓取。
- 主表会预取最近 500 条 `item_key` 做精确去重；如你开启 Vectorize，会再做近似去重。
- 抓取成功后会回写 RSS 源表的状态与时间字段。
- LLM 会生成结构化结果（分类/分数/标题/要点）。

## LLM 总结提示词

提示词在 `rss_ingest.py` 的 `SYSTEM_PROMPT` 中维护。  
[TODO: 如果你想在 README 中展示最新版本，可在此贴出]

## 失败提醒（多维表通知）

你可以用“提醒记录表 + 飞书自动化”实现个人提醒。  
系统会在一次运行中记录首个根因，避免刷屏。

默认触发的提醒类型：
- 鉴权失败（401/403 或缺 Key）
- 限流/配额不足（429）
- 上游服务异常（5xx）
- 网络超时
- 输出解析失败
- 关键配置缺失

## GitHub Actions

### 定时任务

`rss-ingest` 使用 cron 定时运行，见 `.github/workflows/rss-ingest.yml`。

### 创建 Vectorize 索引

`create-vectorize-index` 仅需运行一次。  
[TODO: 若你有固定索引名或维度要求，说明在此处]

## FAQ / 排错

- 401/403：密钥无效/过期/权限不足，更新 Secret。
- 429：配额不足或请求频率过高，降低频率或检查额度。
- 5xx：上游服务异常，稍后重试。
- RSS 403：源站拦截，建议替换源或仅本地运行。
- 内网 RSS 源：GitHub Actions 无法访问，请禁用或改公网源。
- 飞书写入失败：检查 `FEISHU_APP_TOKEN` / 表 ID 是否一致。

## 开源许可与贡献

- License: [TODO: 选择 MIT/Apache-2.0 等并补链接]
- 贡献方式：[TODO: 贡献指南链接或说明]

## 维护者

- [TODO: 你的联系方式或主页链接]
