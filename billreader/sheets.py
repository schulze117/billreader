"""Google Sheets helpers."""

from __future__ import annotations

from datetime import date, datetime

from .extract import BillData

TEMPLATE_TAB = "template"
RESERVED_TABS = {"template", "summary"}

_EPOCH = date(1899, 12, 30)


def _quote(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def _all_tabs(sheets, spreadsheet_id: str) -> dict[str, int]:
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in meta.get("sheets", [])
    }


def ensure_tab(sheets, spreadsheet_id: str, title: str) -> int:
    """Return the sheetId for `title`, duplicating the template tab if missing."""
    tabs = _all_tabs(sheets, spreadsheet_id)
    if title in tabs:
        return tabs[title]
    if TEMPLATE_TAB not in tabs:
        raise RuntimeError(f"Template tab '{TEMPLATE_TAB}' not found in the spreadsheet.")

    reply = (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "duplicateSheet": {
                            "sourceSheetId": tabs[TEMPLATE_TAB],
                            "insertSheetIndex": len(tabs),
                            "newSheetName": title,
                        }
                    }
                ]
            },
        )
        .execute()
    )
    return reply["replies"][0]["duplicateSheet"]["properties"]["sheetId"]


def existing_filenames(sheets, spreadsheet_id: str, title: str) -> set[str]:
    resp = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=f"{_quote(title)}!A2:A",
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )
    return {row[0].strip() for row in resp.get("values", []) if row and row[0].strip()}


def _date_cell(iso: str):
    iso = (iso or "").strip()
    if not iso:
        return ""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except ValueError:
        return iso
    return (d - _EPOCH).days


def append_row(
    sheets,
    spreadsheet_id: str,
    title: str,
    bill: BillData,
    filename_stem: str,
    drive_link: str,
) -> None:
    safe_stem = filename_stem.replace('"', "'")
    file_cell = f'=HYPERLINK("{drive_link}", "{safe_stem}")'

    row = [
        file_cell,
        bill.description or "",
        bill.company or "",
        bill.bill_id or "",
        _date_cell(bill.bill_date),
        bill.nett if bill.nett is not None else "",
        bill.tax if bill.tax is not None else "",
        bill.tax_percent or "",
        bill.total if bill.total is not None else "",
    ]

    sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{_quote(title)}!A:A",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"majorDimension": "ROWS", "values": [row]},
    ).execute()
