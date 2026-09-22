"""
Converts the cleaned MTSamples dataset into instruction-tuning JSONL,
ready for QLoRA fine-tuning.
"""

import json
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

BACKEND_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BACKEND_DIR / "data" / "processed" / "mtsamples_clean.csv"
OUTPUT_DIR = BACKEND_DIR / "data" / "processed"
TRAIN_OUTPUT = OUTPUT_DIR / "finetune_train.jsonl"
VAL_OUTPUT = OUTPUT_DIR / "finetune_val.jsonl"

INSTRUCTION = (
    "Summarize this medical report in simple, patient-friendly language. "
    "Preserve all measurements, left/right side details, negative findings, "
    "and severity mentioned in the report."
)


def build_example(row) -> dict:
    return {
        "instruction": INSTRUCTION,
        "input": row["transcription"],
        "output": row["description"],
        "medical_specialty": row["medical_specialty"],
    }


def main():
    df = pd.read_csv(INPUT_PATH)
    df = df[df["description"].str.len() >= 20]

    examples = [build_example(row) for _, row in df.iterrows()]
    train_examples, val_examples = train_test_split(examples, test_size=0.1, random_state=42)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(TRAIN_OUTPUT, "w", encoding="utf-8") as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(VAL_OUTPUT, "w", encoding="utf-8") as f:
        for ex in val_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Saved {len(train_examples)} training examples to {TRAIN_OUTPUT}")
    print(f"Saved {len(val_examples)} validation examples to {VAL_OUTPUT}")


if __name__ == "__main__":
    main()
