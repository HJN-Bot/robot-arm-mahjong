from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from software.services.api import app as api_app

root = Path(__file__).resolve().parent

app = FastAPI(title="robot-arm-mahjong web")

# mount API at /
app.mount("", api_app)

# serve static
app.mount("/static", StaticFiles(directory=str(root / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    return (root / "templates" / "index.html").read_text(encoding="utf-8")
