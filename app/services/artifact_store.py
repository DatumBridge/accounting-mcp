"""Persisted parse/build artifacts under ACCOUNTING_ARTIFACT_DIR.

Artifacts are tenant-scoped: path `{root}/{tenant_id}/{artifact_id}.json`.
Load requires the same tenant_id that was used at save (fail closed on mismatch).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

_TENANT_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")


class ArtifactError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _root() -> Path:
    raw = os.environ.get("ACCOUNTING_ARTIFACT_DIR", "").strip()
    if raw:
        p = Path(raw)
    else:
        p = Path("/tmp/accounting-artifacts")
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize_tenant_id(tenant_id: Optional[str]) -> str:
    """Map empty/missing to lab tenant `_local`; reject unsafe ids."""
    tid = (tenant_id or "").strip() or "_local"
    if not _TENANT_RE.match(tid) or ".." in tid or "/" in tid:
        raise ArtifactError("INVALID_TENANT", "tenant_id contains invalid characters")
    return tid


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _path(tenant_id: str, artifact_id: str) -> Path:
    return _root() / tenant_id / f"{artifact_id}.json"


def save_json(artifact_id: str, payload: dict[str, Any], *, tenant_id: Optional[str] = None) -> str:
    aid = (artifact_id or "").strip()
    if not aid or "/" in aid or ".." in aid:
        raise ArtifactError("INVALID_ARTIFACT", "artifact_id is required")
    tid = normalize_tenant_id(tenant_id)
    body = dict(payload)
    body["tenantId"] = tid
    dest = _path(tid, aid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return artifact_id


def load_json(artifact_id: str, *, tenant_id: Optional[str] = None) -> dict[str, Any]:
    aid = (artifact_id or "").strip()
    if not aid or "/" in aid or ".." in aid:
        raise ArtifactError("INVALID_ARTIFACT", "artifact_id is required")
    tid = normalize_tenant_id(tenant_id)
    path = _path(tid, aid)
    if not path.is_file():
        raise ArtifactError("ARTIFACT_NOT_FOUND", f"artifact {aid!r} not found for tenant")
    data = json.loads(path.read_text(encoding="utf-8"))
    stored = str(data.get("tenantId") or "").strip()
    if stored and stored != tid:
        raise ArtifactError("TENANT_MISMATCH", "artifact tenant_id does not match request")
    return data
