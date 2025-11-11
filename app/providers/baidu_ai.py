import httpx
from typing import List, Dict

BAIDU_AI_SEARCH_ENDPOINT = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"


def search_baidu_ai(query: str, api_key: str, top_k: int = 10, recency: str = "month") -> List[Dict]:
    """
    使用百度智能云千帆的“百度AI搜索”V2接口获取实时网页搜索结果。
    参考文档：
    - https://cloud.baidu.com/doc/qianfan-api/s/Wmbq4z7e5
    - 每日免费额度约100次（需账号开通），鉴权：Bearer <AppBuilder API Key>

    返回统一结构：[{title, summary, source, published_at, url}]
    """
    if not api_key or not query:
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Appbuilder-Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"content": query, "role": "user"}],
        "search_source": "baidu_search_v2",
        "resource_type_filter": [{"type": "web", "top_k": max(1, min(top_k, 20))}],
        "search_recency_filter": recency,
        "stream": False,
        # 关闭深搜索避免一次请求触发多次扣费；如需更多链接可开启。
        "enable_deep_search": False,
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(BAIDU_AI_SEARCH_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    refs = data.get("references") or []
    items: List[Dict] = []
    for r in refs[:top_k]:
        title = r.get("title") or r.get("web_anchor") or ""
        url = r.get("url") or ""
        summary = r.get("content") or ""
        date = r.get("date") or None
        source = r.get("type") or "BaiduAI"
        items.append({
            "title": title,
            "summary": summary,
            "source": source,
            "published_at": date,
            "url": url,
        })
    return items