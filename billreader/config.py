"""Configuration loading from environment / .env."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_IGNORE_FOLDERS = ("Fahrtenbücher", "pdf")


@dataclass
class Config:
    gemini_api_key: str
    gemini_model: str
    service_account_info: dict
    folder_id: str
    ignore_folders: frozenset[str]


def _load_service_account_info() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        return json.loads(raw)
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE.")


def _load_ignore_folders() -> frozenset[str]:
    raw = os.environ.get("IGNORE_FOLDERS")
    names = raw.split(",") if (raw and raw.strip()) else DEFAULT_IGNORE_FOLDERS
    return frozenset(n.strip().lower() for n in names if n.strip())


def load_config() -> Config:
    api_key = (
        os.environ.get("GOOGLE__AI__API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise RuntimeError("GOOGLE__AI__API_KEY is not set.")

    folder_id = (
        os.environ.get("MANUAL_FOLDER_ID") or os.environ.get("FOLDER_ID") or ""
    ).strip()
    if not folder_id:
        raise RuntimeError("Set MANUAL_FOLDER_ID or FOLDER_ID.")

    return Config(
        gemini_api_key=api_key,
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip(),
        service_account_info=_load_service_account_info(),
        folder_id=folder_id,
        ignore_folders=_load_ignore_folders(),
    )
