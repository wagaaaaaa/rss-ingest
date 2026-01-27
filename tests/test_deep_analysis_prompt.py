from deep_analysis import build_deep_analysis_prompt


def test_build_deep_analysis_prompt_includes_time():
    prompt = build_deep_analysis_prompt("正文")
    assert "你所处的时间为" in prompt
