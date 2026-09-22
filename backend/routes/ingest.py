"""
POST /api/ingest
Accepts either an uploaded PDF file or raw text, returns cleaned report text.
"""

import sys
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from ingest import ingest_report  # noqa: E402

router = APIRouter()


@router.post("/ingest")
async def ingest_endpoint(
    file: UploadFile = File(None),
    text: str = Form(None),
):
    if file is not None:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        try:
            extracted_text = ingest_report(tmp_path, is_pdf=suffix.lower() == ".pdf")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return JSONResponse({"text": extracted_text})

    if text is not None:
        extracted_text = ingest_report(text, is_pdf=False)
        return JSONResponse({"text": extracted_text})

    return JSONResponse({"error": "No file or text provided"}, status_code=400)
