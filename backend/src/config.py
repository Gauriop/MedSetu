"""Central config.

Import this FIRST in any module that loads models,
so Hugging Face settings are configured before
transformers / sentence-transformers are imported.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BACKEND_DIR / ".env")

MODELS_DIR = BACKEND_DIR / "models"


# Store Hugging Face model files inside the project.
# Do NOT change HF_HOME because the Hugging Face
# authentication token is stored in the user's
# normal Hugging Face directory.
os.environ.setdefault(
    "HF_HUB_CACHE",
    str(MODELS_DIR / "hf" / "hub")
)

# Windows may not allow creation of symbolic links.
# This prevents the symlink-related Windows error.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")


# --------------------------------------------------
# Offline mode
# --------------------------------------------------

if os.getenv("LOCAL_ONLY", "0") == "1":
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


# --------------------------------------------------
# Models
# --------------------------------------------------

EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "intfloat/multilingual-e5-small"
)

WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "small"
)

TRANSLATE_EN_INDIC = (
    "ai4bharat/indictrans2-en-indic-dist-200M"
)

TRANSLATE_INDIC_EN = (
    "ai4bharat/indictrans2-indic-en-dist-200M"
)

TTS_MODELS = {
    "mr": "facebook/mms-tts-mar",
    "en": "facebook/mms-tts-eng",
}


# --------------------------------------------------
# QA / STT settings
# --------------------------------------------------

TOP_K = int(os.getenv("TOP_K", "5"))

STT_MIN_LOGPROB = float(
    os.getenv("STT_MIN_LOGPROB", "-1.2")
)

STT_MAX_NO_SPEECH = float(
    os.getenv("STT_MAX_NO_SPEECH", "0.6")
)


# --------------------------------------------------
# Device
# --------------------------------------------------

def get_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"