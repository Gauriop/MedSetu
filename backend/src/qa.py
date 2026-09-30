"""Shared report-grounded Q&A. Text mode and voice mode both call answer_question().

Pipeline: question -> (IndicTrans2 to English if needed) -> RAG retrieval (FAISS)
-> LLM (English, grounded) -> (IndicTrans2 to Marathi if needed) -> structured answer.
"""
import re
from typing import Dict, List, Optional

import config
from llm import generate
from rag import retrieve

NOT_AVAILABLE = {
    "en": "This information is not available in your uploaded report.",
    "mr": "ही माहिती तुमच्या अपलोड केलेल्या अहवालात उपलब्ध नाही.",
}
LABELS = {
    "en": ["Answer", "What your report says", "What it means", "Important"],
    "mr": ["उत्तर", "तुमच्या अहवालात असे म्हटले आहे", "याचा अर्थ", "महत्त्वाचे"],
}
NONE_TEXT = {"en": "None", "mr": "काही नाही"}
UNCLEAR = {
    "en": "Sorry, I could not hear your question clearly. Please repeat it.",
    "mr": "माफ करा, तुमचा प्रश्न मला नीट ऐकू आला नाही. कृपया तो पुन्हा सांगा.",
}
KEYS = ["answer", "report_says", "means", "important"]
NONE_WORDS = {"none", "not applicable", "n/a", "nil", "-", "no limitations"}

SYSTEM_PROMPT = """You are the MedSetu medical report assistant. You EXPLAIN a patient's report; you never diagnose.

Answer ONLY from the retrieved report sections given by the user. Never answer a question about the report from general knowledge.

Rules:
- If the sections do not contain or support the answer, the ANSWER must be exactly: This information is not available in your uploaded report.
- Preserve exactly: measurements, units, numbers, dates, body parts, left/right side, severity, medical terminology, and both positive and negative findings. Never turn "no evidence of X", "absent", "without", "negative for" into a positive finding, or the reverse.
- Do NOT diagnose, predict a disease from an isolated finding, recommend medication or treatment, or turn an uncertain finding into a definite conclusion. Do not invent medical information.
- Clearly separate: what the report states, what a medical term generally means, and what cannot be determined from the report.
- Explain terms in the context where they appear in the report, in simple patient-friendly English.

Reply in EXACTLY this plain-text format (no markdown):
ANSWER: <direct answer to the question>
REPORT_SAYS: <the relevant statement from the report, wording preserved>
MEANS: <simple patient-friendly explanation>
IMPORTANT: <uncertainty or limitation, or None>
TERMS: <medical terms used in your answer, exactly as written in the report, separated by semicolons, or None>"""

TERM_PROMPT = """You explain one medical term to a patient. You never diagnose.
Reply in EXACTLY this plain-text format (no markdown):
SIMPLE_MEANING: <1-2 sentence, simple, patient-friendly general meaning of the term>
CONTEXT: <what the term refers to in THIS report, using ONLY the report sections given. Do not imply a diagnosis just because the term appears. If the sections do not mention the term, write exactly: This information is not available in your uploaded report.>"""

# ---------------- parsing + safety checks (pure python) ----------------
_FIELD_RE = re.compile(
    r"^\s*\**\s*(ANSWER|REPORT_SAYS|MEANS|IMPORTANT|TERMS|SIMPLE_MEANING|CONTEXT)\s*\**\s*:\s*",
    re.M,
)


def parse_fields(raw: str) -> Dict[str, str]:
    matches = list(_FIELD_RE.finditer(raw))
    if not matches:
        return {"ANSWER": raw.strip()}
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        # .lstrip("*") strips a leftover "**" when the model bolds the whole
        # "**LABEL:**" including the colon, e.g. "**ANSWER:** text"
        out[m.group(1)] = raw[m.end():end].strip().lstrip("*").strip()
    return out


_DEV = str.maketrans("०१२३४५६७८९", "0123456789")
_NEG_EN = re.compile(r"\b(no|not|without|absent|negative|denies|free of)\b", re.I)
_NEG_MR = ("नाही", "नाहीत", "नसून", "नसल", "नसते", "नसतात", "नकारात्मक", "अनुपस्थित",
           "शिवाय", "न आढळ", "नसेल", "नव्हत", "नसणे")


def _numbers(s: str) -> List[str]:
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s.translate(_DEV))
    return re.findall(r"\d+(?:\.\d+)?", s)


