"""
summarize.py
Zero-shot summarization via Groq-hosted Llama (no local GPU needed).

Requirements:
    pip install groq python-dotenv
Set your API key by creating a file at backend/.env (same folder as app.py)
containing exactly one line:
    GROQ_API_KEY=your-actual-key-here
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq, APIStatusError

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SYSTEM_PROMPT = """You are a medical assistant who explains a patient's own report to them in plain, everyday language - the way you'd explain it to a worried family member with no medical background.

This is NOT a rewording task. Do not keep every number, date, and lab value from the original - that defeats the purpose. Your job is to decide what actually matters to the patient and explain it simply, leaving out details that don't change the picture.

How to summarize:
- Start with one plain sentence describing the overall situation.
- Only mention specific numbers/values if they are abnormal, flagged (e.g. marked "H" or "L", or outside the stated reference range), or clearly important to the story. For values that are normal, you can simply say "normal" or omit them - do not list every value individually.
- When you do mention an abnormal value, briefly say what it means and why it matters, not just the number (e.g. "your blood isn't clotting as fast as it should" rather than "PT 44.9, INR 5.0").
- Explain medical terms in plain words the first time you use them.
- Mention what is being done about any problems (tests, treatment, monitoring) in plain language.
- Keep it short: aim for 100-180 words. A patient should be able to read it in under a minute.
- Do not add a diagnosis, cause, or outcome that isn't stated in the report. Do not recommend treatment.
- If the report is a lab panel (a table of tests with reference ranges), focus almost entirely on values marked abnormal or outside range, and briefly reassure that other values were normal - do not restate the full table.
- If the report is a narrative clinical note, summarize the overall clinical picture and plan, not each sentence of the note.

Preserve only what's clinically necessary to keep the summary accurate: which side of the body is affected (left/right), whether something was found or ruled out, and how serious it is - but express these in plain words, not jargon."""

MAX_RETRIES = 4


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Set it in backend/.env as:\n"
            "  GROQ_API_KEY=your-actual-key-here"
        )
    return Groq(api_key=api_key)


def summarize_report(report_text: str, model: str = "openai/gpt-oss-20b") -> str:
    client = get_client()
    text = report_text
    truncated = False

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Write a short, plain-language summary of this report for the patient:\n\n{text}"},
                ],
                temperature=0.3,
            )
            summary = response.choices[0].message.content.strip()
            if truncated:
                summary += "\n\n(Note: this report was long and was shortened before summarizing - some sections near the end may not be reflected.)"
            return summary

        except APIStatusError as e:
            if e.status_code == 413 and attempt < MAX_RETRIES - 1:
                text = text[: len(text) // 2]
                truncated = True
                print(f"[summarize] 413 rate limit, retrying with {len(text)} chars (attempt {attempt + 2})")
                continue
            raise

    raise RuntimeError("Could not fit report within token limit even after repeated truncation.")


if __name__ == "__main__":
    sample_report = """
    PREOPERATIVE DIAGNOSIS: Acute appendicitis.
    POSTOPERATIVE DIAGNOSIS: Acute appendicitis with perforation.
    PROCEDURE: Laparoscopic appendectomy.
    The patient is a 34-year-old male who presented with right lower
    quadrant pain for two days. CT scan showed an inflamed appendix
    measuring 1.2 cm with evidence of perforation. No signs of abscess
    formation. The patient tolerated the procedure well.
    """
    summary = summarize_report(sample_report)
    print("--- Generated Summary ---\n")
    print(summary)