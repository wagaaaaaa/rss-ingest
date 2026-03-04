from openai import OpenAI
import os
import sys
import time
import random
import json
import httpx


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


# 改成你的 .env 路径
load_env(r"F:\coding\.env")

API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError("NVIDIA_API_KEY 未设置。请在 F:\\coding\\.env 或系统环境变量中配置 NVIDIA_API_KEY=...")

BASE_URL = "https://integrate.api.nvidia.com/v1"

# 关键：要带命名空间前缀
MODEL = "mistralai/mistral-large-3-675b-instruct-2512"

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

title：Conversational AI doesn’t understand users — 'Intent First' architecture does
content：The modern customer has just one need that matters: Getting the thing they want when they want it. The old standard RAG model embed+retrieve+LLM misunderstands intent, overloads context and misses freshness, repeatedly sending customers down the wrong paths. Instead, intent-first architecture uses a lightweight language model to parse the query for intent and context, before delivering to the most relevant content sources (documents, APIs, people). Enterprise AI is a speeding train headed for a cliff. Organizations are deploying LLM-powered search applications at a record pace, while a fundamental architectural issue is setting most up for failure. A recent Coveo study revealed that 72% of enterprise search queries fail to deliver meaningful results on the first attempt, while Gartner also predicts that the majority of conversational AI deployments have been falling short of enterprise expectations. The problem isn’t the underlying models. It’s the architecture around them. After designing and running live AI-driven customer interaction platforms at scale, serving millions of customer and citizen users at some of the world’s largest telecommunications and healthcare organizations, I’ve come to see a pattern. It’s the difference between successful AI-powered interaction deployments and multi-million-dollar failures. It’s a cloud-native architecture pattern that I call Intent-First. And it’s reshaping the way enterprises build AI-powered experiences. The $36 pillion problem Gartner projects the global conversational AI market will balloon to $36 billion by 2032. Enterprises are scrambling to get a slice. The demos are irresistible. Plug your LLM into your knowledge base, and suddenly it can answer customer questions in natural language.Magic. Then production happens. A major telecommunications provider I work with rolled out a RAG system with the expectation of driving down the support call rate. Instead, the rate increased. Callers tried AI-powered search, were provided incorrect answers with a high degree of confidence and called customer support angrier than before. This pattern is repeated over and over. In healthcare, customer-facing AI assistants are providing patients with formulary information that’s outdated by weeks or months. Financial services chatbots are spitting out answers from both retail and institutional product content. Retailers are seeing discontinued products surface in product searches. The issue isn’t a failure of AI technology. It’s a failure of architecture Why standard RAG architectures fail The standard RAG pattern — embedding the query, retrieving semantically similar content, passing to an LLM —works beautifully in demos and proof of concepts. But it falls apart in production use cases for three systematic reasons: 1. The intent gapIntent is not context. But standard RAG architectures don’t account for this. Say a customer types “I want to cancel” What does that mean? Cancel a service? Cancel an order? Cancel an appointment? During our telecommunications deployment, we found that 65% of queries for “cancel” were actually about orders or appointments, not service cancellation. The RAG system had no way of understanding this intent, so it consistently returned service cancellation documents. Intent matters. In healthcare, if a patient is typing “I need to cancel” because they&#x27;re trying to cancel an appointment, a prescription refill or a procedure, routing them to medication content from scheduling is not only frustrating — it&#x27;s also dangerous. 2. Context flood Enterprise knowledge and experience is vast, spanning dozens of sources such as product catalogs, billing, support articles, policies, promotions and account data. Standard RAG models treat all of it the same, searching all for every query. When a customer asks “How do I activate my new phone,” they don’t care about billing FAQs, store locations or network status updates. But a standard RAG model retrieves semantically similar content from every source, returning search results that are a half-steps off the mark. 3. Freshness blindspot Vector space is timeblind. Semantically, last quarter’s promotion is identical to this quarter’s. But presenting customers with outdated offers shatters trust. We linked a significant percentage of customer complaints to search results that surfaced expired products, offers, or features. The Intent-First architecture pattern The Intent-First architecture pattern is the mirror image of the standard RAG deployment. In the RAG model, you retrieve, then route. In the Intent-First model, you classify before you route or retrieve. Intent-First architectures use a lightweight language model to parse a query for intent and context, before dispatching to the most relevant content sources (documents, APIs, agents). Comparison: Intent-first vs standard RAGCloud-native implementationThe Intent-First pattern is designed for cloud-native deployment, leveraging microservices, containerization and elastic scaling to handle enterprise traffic patterns. Intent classification serviceThe classifier determines user intent before any retrieval occurs: ALGORITHM: Intent Classification INPUT: user_query (string) OUTPUT: intent_result (object) 1. PREPROCESS query (normalize, expand contractions) 2. CLASSIFY using transformer model: - primary_intent ← model.predict(query) - confidence ← model.confidence_score() 3. IF confidence &lt; 0.70 THEN - RETURN { requires_clarification: true, suggested_question: generate_clarifying_question(query) } 4. EXTRACT sub_intent based on primary_intent: - IF primary = &quot;ACCOUNT&quot; → check for ORDER_STATUS, PROFILE, etc. - IF primary = &quot;SUPPORT&quot; → check for DEVICE_ISSUE, NETWORK, etc. - IF primary = &quot;BILLING&quot; → check for PAYMENT, DISPUTE, etc. 5. DETERMINE target_sources based on intent mapping: - ORDER_STATUS → [orders_db, order_faq] - DEVICE_ISSUE → [troubleshooting_kb, device_guides] - MEDICATION → [formulary, clinical_docs] (healthcare) 6. RETURN { primary_intent, sub_intent, confidence, target_sources, requires_personalization: true/false } Context-aware retrieval serviceOnce intent is classified, retrieval becomes targeted: ALGORITHM: Context-Aware Retrieval INPUT: query, intent_result, user_context OUTPUT: ranked_documents 1. GET source_config for intent_result.sub_intent: - primary_sources ← sources to search - excluded_sources ← sources to skip - freshness_days ← max content age 2. IF intent requires personalization AND user is authenticated: - FETCH account_context from Account Service - IF intent = ORDER_STATUS: - FETCH recent_orders (last 60 days) - ADD to results 3. BUILD search filters: - content_types ← primary_sources only - max_age ← freshness_days - user_context ← account_context (if available) 4. FOR EACH source IN primary_sources: - documents ← vector_search(query, source, filters) - ADD documents to results 5. SCORE each document: - relevance_score ← vector_similarity × 0.40 - recency_score ← freshness_weight × 0.20 - personalization_score ← user_match × 0.25 - intent_match_score ← type_match × 0.15 - total_score ← SUM of above 6. RANK by total_score descending 7. RETURN top 10 documents Healthcare-specific considerationsIn healthcare deployments, the Intent-First pattern includes additional safeguards: Healthcare intent categories: Clinical: Medication questions, symptoms, care instructions Coverage: Benefits, prior authorization, formulary Scheduling: Appointments, provider availability Billing: Claims, payments, statements Account: Profile, dependents, ID cards Critical safeguard: Clinical queries always include disclaimers and never replace professional medical advice. The system routes complex clinical questions to human support. Handling edge casesThe edge cases are where systems fail. The Intent-First pattern includes specific handlers: Frustration detection keywords: Anger: &quot;terrible,&quot; &quot;worst,&quot; &quot;hate,&quot; &quot;ridiculous&quot; Time: &quot;hours,&quot; &quot;days,&quot; &quot;still waiting&quot; Failure: &quot;useless,&quot; &quot;no help,&quot; &quot;doesn&#x27;t work&quot; Escalation: &quot;speak to human,&quot; &quot;real person,&quot; &quot;manager&quot; When frustration is detected, skip search entirely and route to human support. Cross-industry applicationsThe Intent-First pattern applies wherever enterprises deploy conversational AI over heterogeneous content: Industry Intent categories Key benefit Telecommunications Sales, Support, Billing, Account, Retention Prevents &quot;cancel&quot; misclassification Healthcare Clinical, Coverage, Scheduling, Billing Separates clinical from administrative Financial services Retail, Institutional, Lending, Insurance Prevents context mixing Retail Product, Orders, Returns, Loyalty Ensures promotional freshness ResultsAfter implementing Intent-First architecture across telecommunications and healthcare platforms: Metric Impact Query success rate Nearly doubled Support escalations Reduced by more than half Time to resolution Reduced approximately 70% User satisfaction Improved roughly 50% Return user rate More than doubled The return user rate proved most significant. When search works, users come back. When it fails, they abandon the channel entirely, increasing costs across all other support channels. The strategic imperativeThe conversational AI market will continue to experience hyper growth. But enterprises that build and deploy typical RAG architectures will continue to fail … repeatedly. AI will confidently give wrong answers, users will abandon digital channels out of frustration and support costs will go up instead of down. Intent-First is a fundamental shift in how enterprises need to architect and build AI-powered customer conversations. It’s not about better models or more data. It’s about understanding what a user wants before you try to help them. The sooner an organization realizes this as an architectural imperative, the sooner they will be able to capture the efficiency gains this technology is supposed to enable. Those that don’t will be debugging why their AI investments haven’t been producing expected business outcomes for many years to come. The demo is easy. Production is hard. But the pattern for production success is clear: Intent First. Sreenivasa Reddy Hulebeedu Reddy is a lead software engineer and enterprise architect

