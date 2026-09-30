"""Local text-to-speech: Meta MMS-TTS (Marathi + English). gTTS is only a fallback."""
import io
import re
import threading

import config

_models = {}
_lock = threading.Lock()


def _load(lang: str):
    with _lock:
        if lang not in _models:
            from transformers import AutoTokenizer, VitsModel
            name = config.TTS_MODELS[lang]
            _models[lang] = (AutoTokenizer.from_pretrained(name), VitsModel.from_pretrained(name).eval())
    return _models[lang]


def _mms(text: str, lang: str) -> bytes:
    import numpy as np
    import torch
    from scipy.io import wavfile
    tok, model = _load(lang)
    sr = model.config.sampling_rate
    pieces = []
    for sent in re.split(r"(?<=[.!?\u0964])\s+|\n+", text):
        sent = sent.strip()
        if not sent:
            continue
        inputs = tok(sent, return_tensors="pt")
        if inputs["input_ids"].shape[1] == 0:
            continue
        with torch.no_grad():
            pieces.append(model(**inputs).waveform[0].cpu().numpy())
        pieces.append(np.zeros(int(sr * 0.25), dtype="float32"))
    if not pieces:
        raise ValueError("nothing speakable")
    wav = np.concatenate(pieces)
    buf = io.BytesIO()
    wavfile.write(buf, sr, (np.clip(wav, -1, 1) * 32767).astype("int16"))
    return buf.getvalue()


def _gtts(text: str, lang: str) -> bytes:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(buf)
    return buf.getvalue()


def synthesize(text: str, lang: str = "mr"):
    """Returns (audio_bytes, mime_type)."""
    lang = lang if lang in config.TTS_MODELS else "en"
    text = re.sub(r"[*_#`]", "", text)
    try:
        return _mms(text, lang), "audio/wav"
    except Exception:
        return _gtts(text, lang), "audio/mpeg"