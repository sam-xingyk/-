from typing import Dict, List
import re
from difflib import SequenceMatcher
import httpx
import feedparser
from app.utils.cache import TTLCache
from app.utils.terms import expand_terms, normalize_text

_TREND_CACHE = TTLCache(ttl_seconds=300)


TREND_FEEDS = {
    # 微博热搜与热榜都尝试，提高命中率
    "weibo": "https://rsshub.app/weibo/search/hot",
    "weibo_hot": "https://rsshub.app/weibo/hot",
    "zhihu": "https://rsshub.app/zhihu/hotlist",
    "bilibili": "https://rsshub.app/bilibili/hot",
    # 扩展平台（若 RSSHub 源不可用会自动忽略）
    "sina": "https://rsshub.app/sina/news",
    "toutiao": "https://rsshub.app/toutiao/today",
    "douyin": "https://rsshub.app/douyin/hot",
    "xiaohongshu": "https://rsshub.app/xiaohongshu/explore",
}


def _fetch_entries(feed_url: str, timeout: float = 5.0) -> List[Dict]:
    cached = _TREND_CACHE.get(feed_url)
    if cached is not None:
        parsed = feedparser.parse(cached)
    else:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(feed_url)
                resp.raise_for_status()
                content = resp.content
            _TREND_CACHE.set(feed_url, content)
            parsed = feedparser.parse(content)
        except Exception:
            return []
    entries = []
    for e in getattr(parsed, "entries", []):
        entries.append({
            "title": e.get("title", ""),
            "link": e.get("link", ""),
        })
    return entries


_re_punct = re.compile(r"[\s#·・\-—_，,。\.！!？\?、/\\:：;；\[\]\(\)【】『』“”\"']+")

def _match_title(title: str, terms: List[str]) -> bool:
    tl = (title or "").lower()
    if not tl:
        return False
    # 直接包含匹配
    if terms and any(term.lower() in tl for term in terms):
        return True
    # 规范化后再匹配（处理#话题#、空格/标点差异）
    nt = normalize_text(title)
    for term in terms:
        if normalize_text(term) in nt:
            return True
        # 模糊匹配：相似度阈值（提升容错）
        try:
            if SequenceMatcher(None, normalize_text(term), nt).ratio() >= 0.8:
                return True
        except Exception:
            pass
    return False


def _expand_terms(query: str) -> List[str]:
    """轻量同义词与变体扩展：
    - 原始查询
    - 去除常见修饰/尾缀（如“是什么”“怎么回事”“最新消息”等）
    - 按空格/标点拆分的子词
    - 针对常见英文别名（如 XPENG/XPEV）做大小写与缩写扩展
    """
    q = (query or "").strip()
    terms: List[str] = []
    if q:
        terms.append(q)
        # 去除常见中文尾缀/修饰词
        cleaned = _re_punct.sub(" ", q)
        cleaned = cleaned.replace("是什么", "").replace("怎么回事", "")
        cleaned = cleaned.replace("最新消息", "").replace("最新", "")
        cleaned = cleaned.replace("事件", "").replace("热搜", "")
        cleaned = cleaned.replace("曝光", "").replace("官宣", "")
        cleaned = cleaned.replace("发布会", "").replace("发布", "")
        cleaned = cleaned.replace("涨价", "").replace("降价", "")
        cq = cleaned.strip()
        if cq and cq != q:
            terms.append(cq)
        # 拆分子词（中英文混合场景、包含空格的品牌名等）
        for tok in cq.split():
            if tok and tok not in terms:
                terms.append(tok)

        low = q.lower()
        if "小鹏" in q:
            terms.extend(["小鹏汽车", "xpeng", "xpev", "xpeng motors"]) 
        if any(t in low for t in ["xpeng", "xpev"]):
            terms.extend(["XPENG", "XPEV", "xpeng motors"]) 
    # 去重保持顺序
    seen = set()
    dedup = []
    for t in terms:
        if t not in seen:
            dedup.append(t)
            seen.add(t)
    return dedup


def trending_presence(query: str) -> Dict:
    """
    在各平台热榜中检测是否存在与 query 相关的条目。
    返回：{platform: {present: bool, matched: [titles...]}}
    """
    q = (query or "").strip().lower()
    terms = expand_terms(query)
    result = {}
    for platform, url in TREND_FEEDS.items():
        entries = _fetch_entries(url)
        matched_titles: List[str] = []
        matched_items: List[Dict] = []
        if q:
            for it in entries:
                t = it.get("title", "")
                if _match_title(t, terms or [q]):
                    matched_titles.append(t)
                    matched_items.append(it)
        result[platform] = {
            "present": bool(matched_titles),
            "matched": matched_titles,
            "matched_items": matched_items,
        }
    return result