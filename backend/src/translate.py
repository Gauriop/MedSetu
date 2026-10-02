"""Thin wrapper: all translation (and the single model cache) lives in translate_local.py,
so /api/translate and the Q&A / term-explain features share one loaded model."""
from translate_local import translate


def translate_to_marathi(text: str) -> str:
    return translate(text, "en", "mr")


def translate_to_marathi_fallback(text: str) -> str:
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="en", target="mr").translate(text)