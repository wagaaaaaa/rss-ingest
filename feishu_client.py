# -*- coding: utf-8 -*-
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


def _sleep_backoff(attempt: int) -> None:
    time.sleep(min(8.0, 0.8 * (2 ** attempt) + random.random() * 0.3))


def http_get(url: str, headers: Dict[str, str], timeout: int, retries: int, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            return requests.get(url, headers=headers, params=params, timeout=timeout)
        except Exception as exc:
            last_err = exc
            _sleep_backoff(i)
    raise RuntimeError(f"HTTP GET failed after retries: {last_err}")


def http_post(url: str, headers: Dict[str, str], json_body: Dict[str, Any], timeout: int, retries: int) -> requests.Response:
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            return requests.post(url, headers=headers, json=json_body, timeout=timeout)
        except Exception as exc:
            last_err = exc
            _sleep_backoff(i)
    raise RuntimeError(f"HTTP POST failed after retries: {last_err}")


def http_put(url: str, headers: Dict[str, str], json_body: Dict[str, Any], timeout: int, retries: int) -> requests.Response:
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            return requests.put(url, headers=headers, json=json_body, timeout=timeout)
        except Exception as exc:
            last_err = exc
            _sleep_backoff(i)
    raise RuntimeError(f"HTTP PUT failed after retries: {last_err}")


def get_tenant_access_token(app_id: str, app_secret: str, timeout: int, retries: int) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}
    headers = {"Content-Type": "application/json; charset=utf-8"}
    resp = http_post(url, headers, payload, timeout, retries)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"[Feishu] token error: {data}")
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"[Feishu] token missing: {data}")
    return token


def list_bitable_fields(
    app_token: str,
    table_id: str,
    tenant_token: str,
    timeout: int,
    retries: int,
    page_size: int = 200,
    max_pages: int = 20,
) -> List[Dict[str, Any]]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
    }

    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    for _ in range(max_pages):
        params: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        resp = http_get(url, headers, timeout, retries, params=params)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"[Feishu] list fields error: {data}")
        data_block = data.get("data") or {}
        items.extend(data_block.get("items") or [])
        if not data_block.get("has_more"):
            break
        page_token = data_block.get("page_token")
        if not page_token:
            break

    return items


def create_bitable_field(
    app_token: str,
    table_id: str,
    tenant_token: str,
    field_name: str,
    field_type: int,
    timeout: int,
    retries: int,
    field_property: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    body: Dict[str, Any] = {
        "field_name": field_name,
        "type": field_type,
    }
    if field_property:
        body["property"] = field_property

    resp = http_post(url, headers, body, timeout, retries)
    data = resp.json()
    if data.get("code") != 0:
        return False, data
    return True, data


def list_bitable_records(
    app_token: str,
    table_id: str,
    tenant_token: str,
    timeout: int,
    retries: int,
    page_size: int = 500,
    max_pages: int = 50,
    filter_obj: Optional[Dict[str, Any]] = None,
    sort: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    for _ in range(max_pages):
        body: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            body["page_token"] = page_token
        if filter_obj:
            body["filter"] = filter_obj
        if sort:
            body["sort"] = sort

        resp = http_post(url, headers, body, timeout, retries)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"[Feishu] list records error: {data}")

        data_block = data.get("data") or {}
        items.extend(data_block.get("items") or [])
        if not data_block.get("has_more"):
            break
        page_token = data_block.get("page_token")
        if not page_token:
            break

    return items


def update_bitable_record_fields(
    app_token: str,
    table_id: str,
    tenant_token: str,
    record_id: str,
    fields: Dict[str, Any],
    timeout: int,
    retries: int,
) -> bool:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {"fields": fields}
    resp = http_put(url, headers, body, timeout, retries)
    data = resp.json()
    if data.get("code") != 0:
        return False
    return True


def create_bitable_record(
    app_token: str,
    table_id: str,
    tenant_token: str,
    fields: Dict[str, Any],
    timeout: int,
    retries: int,
) -> bool:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {"fields": fields}
    resp = http_post(url, headers, body, timeout, retries)
    data = resp.json()
    if data.get("code") != 0:
        print(f"[Feishu] create record error: {data}", flush=True)
        return False
    return True


def create_bitable_record_with_id(
    app_token: str,
    table_id: str,
    tenant_token: str,
    fields: Dict[str, Any],
    timeout: int,
    retries: int,
) -> Tuple[bool, Optional[str]]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    body = {"fields": fields}
    resp = http_post(url, headers, body, timeout, retries)
    data = resp.json()
    if data.get("code") != 0:
        print(f"[Feishu] create record error: {data}", flush=True)
        return False, None
    record = (data.get("data") or {}).get("record") or {}
    return True, record.get("record_id")
