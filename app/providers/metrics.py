from typing import Optional
import httpx
from datetime import datetime, timedelta
from urllib.parse import quote
from app.utils.cache import TTLCache

_METRIC_CACHE = TTLCache(ttl_seconds=600)


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=days)
    return (start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))


def wiki_pageviews(title: str, days: int = 30, lang: str = "zh") -> Optional[int]:
    """
    使用 Wikimedia Pageviews API 获取近 N 天的页面浏览量总计。
    参考：/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}
    project 例如 zh.wikipedia
    """
    if not title:
        return None
    start, end = _date_range(days)
    article = quote(title, safe="")
    project = f"{lang}.wikipedia"
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{project}/all-access/user/{article}/daily/{start}/{end}"
    )

    cache_key = f"pageviews:{project}:{article}:{start}:{end}"
    cached = _METRIC_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    items = data.get("items", [])
    total = sum(it.get("views", 0) for it in items)
    _METRIC_CACHE.set(cache_key, total)
    return total