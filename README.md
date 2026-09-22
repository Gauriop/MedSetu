# MedSetu

**AI-Based Medical Report Summarization and Regional-Language (Marathi) Voice Assistant**

MedSetu helps patients understand their English medical reports by generating a concise, patient-friendly summary and presenting it in Marathi — as text and as speech. It is **not** a diagnostic tool and does not replace a doctor.

## Project Structure

```
MedSetu/
├── frontend/           Plain HTML/CSS/JS pages (landing, upload, report view)
├── backend/            FastAPI app + ML/NLP pipeline + data + models
│   ├── app.py          Main API entrypoint
│   ├── routes/         API endpoints (ingest, summarize, translate, extract, tts, ask)
│   ├── src/            Core pipeline scripts (data, summarization, translation, extraction, TTS, eval, fine-tuning)
│   ├── data/           Raw + processed MTSamples data (gitignored)
│   ├── models/         Fine-tuned LoRA adapter (gitignored)
│   ├── notebooks/      Exploration notebooks
│   └── reports/        Writeup, eval results, generated audio
├── .gitignore
└── README.md
```

## Status

- [x] Repo scaffolded, venv set up
- [x] MTSamples dataset downloaded + cleaned (4,902 rows)
- [x] Data exploration notebook
- [x] Full pipeline scripts written (ingest, extract, summarize, translate, tts, evaluate, fine-tune)
- [x] FastAPI backend wired to pipeline
- [x] Frontend pages built (landing, upload, report/translate view)
- [ ] QLoRA fine-tuning run completed (in progress — Colab, Llama 3.1 8B Instruct)
- [ ] Translation/TTS tested end-to-end with real outputs
- [ ] Evaluation run on real model outputs
- [ ] Final report

## Setup

### Backend
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Get the dataset
python src\download_data.py
python src\preprocess.py
python src\prepare_finetune_data.py

# Set your Groq API key (for zero-shot summarization)
setx GROQ_API_KEY "your-key-here"

# Run the API
uvicorn app:app --reload --port 8000
```
API docs available at http://localhost:8000/docs once running.

### Frontend
No build step — open `frontend/index.html` directly in a browser, or serve it:
```powershell
cd frontend
python -m http.server 5500
```
Then visit http://localhost:5500. The frontend calls the backend at `http://localhost:8000/api` (see `frontend/js/main.js`).

### Fine-tuning (GPU required — Colab or a GPU-equipped machine)
```
pip install bitsandbytes accelerate peft trl datasets
python src/finetune_qlora.py
python src/summarize_finetuned.py
```
Copy the resulting `models/mtsamples-summarizer-lora/` folder back into `backend/models/` (it's gitignored — copy it manually, don't rely on git).

## Dataset

**MTSamples** — medical transcription reports, CC0 (Public Domain).
Source: https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions

> Boyle, T. (2019). *Medical Transcriptions: Medical transcription data scraped from mtsamples.com* [Data set]. Kaggle.

## Disclaimer

MedSetu is an accessibility tool intended to help patients understand existing medical reports. It does not diagnose conditions, provide medical advice, or replace consultation with a qualified healthcare professional.
