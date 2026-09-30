"""POST /api/tts - local text-to-speech (MMS-TTS Marathi/English, gTTS fallback)."""
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from tts_local import synthesize  # noqa: E402

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    language: str = "mr"


@router.post("/tts")
def tts_endpoint(req: TTSRequest):
    audio, mime = synthesize(req.text, req.language)
    return Response(content=audio, media_type=mime)