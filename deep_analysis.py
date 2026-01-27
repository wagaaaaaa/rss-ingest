import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import config
from feishu_client import (
    get_tenant_access_token,
    list_bitable_records,
    send_feishu_webhook_post,
    update_bitable_record_fields,
)
from rss_ingest import clean_feishu_value, call_featured_llm


DEFAULT_PROMPT = r'''# Role: 深度阅读与行动转化专家

## Profile
- **Language**: 中文
- **Description**: 你不是信息的搬运工，而是“思维的过滤器”。你服务于一位追求高效、务实、偏向“一人公司/超级个体”的用户。你的任务是将用户输入的文章进行“无损压缩”，并产生主观的“深度化学反应”。

## User Persona (关键上下文)
- 用户属性：偏应用、偏业务、偏技巧的“超级个体”/一人公司。
- 核心需求：拒绝废话，寻找第一性原理，将理论转化为可落地的行动或商业策略。
- 沟通风格：直白、接地气、毫不留情指出逻辑漏洞。

## Workflow (执行SOP)

### Phase 1: 客观的“无损压缩” (Summary)
**目标**：重构原文逻辑，让未读过的人也能秒懂。
**规则**：
1.  **剥离皮肉**：剔除故事和修辞，只抓作者的思维脉络（核心观点 + 论据 A/B/C + 反驳 D）。
2.  **绝对中立**：像镜子一样还原，即使作者观点偏激也如实记录，禁止使用“我觉得”或“通过这篇文章”。
3.  **独立自洽**：输出的内容必须是一个独立产品，不依赖原文即可阅读。

### Phase 2: 主观的“化学反应” (Deep Thinking)
**目标**：将信息转化为用户的认知资产和行动力。
**规则**：
1.  **向内连接 (缝合)**：调用心理学、商业策略、认知科学等旧知。思考：“这个概念像什么？本质是什么？”
2.  **向上连接 (博弈)**：批判性审视。思考：“谁在获利？隐含假设是什么？商业模式的本质是什么？”
3.  **向下连接 (转化)**：**这是最关键的一步**。结合“超级个体/一人公司”的身份，思考：“如何利用这个逻辑获利？如何防守？明天具体可以做什么？”

## Output Format (严格遵守)

具体内容：
**核心论点：** [一句话概括]
**论证逻辑：**
1. [论点1]：[论据/逻辑链]
2. [论点2]：[论据/逻辑链]
...

深度思考：
#### 1. 向内连接：[概念名称/本质]
* [分析内容：与旧知的挂钩，原理解析]

#### 2. 向上连接：[商业/社会/博弈视角]
* [分析内容：批判性审视，利益链条分析]

#### 3. 向下连接：超级个体的“攻守之道”
* **守（个人防线）：** [具体的避坑或防御策略]
* **攻（业务转化）：** [如何将此逻辑应用到电商、营销、Prompt工程或一人公司的业务中]
    * *行动建议：* [具体的、可执行的下一步]

---
# 输入的新闻/文章内容：

## 重要限制
1. 不要使用 Markdown 符号（不要用 **、###、-、*、` 等）。
2. 只输出纯文本，严格按照上述“Output Format”的字面结构。
'''


def build_deep_analysis_prompt(content: str) -> str:
    china_tz = timezone(timedelta(hours=8))
    now = datetime.now(china_tz)
    time_line = f"你所处的时间为：{now.year}年{now.month:02d}月"
    prompt = config.DEEP_ANALYSIS_PROMPT_OVERRIDE or DEFAULT_PROMPT
    return f"{prompt}\n{time_line}\n\n# Input\n{content}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deep analysis for featured items.")
    parser.add_argument("--hours", type=float, default=12.0, help="Look back hours, default 12.")
    parser.add_argument("--limit", type=int, default=20, help="Max items to process, default 20.")
    parser.add_argument("--dry-run", action="store_true", help="Do not send webhook.")
    return parser.parse_args()


def fetch_featured_records(tenant_token: str, hours: float, limit: int) -> List[Dict[str, str]]:
    field_featured = config.NEWS_FIELD_FEATURED
    field_read = config.NEWS_FIELD_READ
    field_title = config.NEWS_FIELD_TITLE
    field_content = config.NEWS_FIELD_FULL_CONTENT
    field_distance = "\u8ddd\u4eca"  # 距今

    filter_obj = {
        "conjunction": "and",
        "conditions": [
            {"field_name": field_distance, "operator": "isLessEqual", "value": [hours]},
        ],
    }

    # Fetch recent records and filter locally (avoid date filter issues)
    records = list_bitable_records(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_NEWS_TABLE_ID,
        tenant_token,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
        page_size=200,
        max_pages=5,
        filter_obj=filter_obj,
        sort=[{"field_name": field_distance, "order": "asc"}],
    )

    items: List[Dict[str, str]] = []
    for record in records:
        fields = record.get("fields") or {}
        if not fields.get(field_featured):
            continue
        if fields.get(field_read):
            continue
        raw_title = fields.get(field_title)
        title = clean_feishu_value(raw_title).strip()
        link = ""
        if isinstance(raw_title, dict):
            link = clean_feishu_value(raw_title.get("link")).strip()
        content = clean_feishu_value(fields.get(field_content)).strip()
        if not content:
            continue
        items.append(
            {
                "record_id": record.get("record_id"),
                "title": title,
                "link": link,
                "content": content,
            }
        )
        if len(items) >= limit:
            break

    return items


def main() -> int:
    args = parse_args()
    if not config.FEISHU_WEBHOOK_URL and not args.dry_run:
        raise SystemExit("Missing FEISHU_WEBHOOK_URL")

    tenant_token = get_tenant_access_token(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, config.HTTP_TIMEOUT, config.HTTP_RETRIES)
    items = fetch_featured_records(tenant_token, args.hours, args.limit)
    if not items:
        print("No featured records found.")
        return 0

    for item in items:
        prompt = build_deep_analysis_prompt(item["content"])
        raw = call_featured_llm(prompt)
        if not raw:
            continue
        header = item["title"]
        link = item.get("link") or ""
        text = raw.strip()
        if args.dry_run:
            print(f"{header}\n{link}\n\n{text}")
        else:
            ok = send_feishu_webhook_post(
                config.FEISHU_WEBHOOK_URL,
                header,
                link,
                text,
                config.HTTP_TIMEOUT,
                config.HTTP_RETRIES,
            )
            if not ok:
                print(f"[Feishu] webhook send failed: {item['record_id']}")
            else:
                update_bitable_record_fields(
                    config.FEISHU_APP_TOKEN,
                    config.FEISHU_NEWS_TABLE_ID,
                    tenant_token,
                    item["record_id"],
                    {config.NEWS_FIELD_READ: True},
                    config.HTTP_TIMEOUT,
                    config.HTTP_RETRIES,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
