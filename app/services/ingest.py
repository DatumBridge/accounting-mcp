"""Load nhật ký chung .xlsx bytes from attachment / Drive / base64."""

from __future__ import annotations

import base64
import io
import os
from typing import Optional, Tuple

import requests


class IngestError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def decode_file_base64(file_base64: str) -> bytes:
    raw = (file_base64 or "").strip()
    if not raw:
        raise IngestError("INVALID_INPUT", "file_base64 is empty")
    try:
        # tolerate data-URL prefix
        if "," in raw and raw.lower().startswith("data:"):
            raw = raw.split(",", 1)[1]
        return base64.b64decode(raw, validate=False)
    except Exception as exc:
        raise IngestError("INVALID_BASE64", f"file_base64 is not valid Base64: {exc}") from exc


def fetch_attachment_bytes(
    attachment_id: str,
    *,
    agent_base_url: Optional[str] = None,
    bearer_token: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> bytes:
    """Download Work Item attachment content from datumbridge-agent."""
    aid = (attachment_id or "").strip()
    if not aid:
        raise IngestError("INVALID_INPUT", "attachment_id is required")
    base = (agent_base_url or os.environ.get("DATUMBRIDGE_AGENT_INTERNAL_URL") or "").rstrip("/")
    if not base:
        raise IngestError(
            "AGENT_URL_REQUIRED",
            "attachment_id requires agent_base_url or DATUMBRIDGE_AGENT_INTERNAL_URL",
        )
    token = (bearer_token or os.environ.get("AGENT_INTERNAL_TOKEN") or "").strip()
    url = f"{base}/design/attachments/{aid}/content"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id.strip()
    try:
        resp = requests.get(url, headers=headers, timeout=120)
    except requests.RequestException as exc:
        raise IngestError("AGENT_FETCH_FAILED", f"attachment download failed: {exc}") from exc
    if resp.status_code == 404:
        raise IngestError("ATTACHMENT_NOT_FOUND", f"attachment {aid!r} not found")
    if resp.status_code in (401, 403):
        raise IngestError("ATTACHMENT_FORBIDDEN", f"attachment {aid!r} forbidden ({resp.status_code})")
    if resp.status_code >= 400:
        raise IngestError(
            "AGENT_FETCH_FAILED",
            f"attachment download HTTP {resp.status_code}: {resp.text[:200]}",
        )
    if not resp.content:
        raise IngestError("EMPTY_FILE", "attachment content is empty")
    return resp.content


def fetch_drive_file_bytes(
    file_id: str,
    *,
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Binary download of a Drive file (Excel .xlsx), not Sheets API."""
    from app.auth.credentials import get_credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    fid = (file_id or "").strip()
    if not fid:
        raise IngestError("INVALID_INPUT", "file_id is required")
    if not credentials_path and not credentials_json:
        raise IngestError(
            "CREDENTIALS_REQUIRED",
            "file_id requires credentials_path or credentials_json (Google Drive OAuth)",
        )
    try:
        creds = get_credentials(credentials_path=credentials_path, credentials_json=credentials_json)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = (
            drive.files()
            .get(fileId=fid, fields="id,name,mimeType,trashed", supportsAllDrives=True)
            .execute()
        )
        if meta.get("trashed"):
            raise IngestError("FILE_IN_TRASH", f"Drive file {fid!r} is in Trash")
        name = meta.get("name") or fid
        mime = (meta.get("mimeType") or "").lower()
        if "spreadsheet" in mime and "google-apps" in mime:
            # Native Google Sheet — export as xlsx
            request = drive.files().export_media(
                fileId=fid,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            request = drive.files().get_media(fileId=fid, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buf.getvalue()
        if not data:
            raise IngestError("EMPTY_FILE", f"Drive file {name!r} is empty")
        return data, name
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError("DRIVE_DOWNLOAD_FAILED", f"Drive download failed: {exc}") from exc


def resolve_xlsx_bytes(
    *,
    attachment_id: Optional[str] = None,
    file_id: Optional[str] = None,
    file_base64: Optional[str] = None,
    agent_base_url: Optional[str] = None,
    bearer_token: Optional[str] = None,
    tenant_id: Optional[str] = None,
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Pick exactly one ingest source. Returns (bytes, source_label)."""
    sources = [
        bool((attachment_id or "").strip()),
        bool((file_id or "").strip()),
        bool((file_base64 or "").strip()),
    ]
    if sum(1 for s in sources if s) != 1:
        raise IngestError(
            "INVALID_INPUT",
            "Provide exactly one of: attachment_id, file_id, or file_base64",
        )
    if (file_base64 or "").strip():
        return decode_file_base64(file_base64), "file_base64"
    if (attachment_id or "").strip():
        data = fetch_attachment_bytes(
            attachment_id,
            agent_base_url=agent_base_url,
            bearer_token=bearer_token,
            tenant_id=tenant_id,
        )
        return data, f"attachment:{attachment_id.strip()}"
    data, name = fetch_drive_file_bytes(
        file_id or "",
        credentials_path=credentials_path,
        credentials_json=credentials_json,
    )
    return data, f"drive:{name}"
