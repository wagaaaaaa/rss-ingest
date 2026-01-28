import importlib
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def reload_config(env):
    for key in list(os.environ.keys()):
        if key.startswith("LLM_") or key.startswith("QWEN_") or key.startswith("GEMINI_"):
            os.environ.pop(key, None)
    os.environ.update(env)
    if "config" in sys.modules:
        del sys.modules["config"]
    import config
    importlib.reload(config)
    return config


def test_defaults_keep_qwen_and_concurrency_defaults():
    cfg = reload_config({})
    assert cfg.LLM_CONCURRENCY == 4
    assert cfg.LLM_PROVIDER == "nvidia"
