"""POST /api/term-explain - keeps the original request/response shape used by term_feature.js."""
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from qa import NOT_AVAILABLE, explain_term  # noqa: E402

router = APIRouter()


class TermRequest(BaseModel):
    term: str
    context: str = ""                  # sentence around the selected term
    report_text: Optional[str] = None  # full report (sent by term_feature.js)
    language: str = "mr"


@router.post("/term-explain")
def term_endpoint(req: TermRequest):
    source = req.report_text or req.context or req.term
    r = explain_term(source, req.term.strip(), "mr")
    by = {s["key"]: s["value"] for s in r["sections"]}
    ctx = by.get("context", "")
    return {
        **r,
        "simple_english": by.get("simple_english", ""),
        "marathi_meaning": by.get("marathi_meaning", ""),
        "context_note": "" if ctx == NOT_AVAILABLE["mr"] else ctx,
    }