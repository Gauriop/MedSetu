"""Local IndicTrans2 translation (English <-> Marathi/Hindi). Models load lazily.
No IndicTransToolkit needed: for Devanagari languages its job is only the
'<src> <tgt> text' prefix and output spacing cleanup, done here in pure Python.
Note: preprocess_batch avoids backslashes inside f-string expressions, which
is a SyntaxError on Python < 3.12."""
import re
import threading
from typing import Dict, List

import config

LANG_CODE = {"en": "eng_Latn", "mr": "mar_Deva", "hi": "hin_Deva"}
BATCH = 8
_models: Dict[str, tuple] = {}
_lock = threading.Lock()

try:
    from sacremoses import MosesDetokenizer
    _md_en = MosesDetokenizer(lang="en")
except Exception:  # pragma: no cover
    _md_en = None


class SimpleIndicProcessor:
    """Minimal replacement for IndicTransToolkit.IndicProcessor (Devanagari only)."""

    def preprocess_batch(self, sents: List[str], src_lang: str, tgt_lang: str) -> List[str]:
        clean = [re.sub(r"\s+", " ", s).strip() for s in sents]
        return [f"{src_lang} {tgt_lang} {s}" for s in clean]

    def postprocess_batch(self, sents: List[str], lang: str) -> List[str]:
        out = []
        for s in sents:
            s = s.strip()
            if lang == "eng_Latn":
                s = _md_en.detokenize(s.split()) if _md_en else s
            else:
                s = re.sub(r"\s+([.,;:!?\u0964])", r"\1", s)
            out.append(s)
        return out


def _load(kind: str):
    with _lock:
        if kind not in _models:
            import torch  # noqa: F401
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            name = config.TRANSLATE_EN_INDIC if kind == "en-indic" else config.TRANSLATE_INDIC_EN
            print(f"[translate] Loading IndicTrans2 {kind} model (first call only)...")
            tok = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(name, trust_remote_code=True)
            model.to(config.get_device()).eval()
            _models[kind] = (tok, model, SimpleIndicProcessor())
        return _models[kind]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?\u0964])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _translate_batch(sents: List[str], src: str, tgt: str) -> List[str]:
    import torch
    tok, model, ip = _load("en-indic" if src == "en" else "indic-en")
    s_code, t_code = LANG_CODE[src], LANG_CODE[tgt]
    device = config.get_device()
    out: List[str] = []
    for i in range(0, len(sents), BATCH):
        batch = ip.preprocess_batch(sents[i:i + BATCH], src_lang=s_code, tgt_lang=t_code)
        enc = tok(batch, truncation=True, padding="longest", max_length=256,
                  return_tensors="pt", return_attention_mask=True).to(device)
        kwargs = dict(min_length=0, max_length=256, num_beams=4, num_return_sequences=1)
        with torch.no_grad():
            try:
                gen = model.generate(**enc, use_cache=True, **kwargs)
            except Exception:
                gen = model.generate(**enc, use_cache=False, **kwargs)
        dec = tok.batch_decode(gen, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        out.extend(ip.postprocess_batch(dec, lang=t_code))
    return out


def translate(text: str, src: str, tgt: str) -> str:
    if not text.strip() or src == tgt:
        return text
    if src != "en" and tgt != "en":
        text, src = translate(text, src, "en"), "en"
    sents = split_sentences(text)
    return " ".join(_translate_batch(sents, src, tgt))