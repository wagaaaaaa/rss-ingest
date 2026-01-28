import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rss_ingest
from rss_ingest import collect_queue_items, split_sources_and_queue


def test_collect_queue_items_skips_existing_keys():
    items = [
        {"item_key": "a", "content": "x"},
        {"item_key": "b", "content": "y"},
    ]
    existing = {"a"}
    out = collect_queue_items(items, existing)
    assert [i["item_key"] for i in out] == ["b"]


def test_split_sources_and_queue_returns_queue(monkeypatch):
    monkeypatch.setattr(rss_ingest, "update_bitable_record_fields", lambda *args, **kwargs: None)
    sources = [{"feed_url": "x", "enabled": False, "record_id": "r1"}]
    queue, source_states, stats = split_sources_and_queue(sources, existing_keys=set(), tenant_token="t")
    assert isinstance(queue, list)
    assert isinstance(source_states, dict)
    assert isinstance(stats, dict)
