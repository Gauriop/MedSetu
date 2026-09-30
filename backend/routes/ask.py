"""POST /api/ask  - text Q&A. Shares qa.answer_question with voice mode."""
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from qa import answer_question  # noqa: E402

router = APIRouter()


class AskRequest(BaseModel):
    report_text: str
    question: str
    language: str = "en"
    question_language: Optional[str] = None


@router.post("/ask")
def ask_endpoint(req: AskRequest):
    return answer_question(req.report_text, req.question, req.language, req.question_language)