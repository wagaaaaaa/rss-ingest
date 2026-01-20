# -*- coding: utf-8 -*-
import datetime as dt
import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional

import requests

import config
from feishu_client import create_bitable_record, get_tenant_access_token, list_bitable_records, update_bitable_record_fields
from rss_parser import build_item_key, entry_published_ts, entry_text_content, fetch_feed

FAILED_CATEGORIES = {"调用失败", "调用异常", "解析失败", "JSON解析失败", "异常"}

SYSTEM_PROMPT = """
# Role
中英文 AI / 科技 / 商业资讯深度分析师
核心思维：极度理性、关注“信息增量”、对于低价值内容零容忍
服务对象：高认知水平的 AI 创作者、开发者与商业决策者
记住:你所处的时间为：2026年1月

# Protocol
1. **输出格式**：必须是纯文本的 JSON 字符串
   - 严禁使用 Markdown 代码块（如```json ... ```）
   - 严禁包含任何开场白或结束语
2. **语言风格**
   - 这里的“中文”指：高信息密度、通俗、专业（保留 AGI, SaaS, Transformer 等核心术语）
   - 拒绝：翻译腔、公关辞令、正确的废话
3. **目标**：为用户节省时间，只提取能辅助决策的高价值信息

# JSON Schema
{
  "categories": ["Tag1", "Tag2"],
  "score": 0.0,
  "title_zh": "中文标题",
  "one_liner": "一句话说明这是一篇什么样的文章（<=30字）",
  "points": ["要点1", "要点2", "..."]
}

# 核心指令 (Step-by-Step)

## Step 1: 价值评分(Scoring)
请基于“对创作者/商业决策者的实用性”打分：
- **9.0-10.0 (颠覆级)**: 行业范式转移、全新技术架构、重大商业模式变革（必读）
- **7.5-8.9 (高价值)**: 可落地的工具、有数据支撑的报告、具体的实战教程（建议读）
- **5.0-7.4 (一般)**: 常规更新、已知信息的重复、含水量高的公关稿（可略读）
- **0.0-4.9 (噪音)**: 纯情绪输出、无来源的八卦、缺乏逻辑的臆测（不值得读）

## Step 2: 分类定义 (Categories)
请选择 1-3 个标签：
1. **AI新闻**: 融资/新品发布/监管/人事变动/AI走进业务/AI政策
2. **AI工具**: GitHub项目/新品/插件
3. **AI教程**: 落地实战/Prompt/工作流(强调How-to)
4. **效率工具**: 非AI生产力/自动化/笔记
5. **科技趋势**: 硬件/芯片/AR/VR (非纯AI)
6. **产品思维**: 交互/心理/增长策略
7. **创作者经济**: 变现/IP/流量机制
8. **商业案例**: 财报/商业模式/转型
9. **宏观经济**: 政策/市场/行业大盘
10. **深度思考**: 认知框架/伦理/系统思考
11. **生活方式**: 健康/极简/审美
12. **AI提示词**: 具体的Prompt案例/写法

## Step 3: 内容提炼 (Extraction)
- **title_zh**: 直击痛点的中文标题，不要做标题党
- **one_liner**: <=30字。一句话告诉我这篇文章讲什么
- **points**: 提取 2-4 个关键点
  - 格式要求：纯字符串，单条 <=50字
  - 内容要求：要点摘要：具体内容
  - 必须包含：具体数据（如参数量、融资金额）、技术原理、或具体观点
  - 遇到低分文章时：直接在 points 里指出“内容空洞，无实质增量”

# 格式强约束
- JSON 必须合法：字符串内的双引号请使用 \" 转义
- 不要输出 summary 字段
- 即使字段为空，也要保留该 Key (如`[]` 或 `""`)
"""


def log(msg: str) -> None:
    print(msg, flush=True)


def clean_feishu_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                t = item.get("text")
                parts.append(t if isinstance(t, str) else str(item))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(value)


def is_checked(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "yes", "y", "1", "checked", "on"):
            return True
        if s in ("false", "no", "n", "0", ""):
            return False
        return True
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return True
    return bool(value)


def parse_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        s = str(value).strip()
        return int(s) if s else None
    except Exception:
        return None


def parse_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        return float(s) if s else None
    except Exception:
        return None


