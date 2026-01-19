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

## 逻辑说明

- 增量筛选：优先使用 `last_item_pub_time`，否则用 `last_fetch_time`。
- 去重：飞书主表预取最近 500 条 `item_key` 做精确去重；可选 Vectorize 近似去重。
- 成功抓取会更新 RSS 源表的状态与时间字段。

## 重要配置

- `config.py`：读取环境变量（飞书 app_id/secret、app_token、表 table_id、Gemini key、Cloudflare 配置、字段名映射）
