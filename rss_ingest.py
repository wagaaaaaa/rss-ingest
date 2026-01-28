# -*- coding: utf-8 -*-
import datetime as dt
import hashlib
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional

import requests

import config
from feishu_client import (
    create_bitable_record,
    create_bitable_record_with_id,
    get_tenant_access_token,
    list_bitable_records,
    update_bitable_record_fields,
)
from rss_parser import build_item_key, entry_published_ts, entry_text_content, fetch_feed

FAILED_CATEGORIES = {"调用失败", "调用异常", "解析失败", "JSON解析失败", "异常"}

SYSTEM_PROMPT = """
# Role
中英文 AI / 科技 / 商业资讯深度分析师
核心思维：极度理性、关注“信息增量”、对于低价值内容零容忍。
服务对象：高认知水平的 AI 创作者、开发者与商业决策者。
# Protocol
1. **输出格式**：必须是纯文本的 JSON 字符串。
   - 严禁使用 Markdown 代码块（如 ```json ... ```）。
   - 严禁包含任何开场白或结束语。
2. **语言风格**：
   - 这里的“中文”指：高信噪比、通俗、专业（保留 AGI, SaaS, Transformer 等核心术语）。
   - 拒绝：翻译腔、公关辞令、正确的废话。
3. **目标**：为用户节省时间，只提取能辅助决策的高价值信息。
4. **【核心约束】零外部注入**：
   - **封闭原则**：将提供的文章视为世界上唯一的信息来源。
   - **严禁脑补**：绝对禁止引入原文未提及的外部知识（特别是具体价格、版本号、未提及的竞品数据），即使这些信息是真实的，只要原文没写，就绝不能出现在输出中。

# JSON Schema
{
  "categories": ["Tag1", "Tag2"],  // 见下文分类表，严格限制 1-3 个
  "score": 0.0,                    // 见下文评分标准 (0.0 - 10.0)
  "title_zh": "中文标题",
  "one_liner": "一句话说明这是一篇什么样的文章（<=30字）(例如：一篇报道 ChatGPT 成人模式进展及未成年人保护问题的科技新闻)",
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
"""

if config.SYSTEM_PROMPT_OVERRIDE:
    SYSTEM_PROMPT = config.SYSTEM_PROMPT_OVERRIDE

FEATURED_PROMPT_DEFAULT = """
# Role
你是一个服务于“超级个体”和“一人公司”的商业效率顾问。你的客户关注如何利用 AI 工具降低成本、提高产出、获取流量和变现，而不关心底层技术实现。

# Task
分析输入的一组资讯，筛选出对“一人公司”运营最有价值的信息。

# Screening Logic (三层漏斗)
1. **✅ 必选 (High Value - 应用与SOP):**
   - **SOP 化:** 包含可直接复制的工作流、提示词框架 (Prompt Framework)、自动化方案。
   - **业务红利:** 新的流量机会 (如平台算法变更)、新的变现模式、极低成本的获客/生产工具。
   - **实用技巧:** 能立即提升 AI 输出质量的非代码技巧 (如“煤气灯提示法”)。
   - **商业警示:** 直接影响个体户账号安全、合规性或资金流的风险。

2. **❌ 必删 (Reject - 纯技术与噪音):**
   - **开发者视角:** 纯代码实现 (除非是低代码)、架构争论、协议漏洞细节。
   - **企业级新闻:** 大厂并购、高管变动、财报分析 (除非涉及价格战)。
   - **宏观噪音:** 政治新闻、学术论文、概念性发布会 (无实物)。

# Output Format
{
  "featured_ids": ["record_id_1", "record_id_2"]
}
"""


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = msg.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe, flush=True)


def collect_queue_items(items: Iterable[dict], existing_keys: set) -> list:
    out = []
    for item in items:
        key = item.get("item_key")
        if not key or key in existing_keys:
            continue
        out.append(item)
    return out


