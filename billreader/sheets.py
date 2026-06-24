"""Google Sheets helpers."""

from __future__ import annotations

from datetime import date, datetime

from .extract import BillData

HEADERS = [
    "File_name",
    "Description",
    "Company",
    "Bill_id",
    "Bill_date",
    "Nett_€",
    "Tax_€",
    "Tax_%",
    "Total_€",
]

COL_BILL_DATE = 4
COLS_CURRENCY = (5, 6, 8)

CURRENCY_PATTERN = "[$€]#,##0.00"
DATE_PATTERN = "DD.MM.YYYY"

_EPOCH = date(1899, 12, 30)


def _quote(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def _sheet_id(sheets, spreadsheet_id: str, title: str) -> int | None:
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    return None


def _column_format_request(sheet_id: int, col: int, fmt_type: str, pattern: str) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "startColumnIndex": col,
                "endColumnIndex": col + 1,
            },
            "cell": {"userEnteredFormat": {"numberFormat": {"type": fmt_type, "pattern": pattern}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _initialise_tab(sheets, spreadsheet_id: str, sheet_id: int) -> None:
    requests: list[dict] = [
        {
            "updateCells": {
                "rows": [
                    {"values": [{"userEnteredValue": {"stringValue": h}} for h in HEADERS]}
                ],
                "fields": "userEnteredValue",
                "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0},
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        _column_format_request(sheet_id, COL_BILL_DATE, "DATE", DATE_PATTERN),
    ]
    for col in COLS_CURRENCY:
        requests.append(_column_format_request(sheet_id, col, "NUMBER", CURRENCY_PATTERN))

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def ensure_tab(sheets, spreadsheet_id: str, title: str) -> int:
    existing = _sheet_id(sheets, spreadsheet_id, title)
    if existing is not None:
        return existing

    reply = (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )
        .execute()
    )
    sheet_id = reply["replies"][0]["addSheet"]["properties"]["sheetId"]
    _initialise_tab(sheets, spreadsheet_id, sheet_id)
    return sheet_id


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
