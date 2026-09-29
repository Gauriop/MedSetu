"""
POST /api/term-explain
Given a medical term/phrase the user selected, plus the surrounding report
context, returns a simple English meaning, a Marathi meaning, a simple
Marathi explanation, and a note on report-specific context.

This is an accessibility/explanation feature, not a diagnostic one: the
prompt explicitly forbids inferring a disease or suggesting treatment.
"""

import json
import re
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from summarize import get_client  # reuse the same Groq client setup  # noqa: E402

router = APIRouter()

SYSTEM_PROMPT = """You are a medical-language accessibility assistant. A patient has highlighted a medical term or phrase from their own report. Explain it so they can understand what it means - you do not diagnose, and you do not recommend or suggest treatment.

Rules:
- Base your explanation only on the term itself and the surrounding report context given to you. Do not add findings, causes, or implications that are not supported by that text.
- If the report context gives the term a specific meaning (e.g. it is on a specific side, has a specific measurement, has a specific severity, or is negated - "no evidence of X"), reflect that in the context_note field. If the context does not add anything beyond the general meaning, leave context_note as an empty string.
- Marathi text must be natural, everyday, patient-friendly Marathi. Prefer common spoken words over heavily Sanskritized formal medical Marathi, as long as the meaning stays accurate.
- Never suggest a diagnosis, a disease name the patient hasn't been told, a treatment, or medical advice, even if the term strongly implies one.
- Keep every field to one or two short sentences.

Respond with ONLY a JSON object, no other text, no markdown fences, in exactly this shape:
{
  "term": "...",
  "simple_english": "...",
  "marathi_meaning": "...",
  "simple_marathi_explanation": "...",
  "context_note": "..."
}"""


class TermRequest(BaseModel):
    term: str
    context: str = ""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return json.loads(raw)


@router.post("/term-explain")
def term_explain_endpoint(req: TermRequest):
    term = req.term.strip()
    if not term:
        raise HTTPException(status_code=400, detail="No term provided.")

    client = get_client()
    user_content = f'Term: "{term}"'
    if req.context.strip():
        user_content += f"\n\nSurrounding report context:\n{req.context.strip()}"

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    try:
        result = _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=502, detail=f"Could not parse model response: {raw[:300]}")

    for key in ["term", "simple_english", "marathi_meaning", "simple_marathi_explanation", "context_note"]:
        result.setdefault(key, "")

    return result