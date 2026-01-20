# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 飞书 Bitable App（同一应用可包含多个表）
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "")
FEISHU_NEWS_TABLE_ID = os.getenv("FEISHU_NEWS_TABLE_ID", "")
FEISHU_RSS_TABLE_ID = os.getenv("FEISHU_RSS_TABLE_ID", "")

# FreshRSS（如不使用可留空）
FRESHRSS_URL = os.getenv("FRESHRSS_URL", "")
FRESHRSS_USERNAME = os.getenv("FRESHRSS_USERNAME", "")
FRESHRSS_API_PASSWORD = os.getenv("FRESHRSS_API_PASSWORD", "")

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

DEFAULT_ITEM_ID_STRATEGY = "guid"
DEFAULT_CONTENT_HASH_ALGO = "md5"
DEFAULT_FETCH_INTERVAL_MIN = 60
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
GEMINI_RETRIES = 3
FEISHU_MIN_SCORE = 6.0

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
IFLOW_API_KEY = os.getenv("IFLOW_API_KEY", "")
IFLOW_BASE_URL = os.getenv("IFLOW_BASE_URL", "https://apis.iflow.cn/v1").rstrip("/")
IFLOW_MODEL = os.getenv("IFLOW_MODEL", "qwen3-max")
IFLOW_TIMEOUT = int(os.getenv("IFLOW_TIMEOUT", "60"))
IFLOW_RETRIES = int(os.getenv("IFLOW_RETRIES", "3"))
