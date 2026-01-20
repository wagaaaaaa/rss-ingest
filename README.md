# 📰 Feishu RSS Digest (Serverless Edition)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![GitHub Actions](https://img.shields.io/badge/Deployment-GitHub%20Actions-2088FF?logo=github-actions) ![iFlow](https://img.shields.io/badge/AI-Powered%20by%20iFlow-00A98F?logo=spark) ![Feishu](https://img.shields.io/badge/Platform-Feishu%20Open-00D6B9?logo=lark)

> **零成本、零服务器、全自动。**
> 专为飞书/Lark 用户打造的 AI 自动化情报中台。

## 📖 项目简介

**Feishu RSS Digest** 是一个基于 GitHub Actions 运行的自动化工具，它能将杂乱的 RSS 订阅源转化为**结构化、有价值的情报**，并自动同步到飞书多维表格（Bitable）。

不同于普通的 RSS 阅读器，本项目内置了 **LLM 认知引擎**（默认支持免费的 **iFlow API**），能像人类分析师一样，对每一条资讯进行**评分、分类、提取摘要**，并过滤掉低价值的噪音。

你无需购买服务器，无需部署 Docker，Fork 本仓库即可拥有一个 7x24 小时工作的“AI 情报分析员”。

## ✨ 核心特性

* **☁️ Serverless 极简运行**：完全依赖 GitHub Actions 定时任务，无需 VPS，无需运维，**终身免费**。
* **🆓 iFlow 免费驱动**：默认集成 iFlow (讯飞星火) 接口，获取极易，额度充足，无需担心昂贵的 API 费用（同时也兼容 Gemini/OpenAI）。
* **🧠 AI 深度清洗**：
    * **智能评分**：AI 根据内容质量打分，一眼识别爆款。
    * **一句话摘要**：告别标题党，直击核心观点。
    * **自动分类**：根据文章内容自动打标签，便于筛选。
* **🛡️ 企业级风控**：内置完善的容错机制。鉴权失败、API 限流、网络超时等异常情况，会自动推送到飞书，拒绝“静默失败”。
* **🧹 智能去重 (可选)**：支持基于 Cloudflare Vectorize 的向量语义去重，精准过滤同质化洗稿内容。
* **📊 飞书可视化**：利用飞书多维表格的强大能力，支持看板视图、自动化流程和即时协作。

## 🚀 快速开始 (Quick Start)

只需 3 步，即可拥有你的 AI 情报系统。

### 1. 准备飞书环境 (Feishu Setup)

为了让数据能写入飞书，你需要准备一个多维表格和一个飞书应用。

1.  **复制多维表格模版**：
    * **[🔗 点击这里复制模版 (请替换为你生成的模版链接)]**
    * *（模版中已包含“RSS源”、“新闻列表”、“提醒记录”三张表及所需字段）*
    * 复制后，从浏览器地址栏获取 `app_token`（多维表格 ID）和 `table_id`（数据表 ID）。
