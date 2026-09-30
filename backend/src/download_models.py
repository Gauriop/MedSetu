"""One-time download of every local model.

Run:
    python src/download_models.py

Then set LOCAL_ONLY=1 in .env to run offline.
"""

import config
from huggingface_hub import snapshot_download


REPOS = [
    config.EMBED_MODEL,
    config.TRANSLATE_EN_INDIC,
    config.TRANSLATE_INDIC_EN,
    *config.TTS_MODELS.values(),
]


if __name__ == "__main__":

    # --------------------------------------------------
    # Hugging Face models
    # --------------------------------------------------

    for repo in REPOS:
        print(f"Downloading {repo} ...")

        snapshot_download(
            repo,
            cache_dir=str(config.MODELS_DIR / "hf" / "hub"),
        )

    # --------------------------------------------------
    # Faster-Whisper
    # --------------------------------------------------

    print(
        f"Downloading faster-whisper "
        f"'{config.WHISPER_MODEL}' ..."
    )

    from faster_whisper import WhisperModel

    whisper_dir = config.MODELS_DIR / "whisper"
    whisper_dir.mkdir(parents=True, exist_ok=True)

    WhisperModel(
        config.WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
        download_root=str(whisper_dir),
    )

    print()
    print("All models downloaded successfully!")
    print("Models are stored under:", config.MODELS_DIR)