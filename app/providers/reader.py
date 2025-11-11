from typing import Optional, List, Dict
import httpx
from urllib.parse import quote
from app.utils.cache import TTLCache
from concurrent.futures import ThreadPoolExecutor, as_completed

# 使用 Jina Reader 的公开端点，无需 API Key
# 参考：对任意URL使用 r.jina.ai 获取提取后的纯文本
# e.g. https://r.jina.ai/http://example.com

_READ_CACHE = TTLCache(ttl_seconds=600)  # 10分钟缓存


def fetch_content(url: str, timeout_seconds: float = 6.0, max_chars: int = 4000) -> Optional[str]:
    if not url:
        return None

    cached = _READ_CACHE.get(url)
    if cached is not None:
        return cached

    try:
        # 兼容http/https，进行URL编码
        encoded = quote(url, safe="/:?&=%#")
        reader_url = f"https://r.jina.ai/{encoded}"
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(reader_url)
            resp.raise_for_status()
            text = resp.text
            if not text:
                return None
            # 截断以避免极长内容影响性能
            text = text[:max_chars]
            _READ_CACHE.set(url, text)
            return text
    except Exception:
        return None


def fetch_contents_bulk(urls: List[str], timeout_seconds: float = 4.0, max_chars: int = 4000, max_workers: int = 6) -> Dict[str, Optional[str]]:
    """
    并发批量拉取正文，提升整体速度；自动复用缓存。
    返回：{url: content or None}
    """
    results: Dict[str, Optional[str]] = {}
    # 先尝试命中缓存，减少网络请求
    pending: List[str] = []
    for u in urls:
        cached = _READ_CACHE.get(u)
        if cached is not None:
            results[u] = cached
        else:
            pending.append(u)

    if not pending:
        return results

    def _task(u: str) -> Optional[str]:
        try:
            encoded = quote(u, safe="/:?&=%#")
            reader_url = f"https://r.jina.ai/{encoded}"
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.get(reader_url)
                resp.raise_for_status()
                text = resp.text
                if not text:
                    return None
                text = text[:max_chars]
                _READ_CACHE.set(u, text)
                return text
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_task, u): u for u in pending}
        for fut in as_completed(future_map):
            u = future_map[fut]
            try:
                results[u] = fut.result()
            except Exception:
                results[u] = None

    return results