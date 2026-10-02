"""
app.py
Main FastAPI app for MedSetu. Mounts all route modules and enables CORS
so the frontend (served separately as static files) can call this API.

Run locally with:
    uvicorn app:app --port 8000

Then open frontend/index.html directly, or serve it with:
    python -m http.server 5500   (from inside the frontend/ folder)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make src/ importable here (the route modules do the same for themselves).
sys.path.append(str(Path(__file__).resolve().parent / "src"))

import config  # noqa: E402,F401  (must come before transformers: sets HF env vars)

# Import heavy libraries once, on the main thread, so two requests arriving
# at the same time can't race while importing them lazily.
import torch  # noqa: E402,F401
import transformers  # noqa: E402,F401
from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoTokenizer  # noqa: E402,F401
import sentence_transformers  # noqa: E402,F401

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from routes import ingest, summarize, translate, extract, tts, ask, term, voice  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the English -> Marathi model once at startup so the first request is
    # not slow, and so translate and term-explain never load it at the same time.
    try:
        from translate_local import _load
        _load("en-indic")
        print("[startup] en-indic translation model ready.")
    except Exception as e:
        print(f"[startup] Could not preload translation model: {e}")
    yield


app = FastAPI(title="MedSetu API", lifespan=lifespan)

# Allow the frontend (running on a different port/file:// origin) to call this API.
# For a class project, allowing all origins is fine; tighten this if you ever deploy publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api")
app.include_router(summarize.router, prefix="/api")
app.include_router(translate.router, prefix="/api")
app.include_router(extract.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(term.router, prefix="/api")
app.include_router(voice.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "MedSetu API is running", "docs": "/docs"}