def render_progress(done: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "0/0 [" + "".ljust(width, ".") + "]"
    filled = int(width * done / total)
    return f"{done}/{total} [" + "#" * filled + "." * (width - filled) + "]"


ROOT_CAUSE_RECORDED = False
NOTIFY_TENANT_TOKEN: Optional[str] = None


def set_notify_tenant_token(token: str) -> None:
    global NOTIFY_TENANT_TOKEN
    NOTIFY_TENANT_TOKEN = token


def truncate_text(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def collect_queue_items(items: Iterable[dict], existing_keys: set) -> list:
    out = []
    for item in items:
        key = item.get("item_key")
        if not key or key in existing_keys:
            continue
        out.append(item)
    return out


def build_plain_notice(error_type: str) -> str:
    if error_type == "auth":
        return "鉴权失败：API Key 无效/过期/权限不足，请更新后重试。"
    if error_type == "rate_limit":
        return "触发限流或配额不足：请降低频率或检查配额。"
    if error_type == "server_error":
        return "上游服务异常：请稍后重试。"
    if error_type == "timeout":
        return "网络超时：请检查网络/代理设置。"
    if error_type == "parse_error":
        return "输出格式异常：请检查提示词或更换模型。"
    if error_type == "config":
        return "关键配置缺失：请检查 Secrets/环境变量是否完整。"
    return "未知错误：请查看详情并排查配置。"

def render_progress(done: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "0/0 [" + "".ljust(width, ".") + "]"
    filled = int(width * done / total)
    return f"{done}/{total} [" + "#" * filled + "." * (width - filled) + "]"



def notify_root_cause(event: str, detail: str, error_type: str = "unknown") -> None:
    global ROOT_CAUSE_RECORDED
    if ROOT_CAUSE_RECORDED:
        return
    ROOT_CAUSE_RECORDED = True

    if not config.FEISHU_NOTIFY_TABLE_ID:
        log("[Notify] skipped: missing FEISHU_NOTIFY_TABLE_ID")
        return
    if not NOTIFY_TENANT_TOKEN:
        log("[Notify] skipped: missing tenant token")
        return

    plain_text = build_plain_notice(error_type)
    fields = {
        config.NOTIFY_FIELD_EVENT: event,
        config.NOTIFY_FIELD_DETAIL: truncate_text(detail.strip() or event),
        config.NOTIFY_FIELD_PLAIN: plain_text,
        config.NOTIFY_FIELD_TRIGGER_TIME: int(time.time() * 1000),
        config.NOTIFY_FIELD_NOTIFIED: False,
    }
    ok = create_bitable_record(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_NOTIFY_TABLE_ID,
        NOTIFY_TENANT_TOKEN,
        fields,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )
    if not ok:
        log("[Notify] create record failed")


def notify_auth_failure(service: str, detail: str) -> None:
    notify_root_cause(f"{service} 鉴权失败", detail, "auth")


def notify_rate_limit(service: str, detail: str) -> None:
    notify_root_cause(f"{service} 请求失败", detail, "rate_limit")


def notify_server_error(service: str, detail: str) -> None:
    notify_root_cause(f"{service} 请求失败", detail, "server_error")


def notify_timeout(service: str, detail: str) -> None:
    notify_root_cause(f"{service} 请求失败", detail, "timeout")


def notify_parse_error(service: str, detail: str) -> None:
    notify_root_cause(f"{service} 输出解析失败", detail, "parse_error")


def notify_config_missing(detail: str) -> None:
    notify_root_cause("关键配置缺失", detail, "config")


def response_snippet(resp: requests.Response) -> str:
    try:
        text = resp.text or ""
    except Exception:
        return f"HTTP {resp.status_code}"
    return f"HTTP {resp.status_code}: {truncate_text(text.strip(), 300)}"


def _post_with_retries(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int,
    retries: int,
    service: str,
    parse_text,
) -> Optional[str]:
    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code in (401, 403):
                notify_auth_failure(service, response_snippet(resp))
                return None
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return None
            try:
                return parse_text(resp)
            except Exception as exc:
                notify_parse_error(service, str(exc))
                return None
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit(service, last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error(service, last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout(service, str(last_err) if last_err else "timeout")
    return None


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


def gemini_api_url(model_name: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"


def iflow_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.IFLOW_API_KEY}"}


def openai_headers(api_key: str) -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def deepseek_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"}


def zhipu_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.ZHIPU_API_KEY}"}


def nvidia_headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.NVIDIA_API_KEY}"}


def cf_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"}


def cf_post(url: str, payload: Dict[str, Any], timeout: int, retries: int) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=cf_headers(), json=payload, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            data = resp.json()
            if resp.status_code in (401, 403):
                notify_auth_failure("Cloudflare", f"CF {response_snippet(resp)}")
            if resp.status_code >= 400:
                raise RuntimeError(f"CF HTTP {resp.status_code}: {data}")
            return data
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)
    if last_status_type == "rate_limit":
        notify_rate_limit("Cloudflare", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("Cloudflare", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("Cloudflare", str(last_err) if last_err else "timeout")
    raise RuntimeError(f"CF request failed: {last_err}")


def build_prompt(article: Dict[str, Any]) -> str:
    china_tz = dt.timezone(dt.timedelta(hours=8))
    now = dt.datetime.now(china_tz)
    return f"""{SYSTEM_PROMPT}

你所处的时间为：{now.year}年{now.month:02d}月

title：{article.get('title','')}
content：{article.get('content','')}
"""


def build_featured_prompt(items: List[Dict[str, str]]) -> str:
    prompt = (config.FEATURED_PROMPT or "").strip() or FEATURED_PROMPT_DEFAULT
    payload = {"items": items}
    return f"{prompt}\n\n# Input\n{json.dumps(payload, ensure_ascii=False)}"


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


def parse_llm_json(raw_text: str, service: str) -> Optional[Dict[str, Any]]:
    json_str = extract_json_object(raw_text)
    if not json_str:
        notify_parse_error(service, "empty json")
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        notify_parse_error(service, str(exc))
        return None
 
def _post_with_retries(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int,
    retries: int,
    service: str,
    parse_text,
) -> Optional[str]:
    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code in (401, 403):
                notify_auth_failure(service, response_snippet(resp))
                return None
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return None
            try:
                return parse_text(resp)
            except Exception as exc:
                notify_parse_error(service, str(exc))
                return None
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit(service, last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error(service, last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout(service, str(last_err) if last_err else "timeout")
    return None
def call_featured_llm(prompt: str) -> Optional[str]:
    provider = config.LLM_PROVIDER
    service = f"Featured:{provider}"
    known = {"openai", "gemini", "iflow", "deepseek", "zhipu", "nvidia"}
    if not provider:
        provider = "gemini"
        service = f"Featured:{provider}"
    elif provider not in known:
        log(f"[LLM] unknown provider={provider}, fallback to gemini")
        provider = "gemini"
        service = f"Featured:{provider}"

    if provider == "openai":
        if not config.OPENAI_API_KEY:
            notify_auth_failure("OpenAI", "missing OPENAI_API_KEY")
            return None
        url = f"{config.OPENAI_BASE_URL}/responses"
        headers = openai_headers(config.OPENAI_API_KEY)
        payload = {"model": config.OPENAI_MODEL, "input": prompt}

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            if isinstance(data.get("output_text"), str):
                return data.get("output_text", "")
            outputs = data.get("output") or []
            parts: List[str] = []
            if isinstance(outputs, list):
                for item in outputs:
                    if isinstance(item, dict):
                        if isinstance(item.get("text"), str):
                            parts.append(item["text"])
                        content = item.get("content") or []
                        if isinstance(content, list):
                            for piece in content:
                                if isinstance(piece, dict) and isinstance(piece.get("text"), str):
                                    parts.append(piece["text"])
            return "".join(parts)

        return _post_with_retries(url, headers, payload, config.OPENAI_TIMEOUT, config.OPENAI_RETRIES, service, parse_text)

    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            notify_auth_failure("Gemini", "missing GEMINI_API_KEY")
            return None
        url = gemini_api_url(config.GEMINI_MODEL_NAME_PRO)
        headers = gemini_headers()
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()

        return _post_with_retries(url, headers, payload, config.GEMINI_TIMEOUT, config.GEMINI_RETRIES, service, parse_text)

    if provider == "iflow":
        if not config.IFLOW_API_KEY:
            notify_auth_failure("iFlow", "missing IFLOW_API_KEY")
            return None
        url = f"{config.IFLOW_BASE_URL}/chat/completions"
        headers = iflow_headers()
        payload = {"model": config.IFLOW_MODEL, "messages": [{"role": "user", "content": prompt}]}

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        return _post_with_retries(url, headers, payload, config.IFLOW_TIMEOUT, config.IFLOW_RETRIES, service, parse_text)

    if provider == "deepseek":
        if not config.DEEPSEEK_API_KEY:
            notify_auth_failure("DeepSeek", "missing DEEPSEEK_API_KEY")
            return None
        url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
        headers = deepseek_headers()
        payload = {"model": config.DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}]}

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        return _post_with_retries(url, headers, payload, config.DEEPSEEK_TIMEOUT, config.DEEPSEEK_RETRIES, service, parse_text)

    if provider == "zhipu":
        if not config.ZHIPU_API_KEY:
            notify_auth_failure("Zhipu", "missing ZHIPU_API_KEY")
            return None
        url = f"{config.ZHIPU_BASE_URL}/chat/completions"
        headers = zhipu_headers()
        payload = {"model": config.ZHIPU_MODEL, "messages": [{"role": "user", "content": prompt}]}

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        return _post_with_retries(url, headers, payload, config.ZHIPU_TIMEOUT, config.ZHIPU_RETRIES, service, parse_text)

    if provider == "nvidia":
        if not config.NVIDIA_API_KEY:
            notify_auth_failure("NVIDIA", "missing NVIDIA_API_KEY")
            return None
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = nvidia_headers()
        payload = {
            "model": config.QWEN_MODEL_NAME_PRO,
            "messages": [{"role": "user", "content": prompt}],
        }

        def parse_text(resp: requests.Response) -> str:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        return _post_with_retries(url, headers, payload, 300, config.NVIDIA_RETRIES, service, parse_text)

    return None


def parse_featured_ids(raw_text: str, service: str = "Featured") -> List[str]:
    json_str = extract_json_object(raw_text)
    if not json_str:
        notify_parse_error(service, "empty json")
        return []
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        notify_parse_error(service, str(exc))
        return []
    ids = data.get("featured_ids") or []
    if not isinstance(ids, list):
        return []
    return [str(x) for x in ids if x]


def apply_featured(record_ids: List[str], tenant_token: str) -> None:
    if not record_ids:
        return
    for record_id in record_ids:
        update_bitable_record_fields(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_NEWS_TABLE_ID,
            tenant_token,
            record_id,
            {config.NEWS_FIELD_FEATURED: True},
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
def analyze_with_gemini(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.GEMINI_API_KEY:
        notify_auth_failure("Gemini", "missing GEMINI_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing GEMINI_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.GEMINI_RETRIES):
        try:
            url = gemini_api_url(config.GEMINI_MODEL_NAME_SUMMARY)
            resp = requests.post(url, headers=gemini_headers(), json=payload, timeout=config.GEMINI_TIMEOUT)
            if resp.status_code in (401, 403):
                notify_auth_failure("Gemini", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code == 400:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}

            raw_json = resp.json()
            parts = raw_json["candidates"][0]["content"]["parts"]
            raw_text = "".join(p.get("text", "") for p in parts).strip()
            json_str = extract_json_object(raw_text)
            if not json_str:
                notify_parse_error("Gemini", "empty json")
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as exc:
                notify_parse_error("Gemini", str(exc))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("Gemini", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("Gemini", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("Gemini", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_iflow(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.IFLOW_API_KEY:
        notify_auth_failure("iFlow", "missing IFLOW_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing IFLOW_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = f"{config.IFLOW_BASE_URL}/chat/completions"
    payload = {
        "model": config.IFLOW_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.IFLOW_RETRIES):
        try:
            resp = requests.post(url, headers=iflow_headers(), json=payload, timeout=config.IFLOW_TIMEOUT)
            if resp.status_code in (401, 403):
                notify_auth_failure("iFlow", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code == 400:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                log(f"[NVIDIA] bad status: {response_snippet(resp)}")
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}

            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                log(f"[NVIDIA] empty choices: {truncate_text(json.dumps(data, ensure_ascii=False), 300)}")
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            message = choices[0].get("message") or {}
            raw_text = (message.get("content") or "").strip()
            json_str = extract_json_object(raw_text)
            if not json_str:
                notify_parse_error("iFlow", "empty json")
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as exc:
                notify_parse_error("iFlow", str(exc))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("iFlow", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("iFlow", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("iFlow", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_openai(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.OPENAI_API_KEY:
        notify_auth_failure("OpenAI", "missing OPENAI_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing OPENAI_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = f"{config.OPENAI_BASE_URL}/responses"
    payload = {"model": config.OPENAI_MODEL, "input": prompt}

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.OPENAI_RETRIES):
        try:
            resp = requests.post(url, headers=openai_headers(config.OPENAI_API_KEY), json=payload, timeout=config.OPENAI_TIMEOUT)
            if resp.status_code in (401, 403):
                notify_auth_failure("OpenAI", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
                time.sleep(1.2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}

            data = resp.json()
            raw_text = ""
            if isinstance(data.get("output_text"), str):
                raw_text = data.get("output_text", "")
            if not raw_text:
                outputs = data.get("output") or []
                if isinstance(outputs, list):
                    parts: List[str] = []
                    for item in outputs:
                        if not isinstance(item, dict):
                            continue
                        if isinstance(item.get("text"), str):
                            parts.append(item["text"])
                        content = item.get("content") or []
                        if isinstance(content, list):
                            for piece in content:
                                if isinstance(piece, dict):
                                    text = piece.get("text")
                                    if isinstance(text, str):
                                        parts.append(text)
                    raw_text = "".join(parts)

            result = parse_llm_json(raw_text, "OpenAI")
            if result is None:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("OpenAI", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("OpenAI", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("OpenAI", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_deepseek(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.DEEPSEEK_API_KEY:
        notify_auth_failure("DeepSeek", "missing DEEPSEEK_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing DEEPSEEK_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.DEEPSEEK_RETRIES):
        try:
            resp = requests.post(url, headers=deepseek_headers(), json=payload, timeout=config.DEEPSEEK_TIMEOUT)
            if resp.status_code in (401, 403):
                notify_auth_failure("DeepSeek", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
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
            result = parse_llm_json(raw_text, "DeepSeek")
            if result is None:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("DeepSeek", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("DeepSeek", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("DeepSeek", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_zhipu(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.ZHIPU_API_KEY:
        notify_auth_failure("Zhipu", "missing ZHIPU_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing ZHIPU_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = f"{config.ZHIPU_BASE_URL}/chat/completions"
    payload = {
        "model": config.ZHIPU_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.ZHIPU_RETRIES):
        try:
            resp = requests.post(url, headers=zhipu_headers(), json=payload, timeout=config.ZHIPU_TIMEOUT)
            if resp.status_code in (401, 403):
                notify_auth_failure("Zhipu", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
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
            result = parse_llm_json(raw_text, "Zhipu")
            if result is None:
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("Zhipu", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("Zhipu", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("Zhipu", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_nvidia(article: Dict[str, Any]) -> Dict[str, Any]:
    if not config.NVIDIA_API_KEY:
        notify_auth_failure("NVIDIA", "missing NVIDIA_API_KEY")
        return {"categories": ["调用失败"], "score": 0.0, "summary": "missing NVIDIA_API_KEY", "title_zh": "", "one_liner": "", "points": []}

    prompt = build_prompt(article)
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload: Dict[str, Any] = {
        "model": "qwen/qwen3-next-80b-a3b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 0.7,
        "max_tokens": 4096,
        "stream": False,
    }

    last_err: Optional[Exception] = None
    last_status_type: Optional[str] = None
    last_status_detail = ""
    for attempt in range(config.NVIDIA_RETRIES):
        try:
            resp = requests.post(url, headers=nvidia_headers(), json=payload, timeout=300)
            if resp.status_code in (401, 403):
                notify_auth_failure("NVIDIA", response_snippet(resp))
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            if resp.status_code in (429, 500, 502, 503, 504):
                last_status_type = "rate_limit" if resp.status_code == 429 else "server_error"
                last_status_detail = response_snippet(resp)
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
            if raw_text:
                # Drop <think> blocks to keep final JSON only (align with test.py behavior)
                raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.S)
                if "<think>" in raw_text:
                    raw_text = raw_text.split("<think>", 1)[0]
                raw_text = raw_text.strip()
            result = parse_llm_json(raw_text, "NVIDIA")
            if result is None:
                log(f"[NVIDIA] parse failed, raw={truncate_text(raw_text, 300)}")
                return {"categories": ["调用失败"], "score": 0.0, "summary": "", "title_zh": "", "one_liner": "", "points": []}
            return result
        except Exception as exc:
            last_err = exc
            if "timeout" in str(exc).lower():
                last_status_type = "timeout"
            time.sleep(1.0 + attempt)

    if last_status_type == "rate_limit":
        notify_rate_limit("NVIDIA", last_status_detail or "HTTP 429")
    elif last_status_type == "server_error":
        notify_server_error("NVIDIA", last_status_detail or "HTTP 5xx")
    elif last_status_type == "timeout":
        notify_timeout("NVIDIA", str(last_err) if last_err else "timeout")
    return {"categories": ["调用异常"], "score": 0.0, "summary": str(last_err) if last_err else "", "title_zh": "", "one_liner": "", "points": []}


def analyze_with_llm(article: Dict[str, Any]) -> Dict[str, Any]:
    provider = config.LLM_PROVIDER
    if provider == "iflow":
        return analyze_with_iflow(article)
    if provider == "openai":
        return analyze_with_openai(article)
    if provider == "deepseek":
        return analyze_with_deepseek(article)
    if provider == "zhipu":
        return analyze_with_zhipu(article)
    if provider == "nvidia":
        return analyze_with_nvidia(article)
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


def parse_featured_ids(raw_text: str, service: str = "Featured") -> List[str]:
    json_str = extract_json_object(raw_text)
    if not json_str:
        notify_parse_error(service, "empty json")
        return []
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        notify_parse_error(service, str(exc))
        return []
    ids = data.get("featured_ids") or []
    if not isinstance(ids, list):
        return []
    return [str(x) for x in ids if x]


def apply_featured(record_ids: List[str], tenant_token: str) -> None:
    if not record_ids:
        return
    for record_id in record_ids:
        update_bitable_record_fields(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_NEWS_TABLE_ID,
            tenant_token,
            record_id,
            {config.NEWS_FIELD_FEATURED: True},
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )


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


def parse_failed_items(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        return []
    data: Any = raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            data = json.loads(s)
        except Exception:
            return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    items: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_key = str(item.get("item_key") or "").strip()
        if not item_key:
            continue
        items.append(
            {
                "item_key": item_key,
                "title": str(item.get("title") or ""),
                "link": str(item.get("link") or ""),
                "published_ms": int(item.get("published_ms") or 0),
                "fail_count": int(item.get("fail_count") or 0),
                "last_error": str(item.get("last_error") or ""),
                "last_seen_ms": int(item.get("last_seen_ms") or 0),
                "miss_count": int(item.get("miss_count") or 0),
            }
        )
    return items


def serialize_failed_items(items: List[Dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def upsert_failed_item(
    items: List[Dict[str, Any]],
    item_key: str,
    entry_ts_ms: int,
    title: str,
    link: str,
    reason: str,
    now_ms: int,
) -> List[Dict[str, Any]]:
    for item in items:
        if item.get("item_key") == item_key:
            item["fail_count"] = int(item.get("fail_count") or 0) + 1
            item["last_error"] = reason or item.get("last_error") or ""
            item["last_seen_ms"] = now_ms
            item["miss_count"] = 0
            if title and not item.get("title"):
                item["title"] = title
            if link and not item.get("link"):
                item["link"] = link
            if entry_ts_ms and not item.get("published_ms"):
                item["published_ms"] = entry_ts_ms
            return items

    items.append(
        {
            "item_key": item_key,
            "title": title or "",
            "link": link or "",
            "published_ms": entry_ts_ms or 0,
            "fail_count": 1,
            "last_error": reason or "",
            "last_seen_ms": now_ms,
            "miss_count": 0,
        }
    )
    return items


def prune_failed_items(items: List[Dict[str, Any]], now_ms: int) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = item.get("item_key")
        if not key:
            continue
        prev = seen.get(key)
        if not prev or int(item.get("last_seen_ms") or 0) >= int(prev.get("last_seen_ms") or 0):
            seen[key] = item

    max_age_ms = config.FAILED_ITEMS_MAX_AGE_DAYS * 24 * 60 * 60 * 1000
    pruned: List[Dict[str, Any]] = []
    for item in seen.values():
        miss_count = int(item.get("miss_count") or 0)
        if miss_count >= config.FAILED_ITEMS_MAX_MISS:
            continue
        seen_ms = int(item.get("last_seen_ms") or item.get("published_ms") or 0)
        if seen_ms and now_ms - seen_ms > max_age_ms:
            continue
        pruned.append(item)

    pruned.sort(key=lambda x: int(x.get("last_seen_ms") or 0), reverse=True)
    return pruned[: config.FAILED_ITEMS_MAX]


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
        "failed_items": fields.get(config.RSS_FIELD_FAILED_ITEMS),
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


def split_sources_and_queue(
    sources: List[Dict[str, Any]],
    existing_keys: set,
    tenant_token: str,
) -> tuple[list, dict, dict]:
    queue: List[Dict[str, Any]] = []
    source_states: Dict[str, Dict[str, Any]] = {}
    stats = {
        "sources_processed": 0,
        "sources_skipped": 0,
        "entries_fetched": 0,
        "queue_total": 0,
    }

    for source in sources:
        if not source.get("feed_url"):
            stats["sources_skipped"] += 1
            continue

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
            stats["sources_skipped"] += 1
            continue

        if not should_fetch(source, now_ms):
            stats["sources_skipped"] += 1
            continue

        last_item_pub_time = source.get("last_item_pub_time") or 0
        cutoff_ms = last_item_pub_time or (source.get("last_fetch_time") or 0)
        consecutive_fail = source.get("consecutive_fail_count") or 0

        try:
            log(f"[RSS] fetching {source.get('name') or source.get('feed_url')}")
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
            stats["sources_skipped"] += 1
            continue

        entries = feed.entries or []
        log(f"[RSS] fetched entries={len(entries)} for {source.get('name') or source.get('feed_url')}")
        stats["entries_fetched"] += len(entries)
        if config.MAX_ENTRIES_PER_FEED and len(entries) > config.MAX_ENTRIES_PER_FEED:
            entries = entries[: config.MAX_ENTRIES_PER_FEED]

        failed_items = parse_failed_items(source.get("failed_items"))
        entry_map: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            entry_key = build_item_key(entry, source.get("item_id_strategy"), source.get("content_hash_algo"))
            if entry_key:
                entry_map[entry_key] = entry

        latest_pub_ms = 0
        latest_key = ""
        processed_keys: set = set()
        updated_failed_items: List[Dict[str, Any]] = []

        if failed_items:
            retry_budget = config.FAILED_ITEMS_RETRY_LIMIT
            for item in failed_items:
                item_key = item.get("item_key") or ""
                if not item_key:
                    continue
                entry = entry_map.get(item_key)
                if entry is None:
                    item["miss_count"] = int(item.get("miss_count") or 0) + 1
                    item["last_seen_ms"] = now_ms
                    updated_failed_items.append(item)
                    continue
                if item_key in existing_keys:
                    processed_keys.add(item_key)
                    continue
                if retry_budget <= 0:
                    updated_failed_items.append(item)
                    continue
                retry_budget -= 1

                entry_ts = entry_published_ts(entry)
                entry_ts_ms = entry_ts * 1000 if entry_ts else 0
                article = {
                    "title": entry.get("title") or "",
                    "content": entry_text_content(entry),
                    "link": entry.get("link") or "",
                    "published": entry_ts,
                    "source": source.get("name") or source.get("feed_url"),
                }

                queue.append(
                    {
                        "source_id": source["record_id"],
                        "item_key": item_key,
                        "article": article,
                        "entry_ts": entry_ts,
                        "entry_ts_ms": entry_ts_ms,
                        "from_failed": True,
                    }
                )
                processed_keys.add(item_key)

                if entry_ts_ms > latest_pub_ms:
                    latest_pub_ms = entry_ts_ms
                    latest_key = item_key

        for entry in entries:
            entry_ts = entry_published_ts(entry)
            entry_ts_ms = entry_ts * 1000 if entry_ts else 0
            if entry_ts_ms and cutoff_ms and entry_ts_ms <= cutoff_ms:
                continue

            item_key = build_item_key(entry, source.get("item_id_strategy"), source.get("content_hash_algo"))
            if not item_key:
                continue
            if item_key in processed_keys:
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

            queue.append(
                {
                    "source_id": source["record_id"],
                    "item_key": item_key,
                    "article": article,
                    "entry_ts": entry_ts,
                    "entry_ts_ms": entry_ts_ms,
                    "from_failed": False,
                }
            )

            if entry_ts_ms > latest_pub_ms:
                latest_pub_ms = entry_ts_ms
                latest_key = item_key

        source_states[source["record_id"]] = {
            "source": source,
            "now_ms": now_ms,
            "latest_pub_ms": latest_pub_ms,
            "latest_key": latest_key,
            "updated_failed_items": updated_failed_items,
            "new_count": 0,
        }
        stats["sources_processed"] += 1

    stats["queue_total"] = len(queue)
    return queue, source_states, stats


def run_llm_queue(
    queue: List[Dict[str, Any]],
    source_states: Dict[str, Dict[str, Any]],
    tenant_token: str,
    existing_keys: set,
    featured_candidates: List[Dict[str, str]],
    stats: Dict[str, int],
) -> None:
    total = len(queue)
    if total <= 0:
        log("[LLM] queue empty")
        return

    lock = threading.Lock()

    def handle_item(item: Dict[str, Any]) -> None:
        state = source_states[item["source_id"]]
        article = item["article"]
        analysis = analyze_with_llm(article)
        categories = analysis.get("categories") or []
        if isinstance(categories, list) and any(c in FAILED_CATEGORIES for c in categories):
            with lock:
                stats["llm_failed"] += 1
                upsert_failed_item(
                    state["updated_failed_items"],
                    item["item_key"],
                    item["entry_ts_ms"],
                    article.get("title") or "",
                    article.get("link") or "",
                    "llm_failed",
                    state["now_ms"],
                )
            return

        with lock:
            stats["llm_success"] += 1

        score = float(analysis.get("score", 0.0) or 0.0)
        emb_vec = None
        if score >= config.FEISHU_MIN_SCORE:
            if config.ENABLE_VECTORIZE_DEDUP:
                embed_text = build_embedding_text(article, analysis)
                emb_vec = cf_embed_text(embed_text)
                if emb_vec:
                    best_sim = vectorize_query(emb_vec)
                    if best_sim is not None and best_sim >= config.CF_VECTORIZE_SIM_THRESHOLD:
                        log(f"[Vectorize] skip similar={best_sim:.3f} title={article.get('title','')}")
                        with lock:
                            existing_keys.add(item["item_key"])
                            stats["vectorize_skipped"] += 1
                        return
                else:
                    log("[Vectorize] embedding unavailable, fallback to exact dedup only")

            fields = build_news_fields(article, analysis, item["item_key"])
            ok, record_id = create_bitable_record_with_id(
                config.FEISHU_APP_TOKEN,
                config.FEISHU_NEWS_TABLE_ID,
                tenant_token,
                fields,
                config.HTTP_TIMEOUT,
                config.HTTP_RETRIES,
            )
            if not ok:
                with lock:
                    stats["feishu_create_failed"] += 1
            else:
                if config.ENABLE_VECTORIZE_DEDUP and emb_vec:
                    metadata = {
                        "title": article.get("title") or "",
                        "source": article.get("source") or "",
                        "published": item.get("entry_ts") or 0,
                    }
                    vectorize_upsert(item["item_key"], emb_vec, metadata)
                if record_id:
                    with lock:
                        featured_candidates.append(
                            {
                                "record_id": record_id,
                                "title": clean_feishu_value(fields.get(config.NEWS_FIELD_TITLE)).strip(),
                                "summary": clean_feishu_value(fields.get(config.NEWS_FIELD_SUMMARY)).strip(),
                            }
                        )

        with lock:
            existing_keys.add(item["item_key"])
            stats["entries_processed"] += 1
            stats["entries_new"] += 1
            state["new_count"] += 1

    done = 0
    with ThreadPoolExecutor(max_workers=config.LLM_CONCURRENCY) as executor:
        futures = [executor.submit(handle_item, item) for item in queue]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                with lock:
                    stats["llm_failed"] += 1
                log(f"[LLM] task failed: {exc}")
            done += 1
            bar = render_progress(done, total, width=config.PROGRESS_BAR_WIDTH)
            msg = f"[LLM] {bar} ok={stats['llm_success']} fail={stats['llm_failed']}"
            if sys.stdout.isatty():
                sys.stdout.write("\r" + msg)
                sys.stdout.flush()
            else:
                log(msg)
        if sys.stdout.isatty():
            sys.stdout.write("\n")
            sys.stdout.flush()


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

    failed_items = parse_failed_items(source.get("failed_items"))
    entry_map: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        entry_key = build_item_key(entry, source.get("item_id_strategy"), source.get("content_hash_algo"))
        if entry_key:
            entry_map[entry_key] = entry

    latest_pub_ms = 0
    latest_key = ""
    new_count = 0
    processed_keys: set = set()

    if failed_items:
        retry_budget = config.FAILED_ITEMS_RETRY_LIMIT
        updated_failed_items: List[Dict[str, Any]] = []
        for item in failed_items:
            item_key = item.get("item_key") or ""
            if not item_key:
                continue
            entry = entry_map.get(item_key)
            if entry is None:
                item["miss_count"] = int(item.get("miss_count") or 0) + 1
                item["last_seen_ms"] = now_ms
                updated_failed_items.append(item)
                continue
            if item_key in existing_keys:
                processed_keys.add(item_key)
                continue
            if retry_budget <= 0:
                updated_failed_items.append(item)
                continue
            retry_budget -= 1

            entry_ts = entry_published_ts(entry)
            entry_ts_ms = entry_ts * 1000 if entry_ts else 0
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
                upsert_failed_item(
                    updated_failed_items,
                    item_key,
                    entry_ts_ms,
                    article.get("title") or "",
                    article.get("link") or "",
                    "llm_failed",
                    now_ms,
                )
                processed_keys.add(item_key)
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
                            processed_keys.add(item_key)
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
            processed_keys.add(item_key)
            new_count += 1

            if entry_ts_ms > latest_pub_ms:
                latest_pub_ms = entry_ts_ms
                latest_key = item_key

        failed_items = prune_failed_items(updated_failed_items, now_ms)

    for entry in entries:
        entry_ts = entry_published_ts(entry)
        entry_ts_ms = entry_ts * 1000 if entry_ts else 0
        if entry_ts_ms and cutoff_ms and entry_ts_ms <= cutoff_ms:
            continue

        item_key = build_item_key(entry, source.get("item_id_strategy"), source.get("content_hash_algo"))
        if not item_key:
            continue
        if item_key in processed_keys:
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
            log(f"[LLM:{config.LLM_PROVIDER}] skipped due to failure category: {categories}")
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
    update_fields[config.RSS_FIELD_FAILED_ITEMS] = serialize_failed_items(failed_items)

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
    set_notify_tenant_token(tenant_token)
    required = []
    if not config.FEISHU_APP_TOKEN:
        required.append("FEISHU_APP_TOKEN")
    if not config.FEISHU_NEWS_TABLE_ID:
        required.append("FEISHU_NEWS_TABLE_ID")
    if not config.FEISHU_RSS_TABLE_ID:
        required.append("FEISHU_RSS_TABLE_ID")
    if required:
        notify_config_missing("missing: " + ", ".join(required))
        log(f"[Config] missing: {', '.join(required)}")
        return
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

    queue, source_states, fetch_stats = split_sources_and_queue(enabled_sources, existing_keys, tenant_token)
    stats = {
        "llm_success": 0,
        "llm_failed": 0,
        "feishu_create_failed": 0,
        "entries_processed": 0,
        "entries_new": 0,
        "vectorize_skipped": 0,
    }
    stats.update(fetch_stats)
    log(f"[Queue] total={stats['queue_total']} sources_processed={stats['sources_processed']} sources_skipped={stats['sources_skipped']}")

    featured_candidates: List[Dict[str, str]] = []
    run_llm_queue(queue, source_states, tenant_token, existing_keys, featured_candidates, stats)

    for state in source_states.values():
        source = state["source"]
        update_fields: Dict[str, Any] = {
            config.RSS_FIELD_STATUS: config.STATUS_OK,
            config.RSS_FIELD_LAST_FETCH_STATUS: config.FETCH_STATUS_SUCCESS,
            config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT: 0,
            config.RSS_FIELD_LAST_FETCH_TIME: state["now_ms"],
            config.RSS_FIELD_FAILED_ITEMS: serialize_failed_items(prune_failed_items(state["updated_failed_items"], state["now_ms"])),
        }
        if state["latest_pub_ms"]:
            update_fields[config.RSS_FIELD_LAST_ITEM_PUB_TIME] = state["latest_pub_ms"]
        if state["latest_key"]:
            update_fields[config.RSS_FIELD_LAST_ITEM_GUID] = state["latest_key"]

        update_bitable_record_fields(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_RSS_TABLE_ID,
            tenant_token,
            source["record_id"],
            update_fields,
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
        log(f"[RSS] {source.get('name') or source.get('feed_url')} new={state['new_count']}")

    if featured_candidates:
        log(f"[Featured] candidates={len(featured_candidates)} ids={[c.get('record_id') for c in featured_candidates]}")
        prompt = build_featured_prompt(featured_candidates)
        raw_text = call_featured_llm(prompt)
        if not raw_text:
            log("[Featured] empty response")
        else:
            featured_ids = parse_featured_ids(raw_text)
            log(f"[Featured] selected_ids={featured_ids}")
            if featured_ids:
                apply_featured(featured_ids, tenant_token)

    log(
        "[Summary] "
        f"sources_done={stats['sources_processed']} "
        f"sources_skipped={stats['sources_skipped']} "
        f"entries_fetched={stats['entries_fetched']} "
        f"queue_total={stats['queue_total']} "
        f"processed={stats['entries_processed']} "
        f"new={stats['entries_new']} "
        f"llm_ok={stats['llm_success']} "
        f"llm_failed={stats['llm_failed']} "
        f"feishu_failed={stats['feishu_create_failed']} "
        f"vectorize_skipped={stats['vectorize_skipped']}"
    )


if __name__ == "__main__":
    main()
