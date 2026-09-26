"""Create Google Sheet from workbook matrices."""

from __future__ import annotations

from typing import Any, Optional

from googleapiclient.discovery import build

from app.auth.credentials import AuthError, get_credentials
from app.services.layout import workbook_matrices


class ExportError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _chunk_values(values: list[list[Any]], size: int = 500) -> list[list[list[Any]]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def export_t_account_workbook(
    build: dict[str, Any],
    *,
    title: str = "Sơ đồ chữ T",
    parent_folder_id: Optional[str] = None,
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    matrices = workbook_matrices(build)
    if dry_run:
        return {
            "dryRun": True,
            "title": title,
            "tabs": {k: {"rowCount": len(v)} for k, v in matrices.items()},
            "matrices": matrices,
            "spreadsheetId": None,
            "spreadsheetUrl": None,
            "accountCount": build.get("accountCount"),
            "entryCount": build.get("entryCount"),
        }

    if not credentials_path and not credentials_json:
        raise ExportError(
            "CREDENTIALS_REQUIRED",
            "credentials_path or credentials_json required when dry_run=false",
        )

    try:
        creds = get_credentials(credentials_path=credentials_path, credentials_json=credentials_json)
    except AuthError as exc:
        raise ExportError("CREDENTIALS_REQUIRED", exc.message) from exc

    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    body = {
        "properties": {"title": title},
        "sheets": [
            {"properties": {"title": name, "index": i}}
            for i, name in enumerate(matrices.keys())
        ],
    }
    try:
        created = sheets.spreadsheets().create(body=body).execute()
    except Exception as exc:
        raise ExportError("SHEETS_CREATE_FAILED", f"create spreadsheet failed: {exc}") from exc

    spreadsheet_id = created["spreadsheetId"]
    spreadsheet_url = created.get("spreadsheetUrl")

    if parent_folder_id:
        try:
            meta = drive.files().get(fileId=spreadsheet_id, fields="parents").execute()
            prev = meta.get("parents") or []
            drive.files().update(
                fileId=spreadsheet_id,
                addParents=parent_folder_id,
                removeParents=",".join(prev) if prev else None,
                fields="id,parents",
            ).execute()
        except Exception:
            pass  # non-fatal

    data = []
    for tab, values in matrices.items():
        # Sheets API rejects overly nested None; stringify lightly
        clean = [[("" if c is None else c) for c in row] for row in values]
        data.append({"range": f"'{tab}'!A1", "values": clean})
    try:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()
    except Exception as exc:
        raise ExportError("SHEETS_WRITE_FAILED", f"write ranges failed: {exc}") from exc

    return {
        "dryRun": False,
        "title": title,
        "spreadsheetId": spreadsheet_id,
        "spreadsheetUrl": spreadsheet_url,
        "tabs": list(matrices.keys()),
        "accountCount": build.get("accountCount"),
        "entryCount": build.get("entryCount"),
    }
