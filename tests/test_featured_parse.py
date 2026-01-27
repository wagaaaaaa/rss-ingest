import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rss_ingest import parse_featured_ids
import rss_ingest

def test_parse_featured_ids():
    raw = '{"featured_ids": ["rec1", "rec2"]}'
    assert parse_featured_ids(raw) == ["rec1", "rec2"]


def test_parallel_defaults_exist():
    assert isinstance(rss_ingest.config.LLM_CONCURRENCY, int)
    assert isinstance(rss_ingest.config.PROGRESS_BAR_WIDTH, int)
    assert rss_ingest.config.LLM_CONCURRENCY >= 1
