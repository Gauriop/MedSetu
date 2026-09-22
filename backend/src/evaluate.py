"""
evaluate.py
Evaluation metrics: ROUGE, BERTScore, chrF++, and preservation metrics.

Requirements:
    pip install rouge-score bert-score sacrebleu
"""

from rouge_score import rouge_scorer
from bert_score import score as bert_score
import sacrebleu

from extract_rules import compare_preservation


def compute_rouge(reference: str, generated: str) -> dict:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(reference, generated)
    return {k: round(v.fmeasure, 4) for k, v in scores.items()}


def compute_bertscore(references: list, generated: list, lang: str = "en") -> dict:
    P, R, F1 = bert_score(generated, references, lang=lang, verbose=False)
    return {
        "precision": round(P.mean().item(), 4),
        "recall": round(R.mean().item(), 4),
        "f1": round(F1.mean().item(), 4),
    }


def compute_chrf(reference: str, generated: str) -> float:
    result = sacrebleu.sentence_chrf(generated, [reference])
    return round(result.score, 2)


def full_evaluation(original_report, reference_summary, generated_summary,
                     marathi_reference=None, marathi_translation=None) -> dict:
    results = {
        "rouge": compute_rouge(reference_summary, generated_summary),
        "preservation_summary_vs_original": compare_preservation(original_report, generated_summary),
    }
    if marathi_reference and marathi_translation:
        results["chrf"] = compute_chrf(marathi_reference, marathi_translation)
        results["preservation_translation_vs_summary"] = compare_preservation(
            generated_summary, marathi_translation
        )
    return results


if __name__ == "__main__":
    original = """
    The patient presented with right lower quadrant pain. CT scan showed
    an inflamed appendix measuring 1.2 cm. No signs of perforation were found.
    """
    reference_summary = "Patient had appendicitis with a 1.2 cm inflamed appendix, no perforation."
    generated_summary = "The patient's appendix was inflamed and measured 1.2 cm. No perforation was seen."

    results = full_evaluation(original, reference_summary, generated_summary)
    print("--- Evaluation Results ---")
    for k, v in results.items():
        print(f"{k}: {v}")
