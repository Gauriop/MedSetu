import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load .env from the backend/ root regardless of where this script is run from
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SYSTEM_PROMPT = (
    "You are a medical assistant that explains clinical reports to patients "
    "in simple, clear, non-technical language. Do not add any diagnosis or "
    "medical advice beyond what is stated in the report. Preserve all "
    "important details exactly: measurements, left/right side, negative "
    "findings, and severity. Keep the summary concise (4-8 sentences)."
)


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Set it with:\n"
            '  setx GROQ_API_KEY "your-key-here"   (Windows, then restart terminal)'
        )
    return Groq(api_key=api_key)


def summarize_report(report_text: str, model: str = "openai/gpt-oss-20b") -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Summarize this medical report:\n\n{report_text}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


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