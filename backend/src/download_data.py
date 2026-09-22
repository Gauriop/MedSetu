"""
Download the MTSamples medical transcription dataset (CC0 / public domain)
from a public GitHub mirror and save it locally.
"""

import pandas as pd
from pathlib import Path

MTSAMPLES_URL = "https://raw.githubusercontent.com/socd06/medical-nlp/master/data/mtsamples.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "mtsamples.csv"


def main():
    print(f"Downloading MTSamples dataset from:\n{MTSAMPLES_URL}\n")
    df = pd.read_csv(MTSAMPLES_URL)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} rows to {OUTPUT_PATH}")
    print("\nColumns:", list(df.columns))
    print("\nSpecialty counts:")
    print(df["medical_specialty"].value_counts())


if __name__ == "__main__":
    main()
