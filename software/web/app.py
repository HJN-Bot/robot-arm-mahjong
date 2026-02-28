from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from software.services.api import app as api_app

root = Path(__file__).resolve().parent

app = FastAPI(title="robot-arm-mahjong web")

# index page — must be registered before the catch-all sub-app mount
@app.get("/", response_class=HTMLResponse)
def index():
    return (root / "templates" / "index.html").read_text(encoding="utf-8")

# serve static files
app.mount("/static", StaticFiles(directory=str(root / "static")), name="static")

# mount API sub-app last — catch-all prefix "" would shadow routes above it
app.mount("", api_app)
