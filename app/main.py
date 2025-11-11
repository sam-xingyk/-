from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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