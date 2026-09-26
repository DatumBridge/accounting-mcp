"""Pydantic response models for accounting MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    error_code: str
    error_message: str
    retryable: bool = False


class ParseNhatKyResponse(BaseModel):
    success: bool = True
    artifact_id: Optional[str] = None
    entry_count: Optional[int] = None
    skipped_rows: Optional[int] = None
    mst: Optional[str] = None
    company: Optional[str] = None
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    sample_entries: Optional[list[dict[str, Any]]] = None
    source: Optional[str] = None
    error: Optional[ErrorBody] = None


class BuildTAccountsResponse(BaseModel):
    success: bool = True
    artifact_id: Optional[str] = None
    circular: Optional[str] = None
    entry_count: Optional[int] = None
    account_count: Optional[int] = None
    total_debit: Optional[float] = None
    total_credit: Optional[float] = None
    balanced: Optional[bool] = None
    accounts_preview: Optional[list[dict[str, Any]]] = None
    error: Optional[ErrorBody] = None


class ExportWorkbookResponse(BaseModel):
    success: bool = True
    dry_run: bool = False
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    title: Optional[str] = None
    tabs: Optional[Any] = None
    account_count: Optional[int] = None
    entry_count: Optional[int] = None
    matrices: Optional[dict[str, Any]] = Field(
        default=None, description="Present when dry_run=true"
    )
    error: Optional[ErrorBody] = None
