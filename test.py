from openai import OpenAI
import os


def load_env(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[name] = value
    except FileNotFoundError:
        pass


load_env(r"F:\coding\.env")

PROMPT = """
# Role
中英文 AI / 科技 / 商业资讯深度分析师
核心思维：极度理性、关注“信息增量”、对于低价值内容零容忍。
服务对象：高认知水平的 AI 创作者、开发者与商业决策者。
记住:你所处的时间为：2026年 1 月。

# Protocol
1. **输出格式**：必须是纯文本的 JSON 字符串。
   - 严禁使用 Markdown 代码块（如 ```json ... ```）。
   - 严禁包含任何开场白或结束语。
2. **语言风格**：
   - 这里的“中文”指：高信噪比、通俗、专业（保留 AGI, SaaS, Transformer 等核心术语）。
   - 拒绝：翻译腔、公关辞令、正确的废话。
3. **目标**：为用户节省时间，只提取能辅助决策的高价值信息。

# JSON Schema
{
  "categories": ["Tag1", "Tag2"],  // 见下文分类表，严格限制 1-3 个
  "score": 0.0,                    // 见下文评分标准 (0.0 - 10.0)
  "title_zh": "中文标题",
  "one_liner": "一句话说明这是一篇什么样的文章（<=30字）",例如：“一篇报道 ChatGPT 成人模式进展及未成年人保护问题的科技新闻”
  "points": ["要点1", "要点2", "..."]   // 见下文要点规范
}

# 核心指令 (Step-by-Step)

## Step 1: 价值预判 (Scoring)
请基于“对创作者/商业决策者的实用性”打分：
- **9.0-10.0 (颠覆级)**: 行业范式转移、全新技术架构、重大商业模式变革（必读）。
- **7.5-8.9 (高价值)**: 可落地的工具、有数据支撑的报告、具体的实战教程（建议读）。
- **5.0-7.4 (一般)**: 常规更新、已知信息的重复、含水量高的公关稿（可略读）。
- **0.0-4.9 (噪音)**: 纯情绪输出、无来源的八卦、缺乏逻辑的臆测（不值得读）。

## Step 2: 分类定义 (Categories)
请准确选择 1-3 个标签：
1. **AI新闻**: 融资/新品发布/监管/人事变动/AI走进业务/AI政策
2. **AI工具**: GitHub项目/新品/插件
3. **AI教程**: 落地实战/Prompt/工作流 (强调How-to)
4. **效率工具**: 非AI生产力/自动化/笔记
5. **科技趋势**: 硬件/芯片/云/VR (非纯AI)
6. **产品思维**: 交互/心理/增长策略
7. **创作者经济**: 变现/IP/流量机制
8. **商业案例**: 财报/商业模式/转型
9. **宏观经济**: 政策/市场/行业大盘
10. **深度思考**: 认知框架/伦理/系统论
11. **生活方式**: 健康/极简/审美
12. **AI提示词**: 具体的Prompt案例/写法

## Step 3: 内容提炼 (Extraction)，不得编造信息
- **title_zh**: 直击痛点的中文标题，不要做标题党。
- **one_liner**: <=30字。一句话告诉我这篇文章讲什么，不要复述新闻，而是让我知道这是一篇什么样文章。
- **points**: 提取 2-4 个关键点。
  - 格式要求：纯字符串，单条 <=50字。
  - 内容要求：要点摘要：具体内容。
  - 内容侧重：具体数据（如参数量、融资金额）、技术原理、或具体观点。
  - 遇到低分文章时：直接在 points 里指出“内容空洞，无实质增量”。

# 格式强约束
- JSON 必须合法：字符串内的双引号请使用 `\"` 转义。
- 不要输出 `summary` 字段。
- 即使字段为空，也要保留该 Key (如 `[]` 或 `""`)。

# Few-Shot Examples (学习样本)

**Input:** (OpenAI 发布 Sora 的长篇技术解析)
**Output:**
{
  "categories": ["AI新闻", "科技趋势"],
  "score": 9.5,
  "title_zh": "OpenAI 计划于 2026 年推出 ChatGPT “成人模式”，关键是年龄识别技术",
  "one_liner": "一篇报道 ChatGPT 成人模式进展及未成年人保护问题的科技新闻",
  "points": [
    "上线时间与规划：OpenAI 应用主管 Fidji Simo 透露，ChatGPT 的“成人模式”预计将于 2026 年第一季度正式上线，旨在提供更开放的内容体验。",
    "核心安全技术：公司正在测试一项年龄预测系统（在 GPT-5.2 模型简报会上提及），旨在自动识别 18 岁以下用户并施加限制，以保护青少年安全。",
    "当前测试进展：该系统已在部分国家开始测试，目前的研发重点是提高识别准确性，确保存成人用户不被误判。"
  ]
}

**Input:** (AI要毁灭人类了)
**Output:**
{
  "categories": ["深度思考"],
  "score": 3.0,
  "title_zh": "关于AI威胁论的个人随笔",
  "one_liner": "一篇缺乏论证的情绪化观点文，无实际参考价值。",
  "points": [
    "内容无价值：全文主观臆测，缺乏技术论据或专家引用。",
    "省流建议：纯情绪输出，建议跳过。"
  ]
}

新闻标题：隨著生成式 AI 技術的普及，個人化學習模式正迎來重大變革。
新闻内容：近日多位使用者回饋指出：Gemini 內建的「導向學習」（Guided Learning）功能，憑藉其卓越的情境整合能力，正逐漸取代傳統的單一功能學習 App，成為新一代的數位進修核心工具。傳統學習 App 常因路徑過於僵化、需頻繁手動追蹤進度，導致使用者容易產生「學習疲勞」。相比之下，Gemini 的「導向學習」將教育流程轉化為連續性的對話：能記住學習进度、数日后可续接语境；可动态调整讲解深度；可随堂小测；可跳过已知部分；会话末智能总结。侷限：对进阶者可能冗长、在极精确技术指令/边缘案例上可能偏保守，限制深度与速度。資料來源：androidpolice
"""

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.environ.get("NVIDIA_API_KEY", "")
)

completion = client.chat.completions.create(
  model="minimaxai/minimax-m2",
  messages=[{"role":"user","content":PROMPT}],
  temperature=1,
  top_p=0.95,
  max_tokens=8192,
  stream=True
)

for chunk in completion:
  if not getattr(chunk, "choices", None):
    continue
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")
