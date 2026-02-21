"""BRIET Digital Lending — Powered by Lenny.

A Free, Open Source Lending System for Libraries.
This is a self-contained demo adapted for Vercel deployment.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from lenny.routes.views import router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="BRIET Digital Lending",
    description="A demonstration lending platform — Powered by Lenny",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Serve static assets (CSS, images) from public/static
static_dir = BASE_DIR / "public" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)
