"""POST /api/voice-ask - voice Q&A: audio -> STT -> same pipeline as text -> text answer."""
import sys
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from qa import UNCLEAR, answer_question  # noqa: E402
from stt import transcribe  # noqa: E402

router = APIRouter()


@router.post("/voice-ask")
def voice_ask(
    audio: UploadFile = File(...),
    report_text: str = Form(...),
    language: str = Form("en"),
    speech_language: str = Form(""),
):
    speech_language = speech_language or language
    suffix = Path(audio.filename or "q.webm").suffix or ".webm"
    stt = transcribe(audio.file.read(), speech_language, suffix)
    if not stt["clear"]:
        msg = UNCLEAR.get(language, UNCLEAR["en"])
        return {"status": "unclear", "language": language, "transcript": stt["text"],
                "message": msg, "text": msg, "sections": []}
    result = answer_question(report_text, stt["text"], language, speech_language)
    return {**result, "transcript": stt["text"]}