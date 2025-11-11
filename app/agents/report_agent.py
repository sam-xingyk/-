from typing import List, Dict
from collections import Counter
import re


class ReportAgent:
    """
    报告生成代理（POC 版）：
    - 关键词统计（基于简单分词/规则）
    - 倾向性（正/负词表的粗略比例）
    - 摘要与建议（规则模板）
    """

    POSITIVE_WORDS = {"好", "赞", "提升", "优化", "便捷", "高效", "可靠", "满意", "支持"}
    NEGATIVE_WORDS = {"差", "贵", "复杂", "问题", "故障", "不满", "质疑", "风险", "延迟"}

    def _tokenize(self, text: str) -> List[str]:
        # 极简中文切词：按非中文字符做分割
        tokens = re.findall(r"[\u4e00-\u9fff]{1,}", text)
        return tokens

    def _extract_keywords(self, items: List[Dict], top_k: int = 10) -> List[Dict]:
        c = Counter()
        for it in items:
            # 优先使用正文，其次摘要，再次标题
            for field in [it.get("content", ""), it.get("summary", ""), it.get("title", "")]:
                for t in self._tokenize(field):
                    if len(t) >= 2:
                        c[t] += 1
        most = c.most_common(top_k)
        return [{"word": w, "count": cnt} for w, cnt in most]

    def _sentiment_score(self, items: List[Dict]) -> Dict:
        pos, neg = 0, 0
        for it in items:
            text = (it.get("content", "") or (it.get("title", "") + " " + it.get("summary", "")))
            tokens = set(self._tokenize(text))
            pos += len(tokens & self.POSITIVE_WORDS)
            neg += len(tokens & self.NEGATIVE_WORDS)
        total = max(pos + neg, 1)
        score = (pos - neg) / total
        tendency = "偏积极" if score > 0.2 else ("偏消极" if score < -0.2 else "中性")
        return {"positive": pos, "negative": neg, "score": round(score, 3), "tendency": tendency}

    def _make_summary(self, topic: str, items: List[Dict]) -> str:
        if not items:
            return f"围绕‘{topic}’暂未检索到有效素材，建议补充数据源或扩大时间窗口。"
        first_titles = "；".join(it.get("title", "") for it in items[:2])
        return (
            f"围绕‘{topic}’，近期讨论热度有所提升，主要观点覆盖行业趋势、用户反馈与合规关注等方面。"
            f"代表性素材包括：{first_titles}。总体来看，需结合更多一手数据完善结论。"
        )

    def _make_actions(self, topic: str, sentiment: Dict) -> List[str]:
        actions = [
            f"建立‘{topic}’的合规数据采集通道（RSS/官方API/内部库），完善样本覆盖。",
            "引入更细粒度的分类标签（政策/技术/品牌/用户体验），提升结构化分析能力。",
            "设计热度与倾向的时间序列看板，捕捉突发事件与持续话题。",
        ]
        if sentiment.get("tendency") == "偏消极":
            actions.append("建立负向反馈的归因分析与响应SLA，优先跟进高风险议题。")
        elif sentiment.get("tendency") == "偏积极":
            actions.append("将亮点内容沉淀为传播素材，形成品牌正向循环。")
        else:
            actions.append("对中性议题进行深挖，发掘可转化的增长点。")
        return actions

    def generate_report(self, topic: str, items: List[Dict]) -> Dict:
        keywords = self._extract_keywords(items, top_k=10)
        sentiment = self._sentiment_score(items)
        summary = self._make_summary(topic, items)
        actions = self._make_actions(topic, sentiment)
        return {
            "summary": summary,
            "keywords": keywords,
            "sentiment": sentiment,
            "items": items,
            "actions": actions,
        }