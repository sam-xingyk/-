from .agents.query_agent import QueryAgent
from .agents.report_agent import ReportAgent
from .providers.reader import fetch_content, fetch_contents_bulk
from datetime import datetime
from urllib.parse import urlparse
from .providers.metrics import wiki_pageviews
from .providers.trending import trending_presence
from app.config import trend_platform_whitelist
from app.utils.terms import normalize_text, expand_terms
from .providers.meili import upsert_documents
from collections import defaultdict


class Orchestrator:
    """
    轻量编排器：
    - 调用 QueryAgent 获取素材（默认使用模拟数据）
    - 调用 ReportAgent 生成报告结构
    """

    def __init__(self):
        self.query_agent = QueryAgent()
        self.report_agent = ReportAgent()

    def analyze(self, topic: str, max_items: int = 12, use_mock: bool = False, source: str = "rss", fast: bool = False):
        items = self.query_agent.search(topic=topic, max_items=max_items, use_mock=use_mock, source=source)
        now_iso = datetime.now().isoformat(timespec="seconds")
        # 丰富素材的审计信息：来源域名 & 抓取时间
        for it in items:
            url = it.get("url")
            if url:
                try:
                    it["source_domain"] = urlparse(url).netloc
                except Exception:
                    it["source_domain"] = None
            it["fetch_time"] = now_iso

        # 为前N条素材并发拉取正文内容（快速模式缩短超时与截断）
        top_n = 6 if fast else 10
        timeout_s = 3.0 if fast else 4.0
        max_chars = 2500 if fast else 4000
        to_fetch = [it.get("url") for it in items[:top_n] if it.get("url") and not it.get("content")]
        if to_fetch:
            bulk = fetch_contents_bulk(to_fetch, timeout_seconds=timeout_s, max_chars=max_chars, max_workers=6)
            for it in items[:top_n]:
                url = it.get("url")
                if url and not it.get("content"):
                    content = bulk.get(url)
                    if content:
                        it["content"] = content

        report = self.report_agent.generate_report(topic=topic, items=items)
        # 数据指标：页面浏览量（维基）与平台热榜出现情况
        pv_zh = wiki_pageviews(topic, days=30, lang="zh")
        pv_en = wiki_pageviews(topic, days=30, lang="en")
        trend = trending_presence(topic)
        wl = trend_platform_whitelist()

        # 追加报告元信息与KPI
        total_text_len = sum(
            len(
                (
                    it.get("content")
                    or it.get("summary")
                    or it.get("title")
                    or ""
                )
            )
            for it in items
        )
        domain_count = len({it.get("source_domain") for it in items if it.get("source_domain")})
        # 按域名动态分布（更通用）
        domain_counts = defaultdict(int)
        for it in items:
            dom = (it.get("source_domain") or "").lower()
            if dom:
                domain_counts[dom] += 1
        report["generated_at"] = now_iso
        report["stats"] = {
            "item_count": len(items),
            "domain_count": domain_count,
            "total_text_len": total_text_len,
        }
        # 衍生指标（用于顶部大KPI展示）
        reads_total_proxy = (pv_zh or 0) + (pv_en or 0)
        # 聚合微博两个来源（search/hot 与 hot）
        weibo_items_agg = (
            trend.get("weibo", {}).get("matched_items", [])
            + trend.get("weibo_hot", {}).get("matched_items", [])
        )
        zhihu_items = trend.get("zhihu", {}).get("matched_items", [])
        bilibili_items = trend.get("bilibili", {}).get("matched_items", [])
        # 扩展平台
        sina_items = trend.get("sina", {}).get("matched_items", [])
        toutiao_items = trend.get("toutiao", {}).get("matched_items", [])
        douyin_items = trend.get("douyin", {}).get("matched_items", [])
        xhs_items = trend.get("xiaohongshu", {}).get("matched_items", [])
        interactions_proxy = (
            len(weibo_items_agg) + len(zhihu_items) + len(bilibili_items)
            + len(sina_items) + len(toutiao_items) + len(douyin_items) + len(xhs_items)
        )
        platform_max = max(domain_counts.values()) if domain_counts else 1

        # 交叉平台重合：对各平台热榜标题进行规范化，统计跨平台重复出现的热点
        try:
            norm_map = defaultdict(lambda: {"platforms": set(), "sample_title": ""})
            for plat, data in trend.items():
                items_list = data.get("matched_items", [])
                for it in items_list:
                    t = it.get("title", "")
                    nt = normalize_text(t)
                    if not nt:
                        continue
                    norm_map[nt]["platforms"].add(plat)
                    if not norm_map[nt]["sample_title"]:
                        norm_map[nt]["sample_title"] = t
            overlaps = []
            for nt, info in norm_map.items():
                plats = sorted(list(info["platforms"]))
                if len(plats) >= 2:
                    overlaps.append({"title": info["sample_title"], "platforms": plats})
            overlaps = sorted(overlaps, key=lambda x: len(x["platforms"]), reverse=True)[:8]
        except Exception:
            overlaps = []

        # RSS 相关性评分的简单统计
        try:
            rel_scores_raw = [it.get("relevance", {}).get("score", 0.0) for it in items if it.get("relevance")]
            rel_avg = round(sum(rel_scores_raw) / len(rel_scores_raw), 2) if rel_scores_raw else None
            # 归一化到 0-1 区间用于分布展示（假设分数 0-4 为常见范围）
            rel_scores = [min(max(s / 4.0, 0.0), 1.0) for s in rel_scores_raw]
            # 直方图分箱
            bins_def = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
            bins = []
            for lo, hi in bins_def:
                cnt = sum(1 for s in rel_scores if (s >= lo and s < hi))
                rng = f"{round(lo,1)}-{round(hi if hi<=1.0 else 1.0,1)}"
                bins.append({"range": rng, "count": cnt})
            hist_max = max([b["count"] for b in bins]) if bins else 1
            rel_reasons = [it.get("relevance", {}).get("reason", "") for it in items if it.get("relevance")][:5]
        except Exception:
            rel_avg = None
            rel_reasons = []
            bins = []
            hist_max = 1

        report["metrics"] = {
            "wiki_pageviews_zh": pv_zh,
            "wiki_pageviews_en": pv_en,
            "rss_mentions_count": len(items),
            "trending": trend,
            "platform_whitelist": wl,
            # 顶部KPI使用的统计值
            "trending_counts": {
                # 微博取聚合后的条数，避免仅在综合热榜出现时被误判未出现
                "weibo": len(weibo_items_agg),
                "zhihu": len(zhihu_items),
                "bilibili": len(bilibili_items),
                "sina": len(sina_items),
                "toutiao": len(toutiao_items),
                "douyin": len(douyin_items),
                "xiaohongshu": len(xhs_items),
            },
            # 汇总后的条目列表，供模板展示
            "trending_agg": {
                "weibo_items": weibo_items_agg,
                "zhihu_items": zhihu_items,
                "bilibili_items": bilibili_items,
                "sina_items": sina_items,
                "toutiao_items": toutiao_items,
                "douyin_items": douyin_items,
                "xiaohongshu_items": xhs_items,
            },
            # 免费RSS通常不提供点赞/播放的精确值，这里预留字段（N/A）
            "likes_estimate": None,
            "views_estimate": None,
            # 域名素材命中统计（用于可视化分布）
            "domain_counts": dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "domain_max_count": platform_max,
            # 代理指标：阅读与互动
            "reads_total_proxy": reads_total_proxy,
            "interactions_proxy": interactions_proxy,
            # 数据分析增强
            "analysis": {
                "platform_coverage": {
                    "present_count": sum(1 for p, c in {
                        "weibo": len(weibo_items_agg),
                        "zhihu": len(zhihu_items),
                        "bilibili": len(bilibili_items),
                        "sina": len(sina_items),
                        "toutiao": len(toutiao_items),
                        "douyin": len(douyin_items),
                        "xiaohongshu": len(xhs_items),
                    }.items() if c > 0),
                    "total_whitelisted": len(wl or []),
                },
                "overlaps": overlaps,
                "rss_relevance_avg": rel_avg,
                "rss_relevance_samples": rel_reasons,
                "rss_relevance_hist": {
                    "bins": bins,
                    "max_count": hist_max,
                },
            },
        }

        # 索引入库：便于后续高频检索
        try:
            upsert_documents(items, topic=topic)
        except Exception:
            pass

        # 生成近14天按日时间序列（使用 published_at 或 fetch_time）
        try:
            def to_date(s: str) -> str:
                if not s:
                    return ""
                # 尝试截取 YYYY-MM-DD
                if len(s) >= 10 and s[4] == '-' and s[7] == '-':
                    return s[:10]
                # 处理形如 20240601 或含T的ISO格式
                if 'T' in s and '-' in s:
                    return s.split('T')[0]
                if len(s) == 8 and s.isdigit():
                    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
                return ""

            daily = defaultdict(int)
            for it in items:
                d = to_date(it.get("published_at") or it.get("fetch_time") or "")
                if d:
                    daily[d] += 1
            # 仅保留最近14天，按日期升序
            recent = sorted(daily.items(), key=lambda x: x[0])[-14:]
            timeseries = [{"date": d, "count": c} for d, c in recent]
            ts_max = max([c for _, c in recent]) if recent else 1
            report["metrics"]["timeseries_daily"] = timeseries
            report["metrics"]["timeseries_max_count"] = ts_max
        except Exception:
            report["metrics"]["timeseries_daily"] = []
            report["metrics"]["timeseries_max_count"] = 1
        return report