# -*- coding: utf-8 -*-
import time
from typing import Any, Dict, List

import requests

import config
from feishu_client import (
    create_bitable_field,
    create_bitable_record,
    get_tenant_access_token,
    list_bitable_fields,
    list_bitable_records,
)

TEXT = 1
NUMBER = 2
SINGLE_SELECT = 3
DATE = 5
CHECKBOX = 7


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except OSError:
        pass


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
        return str(value)
    if isinstance(value, list):
        return "".join(clean_feishu_value(v) for v in value)
    return str(value)


def get_freshrss_auth_token() -> str:
    url = f"{config.FRESHRSS_URL}/api/greader.php/accounts/ClientLogin"
    params = {"Email": config.FRESHRSS_USERNAME, "Passwd": config.FRESHRSS_API_PASSWORD}
    resp = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"FreshRSS ClientLogin failed: {resp.status_code} {resp.text[:200]}")
    for line in resp.text.splitlines():
        if line.strip().startswith("Auth="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("FreshRSS Auth token not found")


def fetch_subscriptions(auth_token: str) -> List[Dict[str, Any]]:
    url = f"{config.FRESHRSS_URL}/api/greader.php/reader/api/0/subscription/list"
    headers = {"Authorization": f"GoogleLogin auth={auth_token}"}
    resp = requests.get(url, headers=headers, params={"output": "json"}, timeout=config.HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"FreshRSS subscription list failed: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    return data.get("subscriptions") or []


def build_field_defs() -> List[Dict[str, Any]]:
    return [
        {"name": config.RSS_FIELD_NAME, "type": TEXT},
        {"name": config.RSS_FIELD_FEED_URL, "type": TEXT},
        {"name": config.RSS_FIELD_TYPE, "type": SINGLE_SELECT},
        {"name": config.RSS_FIELD_DESCRIPTION, "type": TEXT},
        {"name": config.RSS_FIELD_ENABLED, "type": CHECKBOX},
        {"name": config.RSS_FIELD_STATUS, "type": SINGLE_SELECT},
        {"name": config.RSS_FIELD_LAST_FETCH_TIME, "type": DATE},
        {"name": config.RSS_FIELD_LAST_FETCH_STATUS, "type": SINGLE_SELECT},
        {"name": config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT, "type": NUMBER},
        {"name": config.RSS_FIELD_LAST_ITEM_GUID, "type": TEXT},
        {"name": config.RSS_FIELD_LAST_ITEM_PUB_TIME, "type": DATE},
        {"name": config.RSS_FIELD_ITEM_ID_STRATEGY, "type": SINGLE_SELECT},
        {"name": config.RSS_FIELD_CONTENT_LANGUAGE, "type": SINGLE_SELECT},
    ]


def ensure_fields(tenant_token: str) -> None:
    existing_items = list_bitable_fields(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_RSS_TABLE_ID,
        tenant_token,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )
    existing_names = {item.get("field_name") or item.get("name") for item in existing_items}

    for field_def in build_field_defs():
        name = field_def["name"]
        if name in existing_names:
            continue
        ok, data = create_bitable_field(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_RSS_TABLE_ID,
            tenant_token,
            name,
            field_def["type"],
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
        if not ok and field_def["type"] != TEXT:
            log(f"[Feishu] create field failed, fallback to text: {name} => {data}")
            ok, data = create_bitable_field(
                config.FEISHU_APP_TOKEN,
                config.FEISHU_RSS_TABLE_ID,
                tenant_token,
                name,
                TEXT,
                config.HTTP_TIMEOUT,
                config.HTTP_RETRIES,
            )
        if ok:
            log(f"[Feishu] created field: {name}")
        else:
            log(f"[Feishu] create field failed: {name} => {data}")


def import_subscriptions(tenant_token: str) -> None:
    records = list_bitable_records(
        config.FEISHU_APP_TOKEN,
        config.FEISHU_RSS_TABLE_ID,
        tenant_token,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )

    existing_urls = set()
    for rec in records:
        fields = rec.get("fields") or {}
        url = clean_feishu_value(fields.get(config.RSS_FIELD_FEED_URL))
        if url:
            existing_urls.add(url)

    auth_token = get_freshrss_auth_token()
    subs = fetch_subscriptions(auth_token)

    now_ms = int(time.time() * 1000)
    created = 0
    skipped = 0

    for sub in subs:
        feed_url = (sub.get("url") or "").strip()
        if not feed_url:
            continue
        if feed_url in existing_urls:
            skipped += 1
            continue

        fields: Dict[str, Any] = {
            config.RSS_FIELD_NAME: (sub.get("title") or "").strip(),
            config.RSS_FIELD_FEED_URL: feed_url,
            config.RSS_FIELD_DESCRIPTION: "",
            config.RSS_FIELD_ENABLED: True,
            config.RSS_FIELD_STATUS: config.STATUS_IDLE,
            config.RSS_FIELD_CONSECUTIVE_FAIL_COUNT: 0,
            config.RSS_FIELD_LAST_ITEM_GUID: "",
            config.RSS_FIELD_ITEM_ID_STRATEGY: config.DEFAULT_ITEM_ID_STRATEGY,
            config.RSS_FIELD_CONTENT_LANGUAGE: "",
        }

        ok = create_bitable_record(
            config.FEISHU_APP_TOKEN,
            config.FEISHU_RSS_TABLE_ID,
            tenant_token,
            fields,
            config.HTTP_TIMEOUT,
            config.HTTP_RETRIES,
        )
        if ok:
            created += 1
            existing_urls.add(feed_url)
        else:
            log(f"[Feishu] create record failed: {feed_url}")

    log(f"[Import] created={created}, skipped={skipped}")


def main() -> None:
    tenant_token = get_tenant_access_token(
        config.FEISHU_APP_ID,
        config.FEISHU_APP_SECRET,
        config.HTTP_TIMEOUT,
        config.HTTP_RETRIES,
    )
    ensure_fields(tenant_token)
    import_subscriptions(tenant_token)


if __name__ == "__main__":
    main()
