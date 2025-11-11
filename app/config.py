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


# 平台白名单配置（用于热榜抓取与展示）
def trend_platform_whitelist() -> list[str]:
    """
    从环境变量 TREND_PLATFORM_WHITELIST 读取平台白名单，逗号分隔。
    默认启用：weibo,weibo_hot,zhihu,bilibili,sina,toutiao,douyin,xiaohongshu
    """
    default = "weibo,weibo_hot,zhihu,bilibili,sina,toutiao,douyin,xiaohongshu"
    raw = get_env("TREND_PLATFORM_WHITELIST", default)
    parts = [p.strip().lower() for p in (raw or "").split(",") if p.strip()]
    # 去重保持顺序
    seen = set()
    wl = []
    for p in parts:
        if p not in seen:
            wl.append(p)
            seen.add(p)
    return wl