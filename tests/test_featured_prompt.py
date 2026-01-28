import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rss_ingest


def test_build_featured_prompt_uses_override(monkeypatch):
    monkeypatch.setattr(rss_ingest.config, "FEATURED_PROMPT", "OVERRIDE")
    items = [{"record_id": "r1", "title": "t", "summary": "s"}]
    prompt = rss_ingest.build_featured_prompt(items)
    assert prompt.startswith("OVERRIDE")