def parse_ts_ms(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    fmts = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in fmts:
        try:
            dt_obj = dt.datetime.strptime(s, fmt)
            return int(dt_obj.timestamp() * 1000)
        except Exception:
            continue
    return 0


def clean_html_to_text(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p\s*>", "\n", html)
    html = re.sub(r"(?i)</div\s*>", "\n", html)
    html = re.sub(r"(?i)</li\s*>", "\n", html)
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_single_select(value: Any, allowed: set, default: str = "") -> str:
    s = clean_feishu_value(value).strip()
    return s if s in allowed else default


def derive_fetch_status(exc: Exception) -> str:
    msg = str(exc).lower()
    if "timeout" in msg or "timed out" in msg:
        return config.FETCH_STATUS_TIMEOUT
    if "parse" in msg:
        return config.FETCH_STATUS_PARSE_ERROR
    if "http" in msg:
        return config.FETCH_STATUS_HTTP_ERROR
    return config.FETCH_STATUS_HTTP_ERROR


def derive_overall_status(consecutive_fail: int, enabled: bool) -> str:
    if not enabled:
        return config.STATUS_IDLE
    if consecutive_fail >= 5:
        return config.STATUS_DEAD
    if consecutive_fail >= 2:
        return config.STATUS_UNSTABLE
    return config.STATUS_OK


def gemini_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY}


def iflow_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.IFLOW_API_KEY}"}


def cf_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"}


def cf_post(url: str, payload: Dict[str, Any], timeout: int, retries: int) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=cf_headers(), json=payload, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.2 * (attempt + 1))
                continue
            data = resp.json()
            if resp.status_code >= 400:
                raise RuntimeError(f"CF HTTP {resp.status_code}: {data}")
            return data
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"CF request failed: {last_err}")


def build_prompt(article: Dict[str, Any]) -> str:
    return f"""{SYSTEM_PROMPT}

现在请你根据上面的要求，分析这篇文章：

标题：{article.get('title','')}

正文（可能包含HTML）：
{article.get('content','')}
"""


def extract_json_object(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = t.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        return t[first:last + 1]
    return t


def analyze_with_gemini(article: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt(article)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_err: Optional[Exception] = None
    for attempt in range(config.GEMINI_RETRIES):
        try:
            resp = requests.post(config.GEMINI_API_URL, headers=gemini_headers(), json=payload, timeout=config.GEMINI_TIMEOUT)
            if resp.status_code in (400, 401, 403):
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}

            raw_json = resp.json()
            parts = raw_json["candidates"][0]["content"]["parts"]
            raw_text = "".join(p.get("text", "") for p in parts).strip()
            json_str = extract_json_object(raw_text)
            result = json.loads(json_str)
            return result
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 + attempt)

    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def _parse_llm_json(raw_text: str) -> Dict[str, Any]:
    json_str = extract_json_object(raw_text)
    return json.loads(json_str)


def analyze_with_iflow(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.IFLOW_API_KEY:
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing IFLOW_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = f"{config.IFLOW_BASE_URL}/chat/completions"
    payload = {
        "model": config.IFLOW_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_err: Optional[Exception] = None
    for attempt in range(config.IFLOW_RETRIES):
        try:
            resp = requests.post(url, headers=iflow_headers(), json=payload, timeout=config.IFLOW_TIMEOUT)
            if resp.status_code in (400, 401, 403):
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}

            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            message = choices[0].get("message") or {}
            raw_text = (message.get("content") or "").strip()
            result = _parse_llm_json(raw_text)
            return result
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 + attempt)

    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_llm(article: Dict[str, Any]) -> Dict[str, Any]:
    provider = config.LLM_PROVIDER
    if provider == "iflow":
        return analyze_with_iflow(article)
    if provider and provider != "gemini":
        log(f"[LLM] unknown provider={provider}, fallback to gemini")
    return analyze_with_gemini(article)


def normalize_points(points: Any) -> List[str]:
    if not isinstance(points, list):
        points = [str(points)]
    normalized: List[str] = []
    for p in points:
        if p is None:
            continue
        s = str(p).strip()
        if not s:
            continue
        s = " ".join(s.splitlines()).strip()
        if s:
            normalized.append(s)
    return normalized


def build_summary(one_liner: str, points: List[str]) -> str:
    if one_liner and points:
        return one_liner + "\n" + "\n".join(f"- {p}" for p in points)
    if one_liner:
        return one_liner
    if points:
        return "\n".join(f"- {p}" for p in points)
    return ""


