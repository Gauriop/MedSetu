"""
extract_rules.py
Deterministic regex/wordlist-based extraction: measurements, laterality,
negation, severity - plus preservation comparison between two texts.
"""

import re
from dataclasses import dataclass, field

MEASUREMENT_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(cm|mm|mg|ml|kg|lb|mmHg|bpm|°F|°C|mcg|units?|cc)\b",
    re.IGNORECASE,
)

LATERALITY_TERMS = {
    "left": ["left", "lt.", "lt "],
    "right": ["right", "rt.", "rt "],
    "bilateral": ["bilateral", "both sides", "b/l"],
}

NEGATION_CUES = [
    "no evidence of", "no signs of", "denies", "denied", "without",
    "negative for", "absence of", "not present", "rule out", "ruled out",
    "no ", "free of",
]

SEVERITY_TERMS = {
    "mild": ["mild", "minimal", "slight"],
    "moderate": ["moderate"],
    "severe": ["severe", "significant", "marked", "extensive", "critical"],
}


@dataclass
class ExtractionResult:
    measurements: list = field(default_factory=list)
    laterality: list = field(default_factory=list)
    negations: list = field(default_factory=list)
    severity: list = field(default_factory=list)

    def to_dict(self):
        return {
            "measurements": self.measurements,
            "laterality": self.laterality,
            "negations": self.negations,
            "severity": self.severity,
        }


def extract_measurements(text: str) -> list:
    matches = MEASUREMENT_PATTERN.findall(text)
    return [(float(value), unit.lower()) for value, unit in matches]


def extract_laterality(text: str) -> list:
    text_lower = text.lower()
    found = []
    for side, terms in LATERALITY_TERMS.items():
        for term in terms:
            if term in text_lower:
                found.append(side)
                break
    return found


def extract_negations(text: str, context_chars: int = 40) -> list:
    text_lower = text.lower()
    found = []
    for cue in NEGATION_CUES:
        start = 0
        while True:
            idx = text_lower.find(cue, start)
            if idx == -1:
                break
            snippet_start = max(0, idx - context_chars)
            snippet_end = min(len(text), idx + len(cue) + context_chars)
            snippet = text[snippet_start:snippet_end].strip()
            found.append({"cue": cue.strip(), "context": snippet})
            start = idx + len(cue)
    return found


def extract_severity(text: str) -> list:
    text_lower = text.lower()
    found = []
    for level, terms in SEVERITY_TERMS.items():
        for term in terms:
            if term in text_lower:
                found.append(level)
                break
    return found


def extract_all(text: str) -> ExtractionResult:
    return ExtractionResult(
        measurements=extract_measurements(text),
        laterality=extract_laterality(text),
        negations=extract_negations(text),
        severity=extract_severity(text),
    )


def compare_preservation(original: str, generated: str) -> dict:
    orig = extract_all(original)
    gen = extract_all(generated)

    orig_measurements = set(orig.measurements)
    gen_measurements = set(gen.measurements)
    lost_measurements = orig_measurements - gen_measurements

    orig_laterality = set(orig.laterality)
    gen_laterality = set(gen.laterality)
    lost_laterality = orig_laterality - gen_laterality

    orig_severity = set(orig.severity)
    gen_severity = set(gen.severity)
    lost_severity = orig_severity - gen_severity

    orig_negation_count = len(orig.negations)
    gen_negation_count = len(gen.negations)

    return {
        "lost_measurements": list(lost_measurements),
        "lost_laterality": list(lost_laterality),
        "lost_severity": list(lost_severity),
        "negation_count_original": orig_negation_count,
        "negation_count_generated": gen_negation_count,
        "negation_count_mismatch": orig_negation_count != gen_negation_count,
        "measurement_preservation_rate": (
            len(gen_measurements & orig_measurements) / len(orig_measurements)
            if orig_measurements else None
        ),
        "laterality_preservation_rate": (
            len(gen_laterality & orig_laterality) / len(orig_laterality)
            if orig_laterality else None
        ),
    }


if __name__ == "__main__":
    sample = """
    PREOPERATIVE DIAGNOSIS: Acute appendicitis.
    The patient presented with right lower quadrant pain. CT scan showed
    an inflamed appendix measuring 1.2 cm in diameter. No evidence of
    perforation. Mild tenderness on palpation. Left kidney appeared normal.
    """
    result = extract_all(sample)
    print("Extraction result:")
    print(result.to_dict())

    fake_summary = "The patient had appendix inflammation. No perforation seen."
    print("\nPreservation comparison:")
    print(compare_preservation(sample, fake_summary))
