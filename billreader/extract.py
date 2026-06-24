"""Gemini extraction."""

from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel


class BillData(BaseModel):
    """Returned structure. Field meanings live in the prompt."""

    description: str
    company: str
    bill_id: str
    bill_date: str
    nett: float | None
    tax: float | None
    tax_percent: str
    total: float | None


PROMPT = Path(__file__).with_name("prompt.txt").read_text(encoding="utf-8")


def extract_bill(client: genai.Client, model: str, pdf_bytes: bytes) -> BillData:
    response = client.models.generate_content(
        model=model,
        contents=[
            PROMPT,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=BillData,
        ),
    )
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, BillData):
        return parsed
    return BillData.model_validate_json(response.text)
