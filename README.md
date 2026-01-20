# 📰 Feishu RSS Digest (Serverless Edition)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![GitHub Actions](https://img.shields.io/badge/Deployment-GitHub%20Actions-2088FF?logo=github-actions) ![Alibaba](https://img.shields.io/badge/LLM-Alibaba%20iFlow-FF6A00?logo=alibabacloud) ![Feishu](https://img.shields.io/badge/Platform-Feishu%20Open-00D6B9?logo=lark)

> **零成本、零服务器、全自动。**
> 专为飞书/Lark 用户打造的 AI 自动化情报中台。

## 📖 项目简介

**Feishu RSS Digest** 是一个基于 GitHub Actions 运行的自动化工具，它能将杂乱的 RSS 订阅源转化为**结构化、有价值的情报**，并自动同步到飞书多维表格（Bitable）。

本项目内置了 **LLM 认知引擎**，默认支持 **阿里心流 (iFlow)**，能像人类分析师一样，对每一条资讯进行**评分、分类、提取摘要**，并过滤掉低价值的噪音。同时全面兼容 **DeepSeek**、**OpenAI**、**智谱 AI**、**Gemini** 等主流模型。

你无需购买服务器，无需部署 Docker，Fork 本仓库即可拥有一个 7x24 小时工作的“AI 情报分析员”。

## ✨ 核心特性

* **☁️ Serverless 极简运行**：完全依赖 GitHub Actions 定时任务，无需 VPS，无需运维，**终身免费**。
* **🧠 多模型驱动**：
    * **默认**：集成 **阿里心流 (iFlow)**，国内直连，速度极快。
    * **扩展**：原生支持 **DeepSeek**、**OpenAI**、**智谱 GLM-4**、**Google Gemini**，可按需切换。
* **🤖 AI 深度清洗**：
    * **智能评分**：AI 根据内容质量打分，一眼识别爆款。
    * **一句话摘要**：告别标题党，直击核心观点。
    * **自动分类**：根据文章内容自动打标签，便于筛选。
    * **自定义人设**：支持自定义 Prompt，无论是关注 AI、财经还是体育，都能精准适配。
