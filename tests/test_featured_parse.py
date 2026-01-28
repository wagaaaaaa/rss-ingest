import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rss_ingest import parse_featured_ids


def test_parse_featured_ids_from_json_text():
    raw = "{" + "\"featured_ids\": [\"rid1\", \"rid2\"]}"
    ids = parse_featured_ids(raw)
    assert ids == ["rid1", "rid2"]
