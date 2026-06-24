"""Entry point."""

from __future__ import annotations

import logging

from google import genai

from . import drive as drive_api
from . import sheets as sheets_api
from .config import Config, load_config
from .extract import extract_bill
from .google_clients import build_clients

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("billreader")


def _stem(name: str) -> str:
    return name[:-4] if name.lower().endswith(".pdf") else name


def process_folder(
    drive, sheets, gemini: genai.Client, model: str, spreadsheet_id: str, folder_id: str
) -> None:
    for folder in drive_api.list_subfolders(drive, folder_id):
        title = folder["name"]
        sheets_api.ensure_tab(sheets, spreadsheet_id, title)
        seen = sheets_api.existing_filenames(sheets, spreadsheet_id, title)
        todo = [f for f in drive_api.list_pdfs(drive, folder["id"]) if _stem(f["name"]) not in seen]
        log.info("%s: %d new", title, len(todo))

        for pdf in todo:
            stem = _stem(pdf["name"])
            link = f"https://drive.google.com/file/d/{pdf['id']}/view"
            try:
                pdf_bytes = drive_api.download_pdf_bytes(drive, pdf["id"])
                bill = extract_bill(gemini, model, pdf_bytes)
                sheets_api.append_row(sheets, spreadsheet_id, title, bill, stem, link)
                log.info("  + %s", stem)
            except Exception:
                log.exception("  ! %s", stem)


def run(config: Config) -> None:
    drive, sheets = build_clients(config.service_account_info)
    gemini = genai.Client(api_key=config.gemini_api_key)

    spreadsheets = drive_api.list_spreadsheets(drive, config.folder_id)
    if not spreadsheets:
        raise RuntimeError(f"No spreadsheet in folder {config.folder_id}.")
    if len(spreadsheets) > 1:
        log.warning("Multiple spreadsheets found; using the first.")

    process_folder(
        drive, sheets, gemini, config.gemini_model, spreadsheets[0]["id"], config.folder_id
    )


def main() -> None:
    run(load_config())


if __name__ == "__main__":
    main()
