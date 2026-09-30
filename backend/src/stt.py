"""Local speech-to-text with faster-whisper. Rejects unclear audio instead of guessing."""
import os
import tempfile
import threading
from statistics import mean

import config

_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel
            try:
                if config.get_device() == "cuda":
                    _model = WhisperModel(config.WHISPER_MODEL, device="cuda", compute_type="float16")
                else:
                    raise RuntimeError("cpu")
            except Exception:
                _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes, language: str = "en", suffix: str = ".webm") -> dict:
    """Returns {"text": str, "clear": bool}. clear=False -> ask the user to repeat."""
    model = _load()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        segments, _info = model.transcribe(
            path,
            language=language if language in ("en", "mr", "hi") else None,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        segments = list(segments)
    finally:
        os.unlink(path)

    text = " ".join(s.text.strip() for s in segments).strip()
    if not segments or len(text) < 3:
        return {"text": "", "clear": False}
    clear = (
        mean(s.avg_logprob for s in segments) > config.STT_MIN_LOGPROB
        and mean(s.no_speech_prob for s in segments) < config.STT_MAX_NO_SPEECH
    )
    return {"text": text, "clear": clear}