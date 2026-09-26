"""Minimal Google OAuth credential loader (pass-through like Drive MCP)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


class AuthError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _parse_expiry(creds_dict: dict) -> Optional[datetime]:
    raw = creds_dict.get("expiry") or creds_dict.get("expires_at") or creds_dict.get("token_expiry")
    if isinstance(raw, (int, float)) and raw > 0:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).replace(tzinfo=None)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    expires_in = creds_dict.get("expires_in")
    if isinstance(expires_in, int) and expires_in > 0:
        return datetime.utcnow() + timedelta(seconds=expires_in)
    return None


def get_credentials(
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> OAuth2Credentials:
    if credentials_json:
        data = json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json
    elif credentials_path:
        with open(credentials_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise AuthError("credentials_path or credentials_json required")

    if isinstance(data, dict) and (data.get("token") or data.get("access_token") or data.get("refresh_token")):
        creds = OAuth2Credentials(
            token=data.get("token") or data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes") or SCOPES,
        )
        expiry = _parse_expiry(data)
        if expiry:
            creds.expiry = expiry
        if not creds.valid:
            if creds.refresh_token and creds.client_id and creds.client_secret:
                try:
                    creds.refresh(Request())
                except RefreshError as exc:
                    raise AuthError(
                        "Google token expired or revoked. Reconnect Google Drive in Studio."
                    ) from exc
            else:
                raise AuthError("Google credentials are not valid and cannot be refreshed")
        return creds
    raise AuthError("Unrecognized credentials JSON (need OAuth token + refresh_token)")