2.  **创建飞书应用**：
    * 前往 [飞书开放平台](https://open.feishu.cn/app) 创建一个企业自建应用。
    * **开启权限**：在“权限管理”中开启 `多维表格` 相关读写权限。
    * **获取凭证**：在“凭证与基础信息”中复制 `App ID` 和 `App Secret`。
    * **发布应用**：创建一个版本并发布（否则无法调用 API）。

### 2. 准备 AI 大脑 (iFlow Setup)

本项目默认使用 **iFlow** (SparkDesk) 作为认知引擎，因为它免费、速度快且易于申请。

1.  前往 [讯飞开放平台](https://xinghuo.xfyun.cn/) 获取 API Key。
    * *注：如果你更习惯使用 Gemini 或 OpenAI，也可在后续配置中切换。*

### 3. GitHub 部署 (Deploy on GitHub)

1.  **Fork 本仓库**：点击右上角的 `Fork` 按钮，将项目复制到你的 GitHub 账号下。
2.  **配置密钥 (Secrets)**：
    * 进入 Fork 后的仓库，点击 `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`。
    * 依次添加以下 **6 个** 必须变量：

| 变量名 (Name) | 说明 (Value/Description) | 获取方式 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用 ID | 飞书开放平台 |
| `FEISHU_APP_SECRET` | 飞书应用 Secret | 飞书开放平台 |
| `FEISHU_APP_TOKEN` | 多维表格的 Token | 浏览器地址栏 `base_` 开头的部分 |
| `FEISHU_RSS_TABLE_ID` | "RSS订阅源"表的 ID | 浏览器地址栏 `tbl` 开头的部分 |
| `FEISHU_NEWS_TABLE_ID` | "新闻主表"表的 ID | 浏览器地址栏 `tbl` 开头的部分 |
| `IFLOW_API_KEY` | iFlow (讯飞) 的 API Key | 讯飞开放平台 |

### 4. 启动与验证 (Run)

1.  **配置 RSS 源**：打开你的飞书多维表格，在 **"RSS订阅源"** 表中填入你要抓取的 RSS 链接（例如：`https://techcrunch.com/feed/`），并将 `Enabled` 状态勾选为 ✅。
2.  **手动触发**：
    * 回到 GitHub 仓库，点击 `Actions` 选项卡。
    * 选择左侧的 `RSS Ingest Workflow`。
    * 点击右侧的 `Run workflow` 按钮。
3.  **查看结果**：等待约 1-2 分钟，刷新你的飞书多维表格，看着新闻一条条自动蹦出来吧！🎉
    * *之后系统将按照 `.github/workflows/rss-ingest.yml` 中定义的时间自动运行。*

---

## ⚙️ 进阶配置详解 (Configuration)

本项目支持丰富的自定义配置。为了方便管理，我们将环境变量分为 **“基础必填”** 和 **“进阶选填”** 两类。

### ✅ 1. 基础必填项 (Basic Required)
*只需配置这 6 个变量，系统即可正常运行（默认使用 iFlow 模型）。*
*(见上方快速开始表格)*

### 🛠️ 2. 进阶选填项 (Advanced Optional)
*如果你需要切换模型、开启去重或自定义提示词，请配置以下变量。*

#### **A. 认知引擎设置 (LLM Settings)**

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `iflow` | 指定使用的 LLM 提供商。可选值：`iflow` / `gemini` / `openai`。 |
| `GEMINI_API_KEY` | - | **如果切换为 Gemini**，需填写此 Google API Key。 |
| `IFLOW_MODEL` | `generalv3.5` | iFlow 的模型版本号（如需指定特定版本）。 |
| `SYSTEM_PROMPT_OVERRIDE` | *(内置)* | **高玩专用**。自定义系统提示词，用来覆盖默认的评分/分类逻辑。 |

#### **B. 智能去重设置 (Cloudflare Vectorize)**
*开启此功能需拥有 Cloudflare Vectorize 账号，可大幅减少重复内容。*

| 变量名 | 说明 |
| :--- | :--- |
| `CF_ACCOUNT_ID` | Cloudflare 账户 ID |
| `CF_API_TOKEN` | Cloudflare API Token |
| `CF_VECTORIZE_INDEX` | 向量索引名称 (Index Name) |

#### **C. 消息通知 (Notification)**

| 变量名 | 说明 |
| :--- | :--- |
| `FEISHU_NOTIFY_TABLE_ID` | **强烈推荐**。"提醒记录表" ID。配置后，系统运行报错（如限流/超时/鉴权失败）会写入此表并推送飞书卡片。 |

---

## ❓ 常见问题 (FAQ)

**Q: 为什么运行报错 401/403？**
A: 通常是因为飞书的 App ID/Secret 填错了，或者在飞书后台没有“发布”应用版本。请检查权限管理中是否开启了多维表格权限。

**Q: 为什么提示 429 Too Many Requests？**
A: 可能是 LLM 接口限流或飞书 API 频率过高。系统会自动重试，如果频繁出现，请检查 API 额度。

**Q: GitHub Actions 会收费吗？**
A: 公共仓库（Public Repo）的 Actions 是免费的。如果是私有仓库，GitHub 每月提供 2000 分钟免费额度，对个人使用绰绰有余。

**Q: 如何修改抓取频率？**
A: 修改仓库中 `.github/workflows/rss-ingest.yml` 文件里的 `cron` 表达式即可。

## 🤝 贡献与支持

欢迎提交 Issue 或 Pull Request！
如果你喜欢这个项目，请给一个 ⭐️ Star。

---
*Created by [Your Name/Handle] - 让信息获取更高效。*
