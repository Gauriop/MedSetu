"""
ingest.py
Accepts a medical report as plain text or a PDF file and returns clean text.
Tries direct text extraction first, falls back to OCR for scanned PDFs.

Requirements:
    pip install pdfplumber pytesseract pdf2image pillow
Also requires Tesseract OCR installed separately on Windows:
    https://github.com/UB-Mannheim/tesseract/wiki
"""

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

# If Tesseract isn't on PATH, uncomment and set this:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

MIN_TEXT_LENGTH_FOR_DIRECT_EXTRACTION = 50


def extract_text_direct(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def extract_text_ocr(pdf_path: str) -> str:
    images = convert_from_path(pdf_path)
    text_parts = [pytesseract.image_to_string(img) for img in images]
    return "\n".join(text_parts).strip()


def ingest_pdf(pdf_path: str) -> str:
    pdf_path = str(pdf_path)
    direct_text = extract_text_direct(pdf_path)

    if len(direct_text) >= MIN_TEXT_LENGTH_FOR_DIRECT_EXTRACTION:
        print(f"[ingest] Extracted {len(direct_text)} chars via direct text extraction.")
        return direct_text

    print("[ingest] Direct extraction yielded little/no text - falling back to OCR.")
    ocr_text = extract_text_ocr(pdf_path)
    print(f"[ingest] Extracted {len(ocr_text)} chars via OCR.")
    return ocr_text


def ingest_report(source, is_pdf: bool = None) -> str:
    if is_pdf is None:
        is_pdf = isinstance(source, (str, Path)) and str(source).lower().endswith(".pdf") and Path(source).exists()

    if is_pdf:
        return ingest_pdf(source)
    return str(source).strip()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_pdf_or_text_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    if input_path.lower().endswith(".pdf"):
        result = ingest_report(input_path, is_pdf=True)
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            result = ingest_report(f.read(), is_pdf=False)

    print("\n--- Extracted Text (first 1000 chars) ---\n")
    print(result[:1000])
