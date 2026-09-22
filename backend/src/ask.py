"""
POST /api/ask
Report-grounded question answering (RAG-lite): stuffs the original report
text into the prompt alongside the user's question, since a single report
easily fits in context - no chunking/embedding pipeline needed at this scale.
"""

import sys
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from summarize import get_client  # reuse the same Groq client setup  # noqa: E402

router = APIRouter()

SYSTEM_PROMPT = (
    "You are a medical assistant. Answer the user's question using ONLY "
    "information present in the report text provided. If the report does "
    "not contain the answer, say so clearly. Do not add any diagnosis or "
    "medical advice beyond what is stated in the report."
)


class AskRequest(BaseModel):
    report_text: str
    question: str


@router.post("/ask")
def ask_endpoint(req: AskRequest):
    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Report:\n{req.report_text}\n\nQuestion: {req.question}"},
        ],
        temperature=0.2,
    )
    return {"answer": response.choices[0].message.content.strip()}
