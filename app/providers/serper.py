import httpx
from typing import List, Dict


SERPER_ENDPOINT = "https://google.serper.dev/search"


def search_serper(query: str, api_key: str, num: int = 6, gl: str = "cn", hl: str = "zh-cn") -> List[Dict]:
    """
    使用 Serper.dev 的 Google Search API 进行联网搜索。

    返回统一结构：[{title, summary, source, published_at, url}]
    """
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "gl": gl, "hl": hl}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(SERPER_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    items: List[Dict] = []

    # 优先 web results
    web_results = data.get("organic", []) or data.get("search", []) or []
    for r in web_results[:num]:
        items.append({
            "title": r.get("title") or r.get("name") or "",
            "summary": r.get("snippet") or r.get("description") or "",
            "source": r.get("domain") or r.get("source") or "Serper",
            "published_at": r.get("date") or None,
            "url": r.get("link") or r.get("url") or "",
        })

    return items