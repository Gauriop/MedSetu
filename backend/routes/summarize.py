"""
POST /api/summarize
Generates a patient-friendly summary. Uses the zero-shot Groq model by
default; pass "use_finetuned": true to use your fine-tuned LoRA model
instead (only works on a GPU machine where the adapter is loaded).
"""

import sys
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from summarize import summarize_report  # noqa: E402

router = APIRouter()

# Lazily loaded only if someone actually requests the fine-tuned model,
# since it needs a GPU and takes time to load.
_finetuned_model = None
_finetuned_tokenizer = None


class SummarizeRequest(BaseModel):
    report_text: str
    use_finetuned: bool = False


@router.post("/summarize")
def summarize_endpoint(req: SummarizeRequest):
    if req.use_finetuned:
        global _finetuned_model, _finetuned_tokenizer
        from summarize_finetuned import load_finetuned_model, summarize_with_finetuned

        if _finetuned_model is None:
            _finetuned_model, _finetuned_tokenizer = load_finetuned_model()

        summary = summarize_with_finetuned(_finetuned_model, _finetuned_tokenizer, req.report_text)
    else:
        summary = summarize_report(req.report_text)

    return {"summary": summary, "model_used": "finetuned" if req.use_finetuned else "zero-shot"}