def build_embedding_text(article: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    title = (analysis.get("title_zh") or article.get("title") or "").strip()
    one_liner = (analysis.get("one_liner") or "").strip()
    points = normalize_points(analysis.get("points") or [])
    summary = build_summary(one_liner, points)
    if summary:
        return f"{title}\n{summary}".strip()
    return title


def cf_embed_text(text: str) -> Optional[List[float]]:
    if not text.strip():
        log("   [Vectorize] empty text, skip embedding")
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/ai/run/{config.CF_EMBEDDING_MODEL}"
    payload = {"text": [text]}
    try:
        data = cf_post(url, payload, timeout=30, retries=3)
    except Exception as exc:
        log(f"   [Vectorize] embedding error: {exc}")
        return None
    result = data.get("result") or {}
    items = result.get("data") or result.get("result") or []
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            emb = first.get("embedding")
            if isinstance(emb, list) and emb:
                return [float(x) for x in emb]
        if isinstance(first, list) and first:
            return [float(x) for x in first]
    log(f"   [Vectorize] embedding response missing data: {data}")
    return None


def vectorize_query(embedding: List[float]) -> Optional[float]:
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/vectorize/v2/indexes/{config.CF_VECTORIZE_INDEX}/query"
    payload = {"vector": embedding, "topK": config.CF_VECTORIZE_TOP_K}
    try:
        data = cf_post(url, payload, timeout=20, retries=3)
    except Exception as exc:
        log(f"   [Vectorize] query error: {exc}")
        return None
    result = data.get("result") or {}
    matches = result.get("matches") or []
    if not matches:
        return 0.0
    best = matches[0]
    score = best.get("score")
    if isinstance(score, (int, float)):
        return float(score)
    distance = best.get("distance")
    if isinstance(distance, (int, float)) and config.CF_VECTORIZE_METRIC == "cosine":
        return 1.0 - float(distance)
    return None


def vectorize_upsert(item_key: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
    vec_id = hashlib.sha256(item_key.encode("utf-8", errors="ignore")).hexdigest()
    metadata = dict(metadata)
    metadata["item_key"] = item_key
    url = f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}/vectorize/v2/indexes/{config.CF_VECTORIZE_INDEX}/upsert"
    payload = {"vectors": [{"id": vec_id, "values": embedding, "metadata": metadata}]}
    try:
        cf_post(url, payload, timeout=20, retries=3)
        return True
    except Exception as exc:
        log(f"   [Vectorize] upsert error: {exc}")
        return False


def normalize_source(record: Dict[str, Any]) -> Dict[str, Any]:
    fields = record.get("fields") or {}
    source_id = record.get("record_id") or ""
    enabled = is_checked(fields.get(config.RSS_FIELD_ENABLED))
    last_fetch_time = parse_ts_ms(fields.get(config.RSS_FIELD_LAST_FETCH_TIME))
    last_item_pub_time = parse_ts_ms(fields.get(config.RSS_FIELD_LAST_ITEM_PUB_TIME))
    consecutive_fail = parse_int(fields.get(config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT)) or 0
    item_id_strategy = normalize_single_select(
        fields.get(config.RSS_FIELD_ITEM_ID_STRATEGY),
        config.ITEM_ID_STRATEGY_OPTIONS,
        config.DEFAULT_ITEM_ID_STRATEGY,
    )

    return {
        "record_id": record.get("record_id"),
        "source_id": source_id,
        "name": clean_feishu_value(fields.get(config.RSS_FIELD_NAME)),
        "feed_url": clean_feishu_value(fields.get(config.RSS_FIELD_FEED_URL)),
        "type": clean_feishu_value(fields.get(config.RSS_FIELD_TYPE)),
        "description": clean_feishu_value(fields.get(config.RSS_FIELD_DESCRIPTION)),
        "enabled": enabled,
        "last_fetch_time": last_fetch_time,
        "last_item_pub_time": last_item_pub_time,
        "last_item_guid": clean_feishu_value(fields.get(config.RSS_FIELD_LAST_ITEM_GUID)),
        "item_id_strategy": item_id_strategy,
        "content_hash_algo": config.DEFAULT_CONTENT_HASH_ALGO,
        "consecutive_fail_count": consecutive_fail,
    }


def should_fetch(source: Dict[str, Any], now_ms: int) -> bool:
    if not source.get("enabled"):
        return False
    interval_min = config.DEFAULT_FETCH_INTERVAL_MIN
    last_fetch = source.get("last_fetch_time") or 0
    if last_fetch <= 0:
        return True
    return now_ms - last_fetch >= interval_min * 60 * 1000


def build_news_fields(article: Dict[str, Any], analysis: Dict[str, Any], item_key: str) -> Dict[str, Any]:
    published = article.get("published")
    if isinstance(published, (int, float)) and published > 0:
        base_ts = published
    else:
        base_ts = time.time()
    published_ts_ms = int(base_ts * 1000)

    raw_title = article.get("title") or "（无标题）"
    title_zh = (analysis.get("title_zh") or "").strip()
    title_text = title_zh if title_zh else raw_title

    score = float(analysis.get("score", 0.0) or 0.0)
    categories = analysis.get("categories") or []
    if not isinstance(categories, list):
        categories = [str(categories)]

    one_liner = (analysis.get("one_liner") or "").strip()
    points = normalize_points(analysis.get("points") or [])
    summary = build_summary(one_liner, points)

    full_content = clean_html_to_text(article.get("content") or "")

    return {
        config.NEWS_FIELD_TITLE: {"text": title_text, "link": article.get("link") or ""},
        config.NEWS_FIELD_SCORE: score,
        config.NEWS_FIELD_CATEGORIES: categories,
        config.NEWS_FIELD_SUMMARY: summary,
        config.NEWS_FIELD_PUBLISHED_MS: published_ts_ms,
        config.NEWS_FIELD_SOURCE: article.get("source") or "未知来源",
        config.NEWS_FIELD_FULL_CONTENT: full_content,
        config.NEWS_FIELD_ITEM_KEY: item_key,
    }


def prefetch_recent_item_keys(tenant_token: str) -> set:
    sort_field = config.NEWS_FIELD_CREATED_TIME or config.NEWS_FIELD_PUBLISHED_MS
    sort = [{"field_name": sort_field, "order": "desc"}]
    records = list_bitable_records(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_NEWS_TABLE_ID,
        tenant_token,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
        page_size=config.NEWS_ITEM_KEY_PREFETCH_LIMIT,
        max_pages=1,
        sort=sort,
    )
    keys = set()
    for record in records:
        fields = record.get("fields") or {}
        raw_key = fields.get(config.NEWS_FIELD_ITEM_KEY)
        key = clean_feishu_value(raw_key).strip()
        if key:
            keys.add(key)
    return keys


def process_source(
    source: Dict[str, Any],
    tenant_token: str,
    existing_keys: set,
) -> None:
    if not source.get("feed_url"):
        return

    now_ms = int(time.time() * 1000)
    if not source.get("enabled"):
        update_bitable_record_fields(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_RSS_TABLE_ID,
            tenant_token,
            source["record_id"],
            {
                config.RSS_FIELD_STATUS: config.STATUS_IDLE,
            },
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
        return

    if not should_fetch(source, now_ms):
        return

    last_item_pub_time = source.get("last_item_pub_time") or 0
    cutoff_ms = last_item_pub_time or (source.get("last_fetch_time") or 0)
    consecutive_fail = source.get("consecutive_fail_count") or 0

    try:
        feed = fetch_feed(source["feed_url"], config.HTTP_TIMEOUT, config.HTTP_RETRIES, headers={"User-Agent": "NewsDataRSS/1.0"})
    except Exception as exc:
        fail_count = consecutive_fail + 1
        status = derive_overall_status(fail_count, True)
        fetch_status = derive_fetch_status(exc)
        update_bitable_record_fields(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_RSS_TABLE_ID,
            tenant_token,
            source["record_id"],
            {
                config.RSS_FIELD_STATUS: status,
                config.RSS_FIELD_LAST_FETCH_STATUS: fetch_status,
                config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT: fail_count,
                config.RSS_FIELD_LAST_FETCH_TIME: now_ms,
            },
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
        log(f"[RSS] fetch failed {source['feed_url']}: {exc}")
        return

    entries = feed.entries or []
    if config.MAX_ENTRIES_PER_FEED and len(entries) > config.MAX_ENTRIES_PER_FEED:
        entries = entries[: config.MAX_ENTRIES_PER_FEED]

    latest_pub_ms = 0
    latest_key = ""
    new_count = 0

    for entry in entries:
        entry_ts = entry_published_ts(entry)
        entry_ts_ms = entry_ts * 1000 if entry_ts else 0
        if entry_ts_ms and cutoff_ms and entry_ts_ms <= cutoff_ms:
            continue

        item_key = build_item_key(entry, source.get("item_id_strategy"), source.get("content_hash_algo"))
        if not item_key:
            continue
        if item_key in existing_keys:
            continue

        article = {
            "title": entry.get("title") or "",
            "content": entry_text_content(entry),
            "link": entry.get("link") or "",
            "published": entry_ts,
            "source": source.get("name") or source.get("feed_url"),
        }

        analysis = analyze_with_llm(article)
        categories = analysis.get("categories") or []
        if isinstance(categories, list) and any(c in FAILED_CATEGORIES for c in categories):
            log(f"[Gemini] skipped due to failure category: {categories}")
            continue

        score = float(analysis.get("score", 0.0) or 0.0)
        if score >= config.FEISHU_MIN_SCORE:
            emb_vec = None
            if config.ENABLE_VECTORIZE_DEDUP:
                embed_text = build_embedding_text(article, analysis)
                emb_vec = cf_embed_text(embed_text)
                if emb_vec:
                    best_sim = vectorize_query(emb_vec)
                    if best_sim is not None and best_sim >= config.CF_VECTORIZE_SIM_THRESHOLD:
                        log(f"[Vectorize] skip similar={best_sim:.3f} title={article.get('title','')}")
                        existing_keys.add(item_key)
                        continue
                else:
                    log("[Vectorize] embedding unavailable, fallback to exact dedup only")

            fields = build_news_fields(article, analysis, item_key)
            ok = create_bitable_record(
                config.FEISHU_APP_TOKEN,
                config.FEISHU_NEWS_TABLE_ID,
                tenant_token,
                fields,
                config.HTTP_TIMEOUT,
                config.HTTP_RETRIES,
            )
            if not ok:
                log(f"[Feishu] create record failed: {article.get('title','')}")
            else:
                if config.ENABLE_VECTORIZE_DEDUP and emb_vec:
                    metadata = {
                        "title": article.get("title") or "",
                        "source": article.get("source") or "",
                        "published": entry_ts or 0,
                    }
                    vectorize_upsert(item_key, emb_vec, metadata)
        existing_keys.add(item_key)
        new_count += 1

        if entry_ts_ms > latest_pub_ms:
            latest_pub_ms = entry_ts_ms
            latest_key = item_key

    update_fields: Dict[str, Any] = {
        config.RSS_FIELD_STATUS: config.STATUS_OK,
        config.RSS_FIELD_LAST_FETCH_STATUS: config.FETCH_STATUS_SUCCESS,
        config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT: 0,
        config.RSS_FIELD_LAST_FETCH_TIME: now_ms,
    }
    if latest_pub_ms:
        update_fields[config.RSS_FIELD_LAST_ITEM_PUB_TIME] = latest_pub_ms
    if latest_key:
        update_fields[config.RSS_FIELD_LAST_ITEM_GUID] = latest_key

    update_bitable_record_fields(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_RSS_TABLE_ID,
        tenant_token,
        source["record_id"],
        update_fields,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )
    log(f"[RSS] {source.get('name') or source.get('feed_url')} new={new_count}")


def main() -> None:
    if config.ENABLE_VECTORIZE_DEDUP:
        missing = []
        if not config.CF_ACCOUNT_ID:
            missing.append("CF_ACCOUNT_ID")
        if not config.CF_API_TOKEN:
            missing.append("CF_API_TOKEN")
        if not config.CF_VECTORIZE_INDEX:
            missing.append("CF_VECTORIZE_INDEX")
        if missing:
            log(f"[Vectorize] disabled, missing: {', '.join(missing)}")
            config.ENABLE_VECTORIZE_DEDUP = False

    tenant_token = get_tenant_access_token(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, config.HTTP_TIMEOUT, config.HTTP_RETRIES)
    records = list_bitable_records(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_RSS_TABLE_ID,
        tenant_token,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )

    sources = [normalize_source(r) for r in records if r.get("record_id")]
    enabled_sources = [s for s in sources if s.get("enabled")]
    log(f"[RSS] sources total={len(sources)} enabled={len(enabled_sources)}")
    try:
        existing_keys = prefetch_recent_item_keys(tenant_token)
        log(f"[Dedup] prefetched keys: {len(existing_keys)}")
    except Exception as exc:
        log(f"[Dedup] prefetch failed: {exc}")
        existing_keys = set()
    for source in enabled_sources:
        process_source(source, tenant_token, existing_keys)


if __name__ == "__main__":
    main()
