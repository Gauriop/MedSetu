"""
POST /api/translate
Translates English text into Marathi.
"""

import sys
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from translate import translate_to_marathi, translate_to_marathi_fallback  # noqa: E402

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str


@router.post("/translate")
def translate_endpoint(req: TranslateRequest):
    try:
        translation = translate_to_marathi(req.text)
        method = "indictrans2"
    except Exception:
        translation = translate_to_marathi_fallback(req.text)
        method = "fallback"

    return {"translation": translation, "method": method}
