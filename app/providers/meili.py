from typing import List, Dict, Optional
import hashlib
from meilisearch import Client
from app.config import meili_url, meili_api_key


INDEX_NAME = "documents"


def _client() -> Optional[Client]:
    url = meili_url()
    if not url:
        return None
    key = meili_api_key()
    try:
        return Client(url, key or None)
    except Exception:
        return None


def ensure_index():
    client = _client()
    if not client:
        return False
    try:
        indexes = client.get_indexes()
        if not any(ix.get("uid") == INDEX_NAME for ix in indexes.get("results", [])):
            client.create_index(uid=INDEX_NAME, options={"primaryKey": "id"})
        # 可选：设置可搜索字段与可过滤字段
        client.index(INDEX_NAME).update_settings({
            "searchableAttributes": ["title", "summary", "content", "source_domain", "topic"],
            "filterableAttributes": ["topic", "source_domain", "published_at"],
            "sortableAttributes": ["published_at", "fetch_time"],
        })
        return True
    except Exception:
        return False


def _doc_id(url: str) -> str:
    return hashlib.sha1((url or "").encode("utf-8")).hexdigest()


def upsert_documents(items: List[Dict], topic: str) -> bool:
    """
    将素材写入 Meilisearch。
    文档结构：{id, title, summary, content, source_domain, published_at, fetch_time, url, topic}
    """
    client = _client()
    if not client:
        return False
    try:
        ensure_index()
        docs = []
        for it in items:
            url = it.get("url") or ""
            if not url:
                continue
            doc = {
                "id": _doc_id(url),
                "title": it.get("title") or "",
                "summary": it.get("summary") or "",
                "content": it.get("content") or "",
                "source_domain": it.get("source_domain") or "",
                "published_at": it.get("published_at"),
                "fetch_time": it.get("fetch_time"),
                "url": url,
                "topic": topic,
            }
            docs.append(doc)
        if not docs:
            return True
        client.index(INDEX_NAME).add_documents(docs)
        return True
    except Exception:
        return False


def search_documents(query: str, limit: int = 10, filter_topic: Optional[str] = None) -> List[Dict]:
    """
    从 Meilisearch 搜索文档，返回与 QueryAgent 统一的 items 结构。
    """
    client = _client()
    if not client or not query:
        return []
    try:
        ensure_index()
        params = {
            "limit": limit,
        }
        if filter_topic:
            params["filter"] = [f"topic = '{filter_topic}'"]
        res = client.index(INDEX_NAME).search(query, params)
        hits = res.get("hits", [])
        items: List[Dict] = []
        for h in hits:
            items.append({
                "title": h.get("title") or "",
                "summary": h.get("summary") or "",
                "source": h.get("source_domain") or "Meilisearch",
                "published_at": h.get("published_at"),
                "url": h.get("url") or "",
                "content": h.get("content") or "",
            })
        return items
    except Exception:
        return []