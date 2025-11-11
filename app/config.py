import os
from dotenv import load_dotenv


# 加载 .env 文件（如果存在）
load_dotenv()


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def serper_api_key() -> str:
    return get_env("SERPER_API_KEY", "")


def baidu_appbuilder_api_key() -> str:
    """百度智能云千帆 AppBuilder 的 API Key，用于 AI 搜索调用。"""
    return get_env("BAIDU_APPBUILDER_API_KEY", "")


# Meilisearch 配置
def meili_url() -> str:
    return get_env("MEILISEARCH_URL", "")


def meili_api_key() -> str:
    return get_env("MEILISEARCH_API_KEY", "")