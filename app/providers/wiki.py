import httpx
from typing import List, Dict


WIKI_ENDPOINT = "https://zh.wikipedia.org/w/api.php"


def search_wiki(query: str, num: int = 6) -> List[Dict]:
    """
    使用中文维基百科搜索 API，返回页面 URL 与摘要（snippet）。
    返回结构：[{title, summary, source, published_at, url}]
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": num,
        "utf8": 1,
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(WIKI_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    results = data.get("query", {}).get("search", [])
    items: List[Dict] = []
    for r in results[:num]:
        title = r.get("title", "")
        snippet = r.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
        url = f"https://zh.wikipedia.org/wiki/{title}"
        items.append({
            "title": title,
            "summary": snippet,
            "source": "Wikipedia",
            "published_at": None,
            "url": url,
        })
    return items