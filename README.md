# 微舆 POC 项目

一个极简的舆情分析 POC，用于演示“多智能体（轻量）+ 报告生成”的基本流程：
- QueryAgent：根据主题生成示例素材（默认使用模拟数据，避免不合规抓取）。
- ReportAgent：对素材进行关键词提取、简单情感/倾向打分与摘要，生成报告。
- Orchestrator：编排上述两个 Agent 并输出到网页模板。
- FastAPI + Jinja2 提供一个简单的 Web 界面。

## 快速开始

1) 安装依赖

```bash
pip3 install -r requirements.txt
```

2) 启动服务

```bash
uvicorn app.main:app --reload
```

3) 打开浏览器访问

```
http://127.0.0.1:8000/
```

## 目录结构

- app/
  - main.py（FastAPI 入口）
  - orchestrator.py（编排）
  - agents/
    - query_agent.py
    - report_agent.py
  - schemas.py（数据结构）
- templates/
  - index.html
  - report.html
- static/
  - style.css
- requirements.txt
- README.md

## 说明
- 目前仅为 POC，未集成真实平台抓取与 LLM。后续可按需引入：
  - 数据源：新闻 RSS、合规 API、企业内部数据。
  - LLM：用于更高质量的摘要/分类/多轮协作（需配置 API Key）。
  - 多模态：图片 OCR/视频 ASR 等。
- 请注意数据合规与隐私保护，避免抓取与存储敏感信息。