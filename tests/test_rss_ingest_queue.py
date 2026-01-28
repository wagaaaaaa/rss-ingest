import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rss_ingest import collect_queue_items


def test_collect_queue_items_skips_existing_keys():
    items = [
        {"item_key": "a", "content": "x"},
        {"item_key": "b", "content": "y"},
    ]
    existing = {"a"}
    out = collect_queue_items(items, existing)
    assert [i["item_key"] for i in out] == ["b"]
