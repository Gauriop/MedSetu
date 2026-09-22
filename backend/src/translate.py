"""
translate.py
Translates English text into Marathi using AI4Bharat's IndicTrans2
(distilled 200M variant - runs on CPU, slow but workable).

Requirements:
    pip install torch transformers sentencepiece
    (IndicTrans2 model download happens automatically on first call)

Fallback (if IndicTrans2 setup gives trouble):
    pip install deep-translator
"""

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"

_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is None:
        print("[translate] Loading IndicTrans2 model (first call only)...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, trust_remote_code=True)
        _model.eval()
    return _model, _tokenizer


def translate_to_marathi(text: str) -> str:
    model, tokenizer = _load_model()
    input_text = f"eng_Latn mar_Deva {text}"
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        output_ids = model.generate(**inputs, max_length=512, num_beams=5)
    return tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()


def translate_to_marathi_fallback(text: str) -> str:
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="en", target="mr").translate(text)


if __name__ == "__main__":
    sample_summary = (
        "The patient had appendicitis. The appendix was inflamed and measured "
        "1.2 cm. No signs of perforation were found."
    )
    try:
        result = translate_to_marathi(sample_summary)
        print("--- IndicTrans2 Translation ---\n")
        print(result)
    except Exception as e:
        print(f"IndicTrans2 failed ({e}), trying fallback...")
        result = translate_to_marathi_fallback(sample_summary)
        print("--- Fallback Translation ---\n")
        print(result)
