"""
POST /api/tts
Converts Marathi text to speech, returns the audio file.
"""

import sys
from pathlib import Path
import uuid
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from tts import text_to_speech_marathi  # noqa: E402

router = APIRouter()


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
def tts_endpoint(req: TTSRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = text_to_speech_marathi(req.text, filename)
    return FileResponse(output_path, media_type="audio/mpeg", filename=filename)
