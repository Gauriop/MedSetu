"""Shared report-grounded Q&A, with a general-knowledge fallback.

Three answer sources, decided by the LLM itself:
  - "report":      retrieved report sections answer the question
  - "general":     question is general medical knowledge, not specific to
                    this patient's own data - answered from the model's
                    general knowledge, clearly labelled as such
  - "unavailable": question asks about this patient's specific data, but
                    it isn't in the report - never guessed

Text mode and voice mode both call answer_question(). Term explanation
(explain_term) is also used both standalone (text selection) and inline
inside a Q&A answer (clicking a term chip under the answer).
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
GENERAL_NOTE = {
    "en": "This is general medical information, not based on your specific report. Please consult your doctor for advice about your own case.",
    "mr": "ही सर्वसाधारण वैद्यकीय माहिती आहे, तुमच्या विशिष्ट अहवालावर आधारित नाही. तुमच्या स्वतःच्या स्थितीबद्दल सल्ल्यासाठी कृपया तुमच्या डॉक्टरांचा सल्ला घ्या."
}
LABELS = {
    "en": ["Answer", "What your report says", "What it means", "Important"],
    "mr": ["उत्तर", "तुमच्या अहवालात असे म्हटले आहे", "याचा अर्थ", "महत्त्वाचे"],
}
SOURCE_LABELS = {
    "en": {"report": "From your report", "general": "General information (not from your report)", "unavailable": "Not in your report"},
    "mr": {"report": "तुमच्या अहवालातून", "general": "सर्वसाधारण माहिती (तुमच्या अहवालातून नाही)", "unavailable": "तुमच्या अहवालात नाही"},
}
NONE_TEXT = {"en": "None", "mr": "काही नाही"}
UNCLEAR = {
    "en": "Sorry, I could not hear your question clearly. Please repeat it.",
    "mr": "माफ करा, तुमचा प्रश्न मला नीट ऐकू आला नाही. कृपया तो पुन्हा सांगा.",
}
KEYS = ["answer", "report_says", "means", "important"]
NONE_WORDS = {"none", "not applicable", "n/a", "nil", "-", "no limitations"}
VALID_SOURCES = {"report", "general", "unavailable"}

SYSTEM_PROMPT = """You are the MedSetu medical report assistant. You EXPLAIN; you never diagnose.

You are given retrieved sections from the patient's own uploaded report, and a question. Decide which of these three applies, and set SOURCE accordingly:

- SOURCE: report - the retrieved sections contain information that answers the question about this patient.
- SOURCE: general - the question is a general medical knowledge question (e.g. "what is hypertension", "what causes kidney stones") that does NOT require this patient's own specific data, and the retrieved sections don't already answer it. You MAY answer this from your general medical knowledge, but you must clearly mark it as general information, not something read from the report, and you must still avoid diagnosing this specific patient or implying the general information applies to their case.
- SOURCE: unavailable - the question asks about this patient's OWN specific data or findings (e.g. "what was my blood pressure", "did my report mention X"), and the retrieved sections do not contain it. Do NOT guess or invent patient data. ANSWER must be exactly: This information is not available in your uploaded report.

Rules that always apply, regardless of SOURCE:
- Preserve exactly: measurements, units, numbers, dates, body parts, left/right side, severity, medical terminology, and both positive and negative findings. Never turn "no evidence of X", "absent", "without", "negative for" into a positive finding, or the reverse.
- Do NOT diagnose, predict a disease from an isolated finding, recommend medication or treatment, or turn an uncertain finding into a definite conclusion. Do not invent medical information about this specific patient.
- Clearly separate: what the report states, what a medical term generally means, and what cannot be determined from the report.
- Explain terms in simple, patient-friendly language.

