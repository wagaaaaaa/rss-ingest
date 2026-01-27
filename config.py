# -*- coding: utf-8 -*-
import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(name, value)
    except FileNotFoundError:
        pass

BASE_DIR = Path(__file__).resolve().parent

# Local env file support (optional)
load_env_file(Path(r"F:\coding\local.env"))
load_env_file(Path(r"F:\coding\.env"))

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 飞书 Bitable App（同一应用可包含多个表）
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "")
FEISHU_NEWS_TABLE_ID = os.getenv("FEISHU_NEWS_TABLE_ID", "")
FEISHU_RSS_TABLE_ID = os.getenv("FEISHU_RSS_TABLE_ID", "")
FEISHU_NOTIFY_TABLE_ID = os.getenv("FEISHU_NOTIFY_TABLE_ID", "")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent"

# Cloudflare Vectorize + Workers AI
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_VECTORIZE_INDEX = os.getenv("CF_VECTORIZE_INDEX", "")
CF_VECTORIZE_TOP_K = int(os.getenv("CF_VECTORIZE_TOP_K", "5"))
CF_VECTORIZE_SIM_THRESHOLD = float(os.getenv("CF_VECTORIZE_SIM_THRESHOLD", "0.88"))
CF_VECTORIZE_METRIC = os.getenv("CF_VECTORIZE_METRIC", "cosine")
CF_EMBEDDING_MODEL = os.getenv("CF_EMBEDDING_MODEL", "@cf/baai/bge-m3")
ENABLE_VECTORIZE_DEDUP = os.getenv("ENABLE_VECTORIZE_DEDUP", "true").lower() in {"1", "true", "yes", "y"}

# 新闻表字段
NEWS_FIELD_TITLE = "标题"
NEWS_FIELD_SCORE = "AI打分"
NEWS_FIELD_CATEGORIES = "分类"
NEWS_FIELD_SUMMARY = "总结"
NEWS_FIELD_PUBLISHED_MS = "发布时间"
NEWS_FIELD_SOURCE = "来源"
NEWS_FIELD_FULL_CONTENT = "全文"
NEWS_FIELD_ITEM_KEY = "item_key"
NEWS_FIELD_CREATED_TIME = "创建时间"
NEWS_FIELD_FEATURED = "精选"

# RSS 源表字段
RSS_FIELD_NAME = "name"
RSS_FIELD_FEED_URL = "feed_url"
RSS_FIELD_TYPE = "type"
RSS_FIELD_DESCRIPTION = "description"
RSS_FIELD_ENABLED = "enabled"
RSS_FIELD_STATUS = "status"
RSS_FIELD_LAST_FETCH_TIME = "last_fetch_time"
RSS_FIELD_LAST_FETCH_STATUS = "last_fetch_status"
RSS_FIELD_CONSECUTIVE_FAIL_COUNT = "consecutive_fail_count"
RSS_FIELD_LAST_ITEM_GUID = "last_item_guid"
RSS_FIELD_LAST_ITEM_PUB_TIME = "last_item_pub_time"
RSS_FIELD_ITEM_ID_STRATEGY = "item_id_strategy"
RSS_FIELD_CONTENT_LANGUAGE = "content_language"
RSS_FIELD_FAILED_ITEMS = "failed_items"

DEFAULT_ITEM_ID_STRATEGY = "guid"
DEFAULT_CONTENT_HASH_ALGO = "md5"
DEFAULT_FETCH_INTERVAL_MIN = int(os.getenv("DEFAULT_FETCH_INTERVAL_MIN", "180"))
MAX_ENTRIES_PER_FEED = 200
NEWS_ITEM_KEY_PREFETCH_LIMIT = 500

# 单选字段选项（需与你在表格中设置一致）
STATUS_IDLE = "idle"
STATUS_OK = "ok"
STATUS_UNSTABLE = "unstable"
STATUS_DEAD = "dead"
STATUS_OPTIONS = {STATUS_IDLE, STATUS_OK, STATUS_UNSTABLE, STATUS_DEAD}

FETCH_STATUS_SUCCESS = "success"
FETCH_STATUS_TIMEOUT = "timeout"
FETCH_STATUS_HTTP_ERROR = "http_error"
FETCH_STATUS_PARSE_ERROR = "parse_error"
FETCH_STATUS_OPTIONS = {FETCH_STATUS_SUCCESS, FETCH_STATUS_TIMEOUT, FETCH_STATUS_HTTP_ERROR, FETCH_STATUS_PARSE_ERROR}

ITEM_ID_STRATEGY_OPTIONS = {"guid", "link", "title_pubdate", "content_hash"}
CONTENT_LANGUAGE_OPTIONS = {"zh", "en", "jp", "mixed", "other"}

HTTP_TIMEOUT = 20
HTTP_RETRIES = 3

GEMINI_TIMEOUT = 60
GEMINI_RETRIES = 10
FEISHU_MIN_SCORE = 6.0
FAILED_ITEMS_MAX = int(os.getenv("FAILED_ITEMS_MAX", "50"))
FAILED_ITEMS_RETRY_LIMIT = int(os.getenv("FAILED_ITEMS_RETRY_LIMIT", "5"))
FAILED_ITEMS_MAX_AGE_DAYS = int(os.getenv("FAILED_ITEMS_MAX_AGE_DAYS", "7"))
FAILED_ITEMS_MAX_MISS = int(os.getenv("FAILED_ITEMS_MAX_MISS", "3"))
NVIDIA_RETRIES = int(os.getenv("NVIDIA_RETRIES", "10"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia").strip().lower()
IFLOW_API_KEY = os.getenv("IFLOW_API_KEY", "")
IFLOW_BASE_URL = os.getenv("IFLOW_BASE_URL", "https://apis.iflow.cn/v1").rstrip("/")
IFLOW_MODEL = os.getenv("IFLOW_MODEL", "qwen3-max")
IFLOW_TIMEOUT = int(os.getenv("IFLOW_TIMEOUT", "60"))
IFLOW_RETRIES = int(os.getenv("IFLOW_RETRIES", "10"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))
OPENAI_RETRIES = int(os.getenv("OPENAI_RETRIES", "10"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "60"))
DEEPSEEK_RETRIES = int(os.getenv("DEEPSEEK_RETRIES", "10"))

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4.7")
ZHIPU_TIMEOUT = int(os.getenv("ZHIPU_TIMEOUT", "60"))
ZHIPU_RETRIES = int(os.getenv("ZHIPU_RETRIES", "10"))

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

NOTIFY_FIELD_EVENT = os.getenv("NOTIFY_FIELD_EVENT", "事件")
NOTIFY_FIELD_DETAIL = os.getenv("NOTIFY_FIELD_DETAIL", "详情")
NOTIFY_FIELD_PLAIN = os.getenv("NOTIFY_FIELD_PLAIN", "说明")
NOTIFY_FIELD_TRIGGER_TIME = os.getenv("NOTIFY_FIELD_TRIGGER_TIME", "触发时间")
NOTIFY_FIELD_NOTIFIED = os.getenv("NOTIFY_FIELD_NOTIFIED", "已通知")

SYSTEM_PROMPT_OVERRIDE = os.getenv("SYSTEM_PROMPT_OVERRIDE", "")
