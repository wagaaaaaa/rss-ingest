from rss_ingest import parse_featured_ids


def test_parse_featured_ids():
    raw = '{"featured_ids": ["rec1", "rec2"]}'
    assert parse_featured_ids(raw) == ["rec1", "rec2"]