Reply in EXACTLY this plain-text format (no markdown):
SOURCE: report | general | unavailable
ANSWER: <direct answer to the question>
REPORT_SAYS: <the relevant statement from the report, wording preserved, or "Not mentioned in your report" if SOURCE is general>
MEANS: <simple patient-friendly explanation>
IMPORTANT: <uncertainty, limitation, or the general-information disclaimer if SOURCE is general, or None>
TERMS: <medical terms used in your answer, separated by semicolons, or None>"""

TERM_PROMPT = """You explain one medical term to a patient. You never diagnose.
Reply in EXACTLY this plain-text format (no markdown):
SIMPLE_MEANING: <1-2 sentence, simple, patient-friendly general meaning of the term>
CONTEXT: <what the term refers to in THIS report, using ONLY the report sections given. Do not imply a diagnosis just because the term appears. If the sections do not mention the term, write exactly: This information is not available in your uploaded report.>"""

# ---------------- parsing + safety checks (pure python) ----------------
_FIELD_RE = re.compile(
    r"^\s*\**\s*(SOURCE|ANSWER|REPORT_SAYS|MEANS|IMPORTANT|TERMS|SIMPLE_MEANING|CONTEXT)\s*\**\s*:\s*",
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


def _build(lang: str, vals: Dict[str, str], source: str, terms: List[str]) -> Dict:
    sections = [{"key": k, "label": LABELS[lang][i], "value": vals[k]} for i, k in enumerate(KEYS)]
    return {
        "sections": sections,
        "text": "\n\n".join(f"{s['label']}: {s['value']}" for s in sections),
        "source": source,
        "source_label": SOURCE_LABELS[lang].get(source, source),
        "terms": terms,
    }


def _not_available_response(lang: str) -> Dict:
    msg = NOT_AVAILABLE[lang]
    return {
        "sections": [{"key": "answer", "label": LABELS[lang][0], "value": msg}],
        "text": msg,
        "source": "unavailable",
        "source_label": SOURCE_LABELS[lang]["unavailable"],
        "terms": [],
    }


# ---------------- main pipelines ----------------
def answer_question(report_text: str, question: str, answer_lang: str = "en",
                    question_lang: Optional[str] = None) -> Dict:
    from translate_local import translate
    question_lang = question_lang or answer_lang
    q_en = question if question_lang == "en" else translate(question, question_lang, "en")

    hits = retrieve(report_text, q_en)
    base = {"status": "ok", "language": answer_lang, "question": question, "question_en": q_en,
            "sources": [h["text"] for h in hits]}

    context = "\n---\n".join(h["text"] for h in hits) if hits else "(no relevant sections found in the report)"
    raw = generate(SYSTEM_PROMPT, f"Retrieved report sections:\n{context}\n\nQuestion: {q_en}")
    f = parse_fields(raw)

    source = f.get("SOURCE", "").strip().lower()
    if source not in VALID_SOURCES:
        source = "unavailable" if _is_not_available(f.get("ANSWER", raw)) else "report"

    if source == "unavailable":
        return {**base, **_not_available_response(answer_lang)}

    vals = {
        "answer": f.get("ANSWER", ""),
        "report_says": f.get("REPORT_SAYS", "") or ("Not mentioned in your report" if source == "general" else NOT_AVAILABLE["en"]),
        "means": f.get("MEANS", "") or NOT_AVAILABLE["en"],
        "important": f.get("IMPORTANT", "") or (GENERAL_NOTE["en"] if source == "general" else NONE_TEXT["en"]),
    }
    terms = [t.strip() for t in f.get("TERMS", "").split(";")
             if t.strip() and t.strip().lower() not in NONE_WORDS]

    if answer_lang == "en":
        return {**base, **_build("en", vals, source, terms)}

    mr = {}
    for k, v in vals.items():
        if k == "important" and v.strip().lower().rstrip(".") in NONE_WORDS:
            mr[k] = NONE_TEXT["mr"]
        elif v.strip() == NOT_AVAILABLE["en"]:
            mr[k] = NOT_AVAILABLE["mr"]
        elif v.strip() == GENERAL_NOTE["en"]:
            mr[k] = GENERAL_NOTE["mr"]
        else:
            mr[k] = repair(v, translate(v, "en", "mr"))
    return {**base, **_build("mr", mr, source, terms)}


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