def repair(en: str, mr: str) -> str:
    """Safety net for machine translation: if numbers, negation or left/right
    look lost, keep the original English next to the Marathi instead of trusting it."""
    problems = []
    mr_nums = _numbers(mr)
    if any(n not in mr_nums for n in _numbers(en)):
        problems.append("numbers")
    if _NEG_EN.search(en) and not any(w in mr for w in _NEG_MR):
        problems.append("negation")
    low = en.lower()
    if (re.search(r"\bleft\b", low) and "डाव" not in mr) or (re.search(r"\bright\b", low) and "उजव" not in mr):
        problems.append("side")
    return f"{mr} (मूळ इंग्रजी / original: {en})" if problems else mr


def _is_not_available(text: str) -> bool:
    return NOT_AVAILABLE["en"].lower().rstrip(".") in text.lower()


def _build(lang: str, vals: Dict[str, str]) -> Dict:
    sections = [{"key": k, "label": LABELS[lang][i], "value": vals[k]} for i, k in enumerate(KEYS)]
    return {"sections": sections, "text": "\n\n".join(f"{s['label']}: {s['value']}" for s in sections)}


def _not_available_response(lang: str) -> Dict:
    msg = NOT_AVAILABLE[lang]
    return {"sections": [{"key": "answer", "label": LABELS[lang][0], "value": msg}], "text": msg}


def answer_question(report_text: str, question: str, answer_lang: str = "en",
                    question_lang: Optional[str] = None) -> Dict:
    from translate_local import translate
    question_lang = question_lang or answer_lang
    q_en = question if question_lang == "en" else translate(question, question_lang, "en")

    hits = retrieve(report_text, q_en)
    base = {"status": "ok", "language": answer_lang, "question": question, "question_en": q_en,
            "sources": [h["text"] for h in hits]}
    if not hits:
        return {**base, **_not_available_response(answer_lang)}

    context = "\n---\n".join(h["text"] for h in hits)
    raw = generate(SYSTEM_PROMPT, f"Retrieved report sections:\n{context}\n\nQuestion: {q_en}")
    f = parse_fields(raw)
    if _is_not_available(f.get("ANSWER", raw)) and len(f.get("ANSWER", raw)) < 90:
        return {**base, **_not_available_response(answer_lang)}

    vals = {
        "answer": f.get("ANSWER", ""),
        "report_says": f.get("REPORT_SAYS", "") or NOT_AVAILABLE["en"],
        "means": f.get("MEANS", "") or NOT_AVAILABLE["en"],
        "important": f.get("IMPORTANT", "") or NONE_TEXT["en"],
    }
    terms = [t.strip() for t in f.get("TERMS", "").split(";")
             if t.strip() and t.strip().lower() not in NONE_WORDS]

    if answer_lang == "en":
        return {**base, **_build("en", vals)}

    mr = {}
    for k, v in vals.items():
        if k == "important" and v.strip().lower().rstrip(".") in NONE_WORDS:
            mr[k] = NONE_TEXT["mr"]
        elif v.strip() == NOT_AVAILABLE["en"]:
            mr[k] = NOT_AVAILABLE["mr"]
        else:
            mr[k] = repair(v, translate(v, "en", "mr"))
    if terms:
        mr["means"] += f" (वैद्यकीय संज्ञा / Medical terms: {'; '.join(terms)})"
    return {**base, **_build("mr", mr)}


def explain_term(report_text: str, term: str, lang: str = "en") -> Dict:
    from translate_local import translate
    hits = retrieve(report_text, term, k=3)
    in_report = term.lower() in report_text.lower()
    context = "\n---\n".join(h["text"] for h in hits) if in_report else "(term not found in report)"
    f = parse_fields(generate(TERM_PROMPT, f"Term: {term}\n\nReport sections:\n{context}"))
    simple_en = f.get("SIMPLE_MEANING", "")
    ctx_en = f.get("CONTEXT", "") if in_report else NOT_AVAILABLE["en"]

    if lang == "en":
        sections = [
            {"key": "term", "label": "Term", "value": term},
            {"key": "simple_english", "label": "Simple English meaning", "value": simple_en},
            {"key": "context", "label": "Context in your report", "value": ctx_en},
        ]
    else:
        marathi = f"{repair(simple_en, translate(simple_en, 'en', 'mr'))} ({term})"
        ctx_mr = NOT_AVAILABLE["mr"] if ctx_en == NOT_AVAILABLE["en"] else repair(ctx_en, translate(ctx_en, "en", "mr"))
        sections = [
            {"key": "term", "label": "संज्ञा (Term)", "value": term},
            {"key": "simple_english", "label": "सोपा इंग्रजी अर्थ (Simple English meaning)", "value": simple_en},
            {"key": "marathi_meaning", "label": "मराठी अर्थ", "value": marathi},
            {"key": "context", "label": "तुमच्या अहवालातील संदर्भ", "value": ctx_mr},
        ]
    return {"term": term, "language": lang, "sections": sections,
            "text": "\n\n".join(f"{s['label']}: {s['value']}" for s in sections)}