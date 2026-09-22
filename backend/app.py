"""
app.py
Main FastAPI app for MedSetu. Mounts all route modules and enables CORS
so the frontend (served separately as static files) can call this API.

Run locally with:
    uvicorn app:app --reload --port 8000

Then open frontend/index.html directly, or serve it with:
    python -m http.server 5500   (from inside the frontend/ folder)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import ingest, summarize, translate, extract, tts, ask

app = FastAPI(title="MedSetu API")

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


@app.get("/")
def root():
    return {"status": "MedSetu API is running", "docs": "/docs"}
