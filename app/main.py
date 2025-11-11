from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import jinja2

from .orchestrator import Orchestrator


app = FastAPI(title="微舆 POC")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, topic: str = Form(...), source: str = Form("baidu"), fast: str = Form("off")):
    orchestrator = Orchestrator()
    fast_flag = fast.lower() in ("on", "true", "1", "yes")
    report = orchestrator.analyze(topic=topic, use_mock=False, source=source, fast=fast_flag)
    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "topic": topic,
            "report": report,
            "source": source,
            "fast": fast_flag,
        },
    )


@app.post("/export")
async def export_report(
    request: Request,
    topic: str = Form(...),
    source: str = Form("baidu"),
    fast: str = Form("off"),
    format: str = Form("html"),
):
    orchestrator = Orchestrator()
    fast_flag = fast.lower() in ("on", "true", "1", "yes")
    report = orchestrator.analyze(topic=topic, use_mock=False, source=source, fast=fast_flag)

    # 文件名安全化
    safe_topic = "".join(c for c in topic if c.isalnum() or c in ("_", "-")) or "report"

    if format.lower() == "md":
        # 生成 Markdown 文本
        lines = []
        lines.append(f"# 舆情报告 - {topic}")
        lines.append("")
        lines.append(f"生成时间：{report['generated_at']}")
        lines.append(f"素材条数：{report['stats']['item_count']} | 来源域名数：{report['stats']['domain_count']}")
        lines.append("")
        lines.append("## 关键指标")
        lines.append(f"- 维基浏览量（中文）：{report['metrics'].get('wiki_pageviews_zh', 'N/A')}")
        lines.append(f"- 维基浏览量（英文）：{report['metrics'].get('wiki_pageviews_en', 'N/A')}")
        lines.append(f"- RSS 命中条数：{report['metrics'].get('rss_mentions_count', 0)}")
        if report['metrics'].get('platform_whitelist'):
            plats = ", ".join(report['metrics']['platform_whitelist'])
            lines.append(f"- 平台白名单：{plats}")
        lines.append("")
        lines.append("## 热点关键词（Top10）")
        for kw in report.get('keywords', []):
            lines.append(f"- {kw['word']} x{kw['count']}")
        lines.append("")
        lines.append("## 情感/倾向")
        s = report.get('sentiment', {})
        lines.append(f"- 积极：{s.get('positive', 0)}；消极：{s.get('negative', 0)}；分值：{s.get('score', 0)}；倾向：{s.get('tendency', 'N/A')}")
        lines.append("")
        lines.append("## 平台热榜匹配")
        ta = report['metrics'].get('trending_agg', {})
        for key, label in [
            ('weibo_items', '微博'), ('zhihu_items', '知乎'), ('bilibili_items', '哔哩哔哩'),
            ('sina_items', '新浪'), ('toutiao_items', '今日头条'), ('douyin_items', '抖音'), ('xiaohongshu_items', '小红书')
        ]:
            items = ta.get(key) or []
            if items:
                lines.append(f"- {label}热榜匹配：")
                for it in items:
                    title = it.get('title', '')
                    link = it.get('link', '')
                    lines.append(f"  - [{title}]({link})")
        lines.append("")
        lines.append("## 总体摘要")
        lines.append(report.get('summary', ''))
        lines.append("")
        lines.append("## 后续行动建议")
        for a in report.get('actions', []):
            lines.append(f"- {a}")
        md_text = "\n".join(lines)
        headers = {"Content-Disposition": f"attachment; filename=report_{safe_topic}.md"}
        return Response(content=md_text, media_type="text/markdown; charset=utf-8", headers=headers)

    # 默认导出为自包含的静态 HTML：将 CSS 内联
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"), autoescape=True)
    template = env.get_template("report.html")
    html = template.render({
        "request": request,
        "topic": topic,
        "report": report,
        "source": source,
        "fast": fast_flag,
    })
    css_path = Path("static/style.css")
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    html_export = html.replace('<link rel="stylesheet" href="/static/style.css" />', f"<style>\n{css}\n</style>")
    headers = {"Content-Disposition": f"attachment; filename=report_{safe_topic}.html"}
    return Response(content=html_export, media_type="text/html; charset=utf-8", headers=headers)