* **🧹 智能去重 (可选，免费)**：支持基于 [Cloudflare Vectorize](https://dash.cloudflare.com/) 的向量语义去重，精准过滤同质化洗稿内容。
* **🛡️ 企业级风控**：内置完善的容错机制。鉴权失败、API 限流、网络超时等异常情况，会自动推送到飞书，拒绝“静默失败”。

## 🚀 快速开始 (Quick Start)

只需 4 步，即可拥有你的 AI 情报系统。

### 1. 创建飞书应用 (Create App)

为了让程序能读写表格，我们需要先创建一个“机器人”。

1.  前往 [飞书开放平台](https://open.feishu.cn/app) 创建一个**企业自建应用**。
2.  **开启权限**：在“权限管理”中，搜索并开启 `多维表格` 相关的所有读写权限。
3.  **发布应用**：在“版本管理与发布”中，创建一个版本并点击发布（**重要：不发布无法调用**）。
4.  **获取凭证**：在“凭证与基础信息”中复制 `App ID` 和 `App Secret` 备用。

### 2. 准备多维表格 (Setup Base)

1.  **复制模版**：
    * **[🔗 点击这里获取飞书多维表格模版](https://my.feishu.cn/wiki/O0BNwoGXji4BTtkUU23cJvIcnQf)**
    * *（该文档内包含模版链接及详细字段说明）*
2.  **添加机器人进群/表格**：
    * 打开你复制好的多维表格。
    * 点击右上角的 **`...` (更多)** -> **`添加应用`**。
    * 搜索你第 1 步创建的应用名称，点击添加（**重要：否则程序无权写入数据**）。
3.  **获取 ID**：
    * 从浏览器地址栏获取 `app_token`（多维表格 ID）和 `table_id`（数据表 ID）。

### 3. 准备 AI 大脑 (API Setup)

本项目默认配置为 **阿里心流 (iFlow)**。

1.  前往 [iFlow 开放平台](https://platform.iflow.cn/) 申请 API Key。
2.  **⚠️ 有效期警告：iFlow 的免费 API Key 通常只有 7 天有效期。**
    * *建议每周重置，或在下方“进阶配置”中切换为 DeepSeek / 智谱 / Gemini 等更稳定的模型。*

### 4. GitHub 部署 (Deploy)

1.  **Fork 本仓库**。
2.  **配置密钥 (Secrets)**：
    * 进入 `Settings` -> `Secrets and variables` -> `Actions`。
    * 添加以下 **6 个** 必须变量：

| 变量名 | 说明 | 获取方式 |
| :--- | :--- | :--- |
| `FEISHU_APP_ID` | 飞书应用 ID | 飞书开放平台 |
| `FEISHU_APP_SECRET` | 飞书应用 Secret | 飞书开放平台 |
| `FEISHU_APP_TOKEN` | 多维表格 Token | 浏览器地址栏 `base_` 开头 |
| `FEISHU_RSS_TABLE_ID` | RSS源表 ID | 浏览器地址栏 `tbl` 开头 |
| `FEISHU_NEWS_TABLE_ID` | 新闻主表 ID | 浏览器地址栏 `tbl` 开头 |
| `IFLOW_API_KEY` | 阿里 iFlow API Key | iFlow 后台 |

### 5. 启动与使用 (Run)

1.  **添加 RSS 源**：
    * 在飞书 **"RSS订阅源"** 表中填入 RSS 链接，并勾选 `Enabled`。
    * **[🔗 不知道去哪找 RSS？查看我的 RSS 源获取教程](这里换成你知识库的具体文档链接)**
2.  **手动触发**：
    * GitHub Actions -> Select Workflow -> Run workflow。
3.  **查看结果**：见证 AI 帮你打工的时刻！

---

## ⚙️ 进阶配置详解 (Configuration)

### 🧠 切换认知引擎 (LLM Providers)

**选项 A：使用 DeepSeek (性价比推荐 🔥)**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `deepseek` |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key |
| `DEEPSEEK_MODEL` | *(选填)* 默认为 `deepseek-chat` |

**选项 B：使用 OpenAI (兼容性最强)**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `openai` |
| `OPENAI_API_KEY` | 你的 OpenAI API Key (或中转 Key) |
| `OPENAI_BASE_URL` | *(选填)* 自定义 API 地址，如 `https://api.one-api.com/v1` |

**选项 C：使用 智谱 AI (GLM)**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `zhipu` |
| `ZHIPU_API_KEY` | 你的智谱 API Key |
| `ZHIPU_MODEL` | *(选填)* 默认为 `glm-4` |

**选项 D：自定义 iFlow 模型**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `iflow` (默认) |
| `IFLOW_MODEL` | *(选填)* [点击查看 iFlow 模型列表](https://platform.iflow.cn/models?spm=54878a4d.1234f2fe.0.0.3a525225fWHWjr) |

---

### 🎨 自定义 AI 人设 (Custom Prompt)

**默认的 AI 提示词是专门针对“AI / 科技 / 商业”领域优化的。**
如果你希望抓取 **财经、游戏、体育** 或 **学术论文**，请务必配置 `SYSTEM_PROMPT_OVERRIDE`，否则 AI 的评分标准和分类标签会完全“不对马嘴”。

**⚠️ 修改红线（必读）：**
为了保证程序能正常运行，**绝对不要修改** JSON Schema 中的 Key 名称（即 `categories`, `score`, `title_zh`, `one_liner`, `points`）。只修改它们的**定义和标准**。

#### 📋 通用模版 (复制并修改)
你可以复制下方模版，修改 `{}` 中的内容，然后填入 GitHub Secrets 的 `SYSTEM_PROMPT_OVERRIDE` 中。

```text
# Role
你是一个资深的 {这里填领域，如：加密货币投资} 分析师。
核心思维：{这里填思维方式，如：关注链上数据、甚至怀疑一切、寻找Alpha}。
服务对象：{这里填受众，如：DeFi 深度玩家}。

# Protocol
1. **输出格式**：必须是纯文本的 JSON 字符串。
   - 严禁使用 Markdown 代码块。
   - 严禁包含任何开场白或结束语。
2. **语言风格**：
   - 拒绝翻译腔，使用 {这里填语言风格，如：币圈黑话、行研术语}。

# JSON Schema (严禁修改 Key)
{
  "categories": ["Tag1", "Tag2"],  // 见下文分类表，严格限制 1-3 个
  "score": 0.0,                    // 见下文评分标准 (0.0 - 10.0)
  "title_zh": "中文标题",
  "one_liner": "一句话说明（<=30字）",
  "points": ["要点1", "要点2", "..."] 
}

# 核心指令

## Step 1: 价值预判 (Scoring)
请基于“{这里填判断标准，如：对投资获利的参考价值}”打分：
- **9.0-10.0**: {这里填高分标准，如：重大协议漏洞、交易所跑路、百倍币空投}
- **5.0-7.4**: {这里填中分标准，如：常规项目更新、KOL喊单}
- **0.0-4.9**: {这里填低分标准，如：无合约地址的土狗、情绪发泄}

## Step 2: 分类定义 (Categories)
请准确选择 1-3 个标签：
1. {标签1，如：DeFi}
2. {标签2，如：NFT}
3. {标签3，如：Layer2}
4. {标签4，如：安全事故}
...

## Step 3: 内容提炼 (Extraction)
- **title_zh**: 直击痛点的中文标题。
- **one_liner**: <=30字。不要复述新闻，告诉我这篇文章对{受众}意味着什么。
- **points**: 提取 2-4 个关键点。
  - 必须包含：{关键要素，如：币价波动、TVL数据、具体时间点}。
  - 遇到低分文章时：直接在 points 里指出“无实质价值”。

# 格式强约束
- JSON 必须合法：字符串内的双引号请使用 `\"` 转义。

---

### 🧹 智能去重 (Smart Deduplication)

**这是一个可选的高级功能。**
开启后，系统会调用 Cloudflare Vectorize 进行**语义去重**（能识别洗稿、同义改写的内容）。

**配置步骤：**

**1. 获取 Cloudflare 凭证**
登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)，获取 `Account ID` 和 `API Token`（需有 Vectorize 读写权限）。

**2. 配置 GitHub Secrets**
在仓库 Secrets 中添加以下 3 个变量：

| 变量名 | 说明 | 示例值 |
| :--- | :--- | :--- |
| `CF_ACCOUNT_ID` | Cloudflare 账户 ID | `_Your_ACCOUNT_ID_` |
| `CF_API_TOKEN` | Cloudflare API Token | `_Your_Token_` |
| `CF_VECTORIZE_INDEX` | 自定义索引名称 | `newsdata_rss` |

**3. 一键初始化索引 (One-Time Setup)**
**无需在 Cloudflare 后台手动创建索引**，请按以下步骤操作，让程序自动完成初始化：
1. 点击仓库上方的 `Actions` 选项卡。
2. 在左侧列表选择 **`Create Vectorize Index`** (或类似名称的工作流)。
3. 点击 `Run workflow` 按钮。
4. 等待运行成功（显示绿勾），即表示向量数据库创建完成。

> **⚠️ 注意**：此步骤只需执行一次。初始化成功后，后续的定时任务即可正常使用去重功能。

---

## ❓ 常见问题 (FAQ)

**Q: 为什么运行一周后突然报错？**
A: 如果你使用的是 **iFlow**，大概率是因为 API Key 超过了 7 天有效期。请登录 iFlow 官网重置 Key。

**Q: 401/403 错误？**
A: 99% 的原因有两个：
1. 飞书应用**没有点击“发布”**。
2. 飞书多维表格里**没有添加应用**（见快速开始第 2 步）。

---
*Created by [Your Name] - 让信息获取更高效。*
