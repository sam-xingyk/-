from typing import List, Dict, Tuple
import feedparser
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.cache import TTLCache
from app.utils.terms import expand_terms, normalize_text
from difflib import SequenceMatcher


DEFAULT_FEEDS = [
    # 使用 RSSHub 公共实例（免费，可能限流）。控制源数量以提升响应速度。
    "https://rsshub.app/36kr/newsflashes",
    "https://rsshub.app/bbc/chinese",
    # 扩充来源，提高覆盖度（中文为主）
    "https://rsshub.app/ithome/latest",
    "https://rsshub.app/cnbeta",
    "https://rsshub.app/solidot",
    "https://rsshub.app/zhihu/hotlist",
    # 国内资讯进一步扩展（可能存在限流或不稳定）
    "https://rsshub.app/thepaper/featured",
    "https://rsshub.app/ifeng/news",
]

# 5分钟缓存，减少重复拉取
_FEED_CACHE = TTLCache(ttl_seconds=300)


def _get_feed_content(url: str, timeout_seconds: float = 3.0) -> Tuple[str, bytes]:
    """
    返回 (url, content_bytes)。若失败返回 (url, b"").
    使用简单的缓存以降低重复请求带来的速度问题。
    """
    cached = _FEED_CACHE.get(url)
    if cached is not None:
        return url, cached
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.content
        _FEED_CACHE.set(url, content)
        return url, content
    except Exception:
        return url, b""


def _relevance(title: str, summary: str, terms: List[str]) -> Dict:
    """在爬取判断前，基于标题/摘要做快速总结与相关性判断。返回 {related, score, reason, summary}。"""
    t = (title or "")
    s = (summary or "")
    tl = t.lower()
    sl = s.lower()
    # 命中计数与权重
    hit_title = sum(1 for term in terms if term.lower() in tl)
    hit_summary = sum(1 for term in terms if term.lower() in sl)
    # 规范化后模糊相似度
    nt = normalize_text(t)
    ns = normalize_text(s)
    fuzzy = 0.0
    for term in terms:
        try:
            fuzzy = max(fuzzy, SequenceMatcher(None, normalize_text(term), nt).ratio())
            fuzzy = max(fuzzy, SequenceMatcher(None, normalize_text(term), ns).ratio())
        except Exception:
            pass
    score = hit_title * 2 + hit_summary + (fuzzy if fuzzy >= 0.6 else 0)
    related = (hit_title > 0) or (hit_summary > 0) or (fuzzy >= 0.8)
    # 生成用于判断的简要总结（命中句优先）
    sent = ""
    for seg in (s.replace("。", ".").split(".") if s else []):
        if any(term.lower() in seg.lower() for term in terms):
            sent = seg.strip()
            break
    if not sent:
        sent = (s[:180] + "...") if s else (t[:180] + "...")
    reason = f"title_hits={hit_title}, summary_hits={hit_summary}, fuzzy={round(fuzzy,2)}"
    return {"related": related, "score": score, "reason": reason, "summary": sent}


def fetch_rss_items(query: str, max_items: int = 10, feeds: List[str] = None, timeout_seconds: float = 3.0, max_workers: int = 6) -> List[Dict]:
    """
    从若干 RSS 源抓取最新条目，并根据 query 做简单过滤（标题/摘要包含关键字）。
    返回结构：[{title, summary, source, published_at, url}]
    """
    if feeds is None:
        feeds = DEFAULT_FEEDS

    items: List[Dict] = []

    # 并发拉取RSS，显著降低等待时间
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url in feeds:
            futures.append(executor.submit(_get_feed_content, url, timeout_seconds))
        for fut in as_completed(futures):
            try:
                url, content = fut.result()
            except Exception:
                continue
            if not content:
                continue
            parsed = feedparser.parse(content)
            source_title = parsed.feed.get("title", "RSS")
            # 多词匹配（联想主题词）
            terms = expand_terms(query)
            for entry in parsed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                link = entry.get("link", "")
                published = entry.get("published", "") or entry.get("updated", "")
                # 在爬取判断前先总结并判断相关性
                rel = _relevance(title, summary, terms)
                if not rel["related"]:
                    continue

                items.append({
                    "title": title,
                    "summary": summary,
                    "source": source_title,
                    "published_at": published,
                    "url": link,
                    "relevance": rel,
                })
                if len(items) >= max_items:
                    break
            if len(items) >= max_items:
                break

    return items