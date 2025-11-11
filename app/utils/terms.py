from typing import List
import re

_re_punct = re.compile(r"[\s#·・\-—_，,。\.！!？\?、/\\:：;；\[\]\(\)【】『』“”\"']+")

def normalize_text(text: str) -> str:
    """Lowercase and remove common punctuation and hashtag markers."""
    t = (text or "").strip().lower()
    if not t:
        return ""
    return _re_punct.sub("", t)

def expand_terms(query: str) -> List[str]:
    """
    Lightweight synonym and variant expansion for Chinese/English mixed topics.
    - Original query
    - Remove common suffixes/modifiers (e.g., "是什么", "怎么回事", "最新消息")
    - Split into sub tokens
    - Known brand aliases (e.g., XPENG/XPEV)
    """
    q = (query or "").strip()
    terms: List[str] = []
    if not q:
        return terms

    terms.append(q)
    # remove common modifiers
    cleaned = _re_punct.sub(" ", q)
    for w in ["是什么", "怎么回事", "最新消息", "最新", "事件", "热搜", "曝光", "官宣", "发布会", "发布", "涨价", "降价"]:
        cleaned = cleaned.replace(w, "")
    cq = cleaned.strip()
    if cq and cq != q:
        terms.append(cq)
    for tok in cq.split():
        if tok and tok not in terms:
            terms.append(tok)

    low = q.lower()
    # sample brand alias expansion (extend as needed)
    if "小鹏" in q:
        terms.extend(["小鹏汽车", "xpeng", "xpev", "xpeng motors"]) 
    if any(t in low for t in ["xpeng", "xpev"]):
        terms.extend(["XPENG", "XPEV", "xpeng motors"]) 

    # deduplicate keep order
    seen = set()
    dedup = []
    for t in terms:
        if t not in seen:
            dedup.append(t)
            seen.add(t)
    return dedup