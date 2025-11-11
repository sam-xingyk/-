from datetime import datetime, timedelta
from typing import List, Dict
from app.config import serper_api_key, baidu_appbuilder_api_key
from app.providers.serper import search_serper
from app.providers.rss import fetch_rss_items
from app.providers.wiki import search_wiki
from app.providers.baidu_ai import search_baidu_ai
from app.providers.meili import search_documents
from urllib.parse import quote


class QueryAgent:
    """
    查询代理（POC 版）：
    - 默认返回模拟数据，避免不合规抓取。
    - 未来可以替换为合规的数据源（RSS、官方 API、内部库）。
    """

    def search(self, topic: str, max_items: int = 6, use_mock: bool = False, source: str = "rss") -> List[Dict]:
        """
        获取真实数据 URL：
        - source='rss'：从免费 RSS 源（含 RSSHub 公共实例）拉取并按 query 过滤
        - source='wiki'：从中文维基百科搜索 API 获取页面 URL
        - source='serper'：使用 Serper.dev 搜索（需要 SERPER_API_KEY）
        """
        # 若已配置自建索引，优先从索引检索
        try:
            indexed_items = search_documents(query=topic, limit=max_items, filter_topic=topic)
            if indexed_items:
                return indexed_items[:max_items]
        except Exception:
            pass

        if source == "rss":
            # 基于中文维基做联想扩展，提升相关素材覆盖
            wiki_related = search_wiki(query=topic, num=5)
            related_terms = [topic]
            for w in wiki_related[:3]:
                t = (w.get("title") or "").strip()
                if t and t not in related_terms:
                    related_terms.append(t)

            aggregated: List[Dict] = []
            per_term_limit = max(2, max_items // max(1, len(related_terms)))
            for term in related_terms:
                term_items = fetch_rss_items(query=term, max_items=per_term_limit)
                # 追加并去重（按URL）
                for it in term_items:
                    if it.get("url") and all(it.get("url") != x.get("url") for x in aggregated):
                        aggregated.append(it)
                if len(aggregated) >= max_items:
                    break

            # 若聚合仍为空，优先使用百度AI搜索（若已配置），再回退到wiki；都无则返回最新RSS（不筛选）
            if not aggregated:
                baidu_key = baidu_appbuilder_api_key()
                if baidu_key:
                    baidu_items = search_baidu_ai(topic, api_key=baidu_key, top_k=max_items)
                    if baidu_items:
                        return baidu_items
                wiki_items = search_wiki(query=topic, num=max_items)
                if wiki_items:
                    return wiki_items
                return fetch_rss_items(query="", max_items=max_items)
            return aggregated[:max_items]
        elif source == "wiki":
            return search_wiki(query=topic, num=max_items)
        elif source == "jina":
            # 仅使用 Jina Reader：不做搜索，只构造维基百科页面URL供后续正文抽取
            enc = quote(topic, safe="")
            items: List[Dict] = []
            items.append({
                "title": f"维基百科：{topic}",
                "summary": "",
                "source": "Jina Reader",
                "published_at": None,
                "url": f"https://zh.wikipedia.org/wiki/{enc}",
            })
            # 备用英文维基
            items.append({
                "title": f"Wikipedia: {topic}",
                "summary": "",
                "source": "Jina Reader",
                "published_at": None,
                "url": f"https://en.wikipedia.org/wiki/{enc}",
            })
            return items[:max_items]
        elif source == "serper":
            api_key = serper_api_key()
            if not api_key:
                return []
            return search_serper(topic, api_key=api_key, num=max_items)
        elif source == "baidu":
            api_key = baidu_appbuilder_api_key()
            if not api_key:
                return []
            return search_baidu_ai(topic, api_key=api_key, top_k=max_items)

        # 默认兜底：RSS；若配置了百度AI搜索则增强兜底
        api_key = baidu_appbuilder_api_key()
        if api_key:
            items = search_baidu_ai(topic, api_key=api_key, top_k=max_items)
            if items:
                return items
        return fetch_rss_items(query=topic, max_items=max_items)