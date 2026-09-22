"""
Clean and preprocess the raw MTSamples dataset.
"""

import pandas as pd
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BACKEND_DIR / "data" / "raw" / "mtsamples.csv"
OUTPUT_PATH = BACKEND_DIR / "data" / "processed" / "mtsamples_clean.csv"

MIN_TRANSCRIPTION_LENGTH = 200  # characters


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    df = pd.read_csv(RAW_PATH)

    df = df.rename(columns={"Unnamed: 0": "note_id"})
    df = df.dropna(subset=["transcription"])

    df["transcription"] = df["transcription"].apply(clean_text)
    df["description"] = df["description"].apply(clean_text)

    before = len(df)
    df = df[df["transcription"].str.len() >= MIN_TRANSCRIPTION_LENGTH]
    print(f"Dropped {before - len(df)} rows shorter than {MIN_TRANSCRIPTION_LENGTH} chars")

    df = df[["note_id", "medical_specialty", "sample_name", "description", "transcription", "keywords"]]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} cleaned rows to {OUTPUT_PATH}")
    print(df["medical_specialty"].value_counts().head(10))


if __name__ == "__main__":
    main()
