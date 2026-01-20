# 📰 Feishu RSS Digest (Serverless Edition)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![GitHub Actions](https://img.shields.io/badge/Deployment-GitHub%20Actions-2088FF?logo=github-actions) ![Alibaba](https://img.shields.io/badge/LLM-Alibaba%20iFlow-FF6A00?logo=alibabacloud) ![Feishu](https://img.shields.io/badge/Platform-Feishu%20Open-00D6B9?logo=lark)

> **零成本、零服务器、全自动。**
> 专为飞书/Lark 用户打造的 AI 自动化情报中台。

## 📖 项目简介

**Feishu RSS Digest** 是一个基于 GitHub Actions 运行的自动化工具，它能将杂乱的 RSS 订阅源转化为**结构化、有价值的情报**，并自动同步到飞书多维表格（Bitable）。

本项目内置了 **LLM 认知引擎**，默认支持 **阿里心流 (iFlow)**，能像人类分析师一样，对每一条资讯进行**评分、分类、提取摘要**，并过滤掉低价值的噪音。同时也全面兼容 **DeepSeek**、**OpenAI**、**智谱 AI**、**Gemini** 等主流模型。

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
* **🛡️ 企业级风控**：内置完善的容错机制。鉴权失败、API 限流、网络超时等异常情况，会自动推送到飞书，拒绝“静默失败”。
* **🧹 智能去重 (可选)**：支持基于 Cloudflare Vectorize 的向量语义去重，精准过滤同质化洗稿内容。

## 🚀 快速开始 (Quick Start)

只需 3 步，即可拥有你的 AI 情报系统。

### 1. 准备飞书环境 (Feishu Setup)

1.  **复制多维表格模版**：
    * **[🔗 点击这里复制模版 (请替换你的链接)]**
    * 复制后，从浏览器地址栏获取 `app_token`（多维表格 ID）和 `table_id`（数据表 ID）。
2.  **创建飞书应用**：
    * 前往 [飞书开放平台](https://open.feishu.cn/app) 创建企业自建应用。
    * **开启权限**：开启 `多维表格` 相关读写权限。
    * **获取凭证**：复制 `App ID` 和 `App Secret`。
    * **发布应用**：创建一个版本并发布。

### 2. 准备 AI 大脑 (API Setup)

本项目默认配置为 **阿里心流 (iFlow)**。

1.  前往 [iFlow 开放平台 (platform.iflow.cn)](https://platform.iflow.cn/) 申请 API Key。
2.  **⚠️ 重要提示：iFlow 的免费 API Key 有效期通常为 7 天。**
    * *这意味着你每 7 天需要手动登录平台重置 Key，并更新到 GitHub Secrets 中。*
    * *如果你希望实现“真正的全自动”，建议使用下方的 DeepSeek、OpenAI 或 智谱 AI 方案。*

### 3. GitHub 部署 (Deploy)

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

### 4. 启动 (Run)
* 在飞书表格填入 RSS 源 -> GitHub Actions 手动触发 -> 见证奇迹。

---

## ⚙️ 进阶配置详解 (Configuration)

### 🧠 切换认知引擎 (LLM Providers)
*嫌每周更新 iFlow Key 太麻烦？你可以切换到以下模型，实现真正的“长期自动化”。*

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
| `OPENAI_MODEL` | *(选填)* 默认为 `gpt-3.5-turbo` |

**选项 C：使用 智谱 AI (GLM)**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `zhipu` |
| `ZHIPU_API_KEY` | 你的智谱 API Key |
| `ZHIPU_MODEL` | *(选填)* 默认为 `glm-4` |

**选项 D：使用 Google Gemini (免费额度高)**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | 你的 Google AI Studio Key |

**选项 E：自定义 iFlow 模型**
| 变量名 | 值/说明 |
| :--- | :--- |
| `LLM_PROVIDER` | `iflow` (默认) |
| `IFLOW_MODEL` | *(选填)* 指定特定模型版本 |

---

### 🛠️ 其他高级设置

**1. 智能去重 (Cloudflare Vectorize)**
| 变量名 | 说明 |
| :--- | :--- |
| `CF_ACCOUNT_ID` | CF 账户 ID |
| `CF_API_TOKEN` | CF API Token |
| `CF_VECTORIZE_INDEX` | 向量索引名称 |

**2. 自定义系统提示词**
| 变量名 | 说明 |
| :--- | :--- |
| `SYSTEM_PROMPT_OVERRIDE` | **高玩专用**。覆盖默认的 Prompt，用于调整评分标准或摘要风格。 |

**3. 消息通知**
| 变量名 | 说明 |
| :--- | :--- |
| `FEISHU_NOTIFY_TABLE_ID` | **强烈推荐**。配置“提醒记录表”ID，开启错误日志推送。 |

---

## ❓ 常见问题 (FAQ)

**Q: 为什么运行一周后突然报错？**
A: 如果你使用的是 **iFlow**，大概率是因为 API Key 超过了 7 天有效期。请登录 iFlow 官网重置 Key，并在 GitHub Secrets 中更新 `IFLOW_API_KEY`。

**Q: 401/403 错误？**
A: 99% 是因为飞书应用**没有点击“发布”**，或者没有开启“多维表格”权限。

**Q: 如何使用 OneAPI / 中转服务？**
A: 配置 `LLM_PROVIDER=openai`，然后在 `OPENAI_BASE_URL` 中填入你的中转地址（例如 `https://api.one-api.com/v1`），Key 填中转的 Key 即可。

---
*Created by [Your Name] - 让信息获取更高效。*
