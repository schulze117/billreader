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

MAX_ATTEMPTS = 3


def _generate(client: genai.Client, model: str, pdf_bytes: bytes, temperature: float) -> BillData:
    response = client.models.generate_content(
        model=model,
        contents=[
            PROMPT,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=BillData,
        ),
    )
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, BillData):
        return parsed
    return BillData.model_validate_json(response.text)


def _apply_no_tax_rule(bill: BillData) -> BillData:
    # No VAT on the bill (model reports 0%): net equals gross and tax is zero.
    pct = bill.tax_percent.strip().rstrip("%").replace(",", ".")
    if pct in ("0", "0.0"):
        bill.tax_percent = "0"
        bill.tax = 0.0
        if bill.total is not None:
            bill.nett = bill.total
        elif bill.nett is not None:
            bill.total = bill.nett
    return bill


def _is_complete(bill: BillData) -> bool:
    return (
        bool(bill.description.strip())
        and bool(bill.company.strip())
        and bool(bill.bill_id.strip())
        and bool(bill.bill_date.strip())
        and bool(bill.tax_percent.strip())
        and bill.nett is not None
        and bill.tax is not None
        and bill.total is not None
    )


def extract_bill(client: genai.Client, model: str, pdf_bytes: bytes) -> BillData:
    # Retry on the same PDF until every field is filled, up to MAX_ATTEMPTS.
    # First pass is deterministic; retries use a higher temperature to vary output.
    bill = _apply_no_tax_rule(_generate(client, model, pdf_bytes, 0.0))
    attempt = 1
    while attempt < MAX_ATTEMPTS and not _is_complete(bill):
        attempt += 1
        bill = _apply_no_tax_rule(_generate(client, model, pdf_bytes, 0.5))
    return bill