"""


def make_client() -> OpenAI:
    # 给足超时 + keepalive，减少 streaming 被中途掐断
    timeout = httpx.Timeout(connect=20.0, read=300.0, write=60.0, pool=60.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
    http_client = httpx.Client(timeout=timeout, limits=limits)

    return OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        http_client=http_client,
    )


def list_models(client: OpenAI) -> None:
    # 只输出到 stderr，避免污染你 stdout 的“纯输出”
    try:
        data = client.models.list()
        ids = []
        for m in getattr(data, "data", []) or []:
            mid = getattr(m, "id", None)
            if mid:
                ids.append(mid)
        ids.sort()
        print(json.dumps({"models": ids}, ensure_ascii=False, indent=2), file=sys.stderr)
    except Exception as e:
        print(f"[warn] list models failed: {type(e).__name__}: {e}", file=sys.stderr)


def request_once(client: OpenAI, stream: bool):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.15,
        top_p=0.95,
        max_tokens=4096,  # 先别 8192，太长更容易中途被网关断开
        seed=42,
        stream=stream,
    )


def run_with_retry(max_retries: int = 4) -> None:
    client = make_client()

    # 可选：python test.py --list-models
    if "--list-models" in sys.argv:
        list_models(client)
        return

    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            stream = request_once(client, stream=True)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    sys.stdout.write(delta.content)
                    sys.stdout.flush()
            sys.stdout.write("\n")
            sys.stdout.flush()
            return

        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.HTTPError) as e:
            last_err = e
            print(f"[warn] streaming failed (attempt {attempt}/{max_retries}): {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(min(2 ** attempt, 10) + random.random())

        except Exception as e:
            # 重点：如果又遇到 404，这里直接提示你怎么排查
            msg = f"{type(e).__name__}: {e}"
            print(f"[warn] request failed: {msg}", file=sys.stderr)
            if "404" in msg:
                print("[hint] 404 通常是模型名不对或账号没权限。先跑：python test-mistral.py --list-models 看你能用哪些模型。", file=sys.stderr)
            raise

    print("[warn] streaming keeps failing, fallback to non-streaming...", file=sys.stderr)

    # fallback 非流式
    resp = request_once(client, stream=False)
    raw = (resp.choices[0].message.content or "").strip()
    sys.stdout.write(raw + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    run_with_retry(max_retries=4)
