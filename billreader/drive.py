"""Google Drive helpers."""

from __future__ import annotations

import io

from googleapiclient.http import MediaIoBaseDownload

_LIST_FIELDS = "nextPageToken, files(id, name)"


def _list_all(drive, query: str, *, order_by: str | None = None) -> list[dict]:
    items: list[dict] = []
    page_token = None
    while True:
        resp = (
            drive.files()
            .list(
                q=query,
                fields=_LIST_FIELDS,
                orderBy=order_by,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def list_spreadsheets(drive, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents "
        "and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    )
    return _list_all(drive, query, order_by="name_natural")


def list_subfolders(drive, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    return _list_all(drive, query, order_by="name_natural")


def list_pdfs(drive, folder_id: str) -> list[dict]:
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    return _list_all(drive, query, order_by="name_natural")


def download_pdf_bytes(drive, file_id: str) -> bytes:
    request = drive.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()
