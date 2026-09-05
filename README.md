# MedSetu

**AI-Based Medical Report Summarization and Regional-Language (Marathi) Voice Assistant**

MedSetu helps patients understand their English medical reports by generating a concise, patient-friendly summary and presenting it in Marathi — as text and as speech. It is **not** a diagnostic tool and does not replace a doctor; its goal is improving accessibility of existing medical reports for patients more comfortable in a regional Indian language.

## Objective

- Accept an English medical report (text or uploaded document/PDF).
- Generate a concise, clinically accurate, patient-friendly summary using an LLM (Llama 3.1 8B Instruct or similar), adapted via QLoRA fine-tuning.
- Translate the summary into Marathi using a medical-aware translation approach.
- Extract key medical information (anatomical location, findings, laterality, measurements, severity, negation, terminology) from both original and translated text.
- Detect whether important clinical information was lost or altered during summarization/translation (information-preservation module).
- Present the Marathi explanation as text and speech (TTS).
- (Optional) Support simple spoken questions about the report in Marathi (STT + report-grounded QA).
- Architecture designed to extend to other Indian regional languages in future work.

## Research Component

Compares pretrained vs. fine-tuned LLM vs. existing translation approaches on:
- Summarization quality
- Translation quality
- Medical terminology / numerical-value / laterality / negation preservation
- Overall medical meaning preservation
- Readability of the Marathi output

## Project Status

Currently in early data-preparation stage. See progress below.

- [x] Repo scaffolded (`data/`, `notebooks/`, `src/`, `models/`, `reports/`)
- [x] Python 3.11 virtual environment set up
- [x] MTSamples dataset downloaded (`src/download_data.py`)
- [ ] Data exploration and cleaning
- [ ] PDF/OCR ingestion module
- [ ] Zero-shot summarization with pretrained LLM
- [ ] QLoRA fine-tuning on MTSamples
- [ ] Marathi translation integration (IndicTrans2)
- [ ] Medical information extraction (rule-based + LLM-based)
- [ ] Information-preservation comparison module
- [ ] Marathi TTS integration
- [ ] Optional: Marathi STT + report-grounded QA
- [ ] Evaluation (ROUGE, BERTScore, chrF++, preservation metrics, human eval)
- [ ] Final report and writeup

## Dataset

**MTSamples** — medical transcription reports scraped from mtsamples.com, compiled by Tara Boyle.

- ~4,999 reports across 40 medical specialties (Surgery, Cardiovascular/Pulmonary, Orthopedic, Radiology, etc.)
- License: CC0 (Public Domain) — free to use, no approval process, no PHI/privacy concerns (samples, not real patient records)
- Source: https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions
- Downloaded locally via `src/download_data.py` into `data/raw/mtsamples.csv` (not committed to git; regenerate by running the script)

Citation:
> Boyle, T. (2019). *Medical Transcriptions: Medical transcription data scraped from mtsamples.com* [Data set]. Kaggle.

## Repository Structure

```
MedSetu/
├── data/
│   ├── raw/            # raw downloaded data (gitignored)
│   └── processed/      # cleaned data (gitignored)
├── notebooks/          # exploration and experiment notebooks
├── src/                # pipeline scripts (download, preprocess, summarize, translate, extract, tts, etc.)
├── models/             # fine-tuned LoRA adapters (gitignored)
├── reports/            # writeup, evaluation results
├── requirements.txt
└── README.md
```

## Setup

```powershell
# Clone the repo
git clone https://github.com/Gauriop/MedSetu.git
cd MedSetu

# Create and activate a Python 3.11 virtual environment
py -3.11 -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Getting the Dataset

```powershell
python src\download_data.py
```

This downloads MTSamples into `data/raw/mtsamples.csv` (~4,999 rows).

## Disclaimer

MedSetu is an accessibility tool intended to help patients understand existing medical reports. It does not diagnose conditions, provide medical advice, or replace consultation with a qualified healthcare professional.
