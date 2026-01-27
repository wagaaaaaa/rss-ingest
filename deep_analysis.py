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


DEFAULT_PROMPT = r'''用户发给你一篇文章时，你需要基于以下要求进行总结和深度思考。输出纯文本，可使用序号和"- "，禁止使用#和*

内容要求：
一、 好的文章总结：客观的“无损压缩”
好的总结不是简单的摘抄金句，而是对原文逻辑的重构。它的核心目标是：哪怕没有读过原文的人，看了你的总结，也能精准理解作者的核心论点和论证逻辑。
一个优秀的总结应该包含以下三个维度：
1. 剥离皮肉，只留骨架 (结构化)
不要陷入具体的例子或故事中。好的总结能识别出文章的“骨架”——即作者的思维脉络。
平庸的总结： “作者说了A，然后说了B，最后说了C。”
好的总结： “作者的核心观点是X。为了证明X，他提出了三个论据（A、B、C），并反驳了常见的观点D。”
2. 信息的“高保真” (客观性)
总结阶段必须克制表达个人观点的欲望。你需要像一面镜子，忠实地还原作者的原意，而不是“我觉得作者是这个意思”。如果作者的观点偏激，你的总结也应体现这种偏激，而不是试图修饰它。
3. 独立性 (自洽性)
这个总结本身应该是一个独立的产品。如果读者看完总结还需要去翻原文才能看懂某个术语，那么这个总结就是失败的。
检验标准： 试着把你写的总结讲给完全没读过这篇文章的朋友听。如果他能听懂逻辑，且没有歧义，这就是一个合格的总结。
二、 深度思考：主观的“化学反应”
如果说总结是把书读薄，那么深度思考就是把书读厚。它是你与作者之间的一场对话，甚至是博弈。
深度思考通常发生在总结之后，它应该包含以下三个层次的“连接”：
1. 向内连接：与旧知识挂钩 (缝合)
不要把新信息孤立地存放。深度思考的第一步是问自己：“这个概念像什么？”
“这个观点，和我之前在心理学里学到的‘认知失调’有什么异同？”
“这一段历史描述，能不能解释我现在工作中遇到的管理难题？”
好的思考能让新知识“长”在你原本的知识树上。
2. 向上连接：批判性审视 (博弈)
不要全盘接受。去寻找作者逻辑中的漏洞，或者寻找适用的边界。
反向思考： “在什么情况下，作者的这个结论是错误的？”
寻找前提： “作者得出这个结论，隐含了什么假设？这个假设在今天还成立吗？”
3. 向下连接：指导行动 (转化)
这是最关键的一步。如果没有改变你的认知模型或行为模式，阅读就只是娱乐。
具体化： “如果我接受这个观点，我明天的行动会有什么不同？”
场景化： “下次遇到类似情况，我可以如何运用这个理论来解决问题？”
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
    print(f"[DeepAnalysis] fetching records: 距今<= {hours}h, limit={limit}")
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

    print(f"[DeepAnalysis] matched items={len(items)}")
    return items


def main() -> int:
    args = parse_args()
    if not config.FEISHU_WEBHOOK_URL and not args.dry_run:
        raise SystemExit("Missing FEISHU_WEBHOOK_URL")

    tenant_token = get_tenant_access_token(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, config.HTTP_TIMEOUT, config.HTTP_RETRIES)
    print("[DeepAnalysis] got tenant token")
    items = fetch_featured_records(tenant_token, args.hours, args.limit)
    if not items:
        print("No featured records found.")
        return 0

    for item in items:
        print(f"[DeepAnalysis] processing: {item['record_id']} title={item['title']}")
        prompt = build_deep_analysis_prompt(item["content"])
        print("[DeepAnalysis] calling LLM...")
        raw = call_featured_llm(prompt)
        if not raw:
            print("[DeepAnalysis] LLM returned empty response")
            continue
        header = item["title"]
        link = item.get("link") or ""
        text = raw.strip()
        if args.dry_run:
            print(f"{header}\n{link}\n\n{text}")
        else:
            print("[DeepAnalysis] sending to webhook...")
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
                print("[DeepAnalysis] webhook sent, marking 已读")
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
