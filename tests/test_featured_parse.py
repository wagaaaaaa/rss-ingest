import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rss_ingest
from rss_ingest import parse_featured_ids


def test_parse_featured_ids_from_json_text():
    raw = "{" + "\"featured_ids\": [\"rid1\", \"rid2\"]}"
    ids = parse_featured_ids(raw)
    assert ids == ["rid1", "rid2"]


def test_parallel_defaults_exist():
    assert isinstance(rss_ingest.config.LLM_CONCURRENCY, int)
    assert isinstance(rss_ingest.config.PROGRESS_BAR_WIDTH, int)
    assert rss_ingest.config.LLM_CONCURRENCY >= 1
