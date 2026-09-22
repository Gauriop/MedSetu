"""
tts.py
Converts Marathi text into speech (MP3) using gTTS.

Requirements:
    pip install gTTS
"""

from gtts import gTTS
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "reports" / "audio_outputs"


def text_to_speech_marathi(text: str, output_filename: str = "output.mp3") -> str:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DEFAULT_OUTPUT_DIR / output_filename

    tts = gTTS(text=text, lang="mr")
    tts.save(str(output_path))

    print(f"[tts] Saved Marathi audio to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    sample_marathi_text = (
        "रुग्णाला अपेंडिसाइटिस झाला होता. अपेंडिक्समध्ये सूज होती आणि त्याचा आकार "
        "१.२ सेंटीमीटर होता."
    )
    text_to_speech_marathi(sample_marathi_text, "test_marathi.mp3")
