"""
POST /api/extract
Runs rule-based extraction on report/summary text, and compares two texts
for information preservation (used for both summary and translation checks).
"""

import sys
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from extract_rules import extract_all, compare_preservation  # noqa: E402

router = APIRouter()


class ExtractRequest(BaseModel):
    text: str


class PreservationRequest(BaseModel):
    original: str
    generated: str


@router.post("/extract")
def extract_endpoint(req: ExtractRequest):
    result = extract_all(req.text)
    return result.to_dict()


@router.post("/extract/preservation")
def preservation_endpoint(req: PreservationRequest):
    return compare_preservation(req.original, req.generated)
