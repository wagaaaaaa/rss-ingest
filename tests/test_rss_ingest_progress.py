import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rss_ingest import render_progress


def test_render_progress_basic():
    assert render_progress(0, 0, width=4) == "0/0 [....]"
    assert render_progress(1, 2, width=4) == "1/2 [##..]"
