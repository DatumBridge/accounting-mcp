"""Register accounting MCP tools."""

from __future__ import annotations

import logging
from typing import Optional, Union

from pydantic import Field

from app.schemas import (
    BuildTAccountsResponse,
    ErrorBody,
    ExportWorkbookResponse,
    ParseNhatKyResponse,
)
from app.services import artifact_store
from app.services.ingest import IngestError, resolve_xlsx_bytes
from app.services.journal_parse import ParseError, parse_nhat_ky_chung_bytes
from app.services.sheets_export import ExportError, export_t_account_workbook as write_workbook
from app.services.t_accounts import PostError, build_t_accounts as post_t_accounts

logger = logging.getLogger(__name__)


def _err(code: str, message: str, retryable: bool = False) -> ErrorBody:
    return ErrorBody(error_code=code, error_message=message, retryable=retryable)


def _coerce_account_filter(
    account_filter: Optional[Union[list[str], str]],
) -> Optional[list[str]]:
    if account_filter is None:
        return None
    if isinstance(account_filter, str):
        parts = [p.strip() for p in account_filter.replace(";", ",").split(",")]
        return [p for p in parts if p] or None
    return [str(a).strip() for a in account_filter if str(a).strip()] or None


def register(mcp) -> None:
    @mcp.tool()
    def parse_nhat_ky_chung(
        attachment_id: Optional[str] = Field(
            default=None,
            description="Work Item / MCBP attachment id (xlsx). Requires agent_base_url or DATUMBRIDGE_AGENT_INTERNAL_URL.",
        ),
        file_id: Optional[str] = Field(
            default=None,
            description="Google Drive file id of uploaded .xlsx (binary download). Requires OAuth credentials.",
        ),
        file_base64: Optional[str] = Field(
            default=None,
            description="Base64-encoded .xlsx bytes (tests / small files).",
        json_schema_extra={"x-datumbridge-encoding": "base64"}
        ),
        sheet_name: Optional[str] = Field(
            default=None,
            description="Optional worksheet name; defaults to Nhật ký chung / first sheet.",
        ),
        agent_base_url: Optional[str] = Field(
            default=None,
            description="datumbridge-agent base URL for attachment download",
        ),
        bearer_token: Optional[str] = Field(
            default=None,
            description="Bearer for attachment API (or AGENT_INTERNAL_TOKEN)",
        ),
        tenant_id: Optional[str] = Field(
            default=None,
            description="Tenant scope for attachment API and artifact store (required in multi-tenant hosts)",
        ),
        credentials_path: Optional[str] = Field(default=None, description="OAuth token path for Drive"),
        credentials_json: Optional[str] = Field(default=None, description="OAuth token JSON for Drive"),
    ) -> ParseNhatKyResponse:
        """
        Parse Sổ nhật ký chung (.xlsx) into a persisted artifact.
        Detects header TK nợ / TK có / Giá trị. Does not send the full journal to an LLM.
        

        Capabilities: accounting.parse_nhat_ky_chung
Outputs: success
        """
        try:
            data, source = resolve_xlsx_bytes(
                attachment_id=attachment_id,
                file_id=file_id,
                file_base64=file_base64,
                agent_base_url=agent_base_url,
                bearer_token=bearer_token,
                tenant_id=tenant_id,
                credentials_path=credentials_path,
                credentials_json=credentials_json,
            )
            parsed = parse_nhat_ky_chung_bytes(data, sheet_name=sheet_name)
            # Strip narration from samples returned to LLM context (amounts/codes only)
            samples = []
            for s in (parsed.get("sampleEntries") or [])[:5]:
                samples.append(
                    {
                        "line": s.get("line"),
                        "date": s.get("date"),
                        "debit_account": s.get("debit_account"),
                        "credit_account": s.get("credit_account"),
                        "amount": s.get("amount"),
                    }
                )
            artifact_id = artifact_store.new_id("nkc")
            artifact_store.save_json(
                artifact_id,
                {"kind": "nhat_ky_chung", "source": source, **parsed},
                tenant_id=tenant_id,
            )
            return ParseNhatKyResponse(
                success=True,
                artifact_id=artifact_id,
                entry_count=parsed["entryCount"],
                skipped_rows=parsed.get("skippedRows"),
                mst=parsed.get("mst") or None,
                company=parsed.get("company") or None,
                date_min=parsed.get("dateMin"),
                date_max=parsed.get("dateMax"),
                sample_entries=samples,
                source=source,
            )
        except (IngestError, ParseError, artifact_store.ArtifactError) as e:
            logger.warning("parse_nhat_ky_chung failed: %s", e.message)
            return ParseNhatKyResponse(success=False, error=_err(e.code, e.message))
        except Exception as e:
            logger.exception("parse_nhat_ky_chung unexpected")
            return ParseNhatKyResponse(
                success=False, error=_err("INTERNAL", str(e), retryable=True)
            )

    @mcp.tool()
    def build_t_accounts(
        artifact_id: str = Field(..., description="Artifact id from parse_nhat_ky_chung"),
        circular: str = Field(
            default="TT200",
            description="Officer-selected circular: TT200 or TT133 (labels only; posting is mechanical).",
        ),
        account_filter: Optional[Union[list[str], str]] = Field(
            default=None,
            description="Optional account codes (list or comma-separated string); omit for full chart.",
        ),
        tenant_id: Optional[str] = Field(
            default=None,
            description="Must match tenant_id used when parsing the artifact",
        ),
    ) -> BuildTAccountsResponse:
        """
        Deterministic double-entry post: each line debits TK nợ and credits TK có by Giá trị.
        Fails closed if books do not balance or no lines post. Never invents account codes or amounts.
        

        Capabilities: accounting.build_t_accounts
Outputs: success
        """
        try:
            parsed = artifact_store.load_json(artifact_id, tenant_id=tenant_id)
            if "entries" not in parsed:
                return BuildTAccountsResponse(
                    success=False,
                    error=_err("INVALID_ARTIFACT", "artifact is not a parse_nhat_ky_chung result"),
                )
            entries = parsed.get("entries") or []
            filt = _coerce_account_filter(account_filter)
            built = post_t_accounts(entries, circular=circular, account_filter=filt)
            out_id = artifact_store.new_id("tac")
            artifact_store.save_json(
                out_id,
                {
                    "kind": "t_accounts",
                    "sourceArtifactId": artifact_id,
                    "mst": parsed.get("mst"),
                    "company": parsed.get("company"),
                    **built,
                },
                tenant_id=tenant_id,
            )
            preview = [
                {
                    "account": a["account"],
                    "debitTotal": a["debitTotal"],
                    "creditTotal": a["creditTotal"],
                    "net": a["net"],
                }
                for a in (built.get("accounts") or [])[:25]
            ]
            return BuildTAccountsResponse(
                success=True,
                artifact_id=out_id,
                circular=built.get("circular"),
                entry_count=built.get("entryCount"),
                account_count=built.get("accountCount"),
                total_debit=built.get("totalDebit"),
                total_credit=built.get("totalCredit"),
                balanced=built.get("balanced"),
                accounts_preview=preview,
            )
        except (PostError, artifact_store.ArtifactError) as e:
            logger.warning("build_t_accounts failed: %s", e.message)
            return BuildTAccountsResponse(success=False, error=_err(e.code, e.message))
        except Exception as e:
            logger.exception("build_t_accounts unexpected")
            return BuildTAccountsResponse(
                success=False, error=_err("INTERNAL", str(e), retryable=True)
            )

    @mcp.tool()
    def export_t_account_workbook(
        artifact_id: str = Field(..., description="Artifact id from build_t_accounts"),
        title: str = Field(default="Sơ đồ chữ T", description="Google Sheet title"),
        parent_folder_id: Optional[str] = Field(
            default=None, description="Optional Drive folder id"
        ),
        dry_run: bool = Field(
            default=False,
            description=(
                "If true, return sheet matrices without calling Google. "
                "If false, credentials are required (CREDENTIALS_REQUIRED when missing). "
                "Prefer catalog ht-nhat-ky-chung-t-account HITL before live export."
            ),
        ),
        tenant_id: Optional[str] = Field(
            default=None,
            description="Must match tenant_id used when building the artifact",
        ),
        credentials_path: Optional[str] = Field(default=None),
        credentials_json: Optional[str] = Field(default=None),
    ) -> ExportWorkbookResponse:
        """
        Create a Google Sheet with tabs T-accounts and Sơ đồ chữ T from a build artifact.
        Process-tab narrative is template-based; amounts are only from postings.
        Live Sheet create is a side effect — prefer catalog HITL confirm; use dry_run for preview.
        

        Capabilities: accounting.export_t_account_workbook
Outputs: success
        """
        try:
            built = artifact_store.load_json(artifact_id, tenant_id=tenant_id)
            if "accounts" not in built:
                return ExportWorkbookResponse(
                    success=False,
                    error=_err("INVALID_ARTIFACT", "artifact is not a build_t_accounts result"),
                )
            result = write_workbook(
                built,
                title=title,
                parent_folder_id=parent_folder_id,
                credentials_path=credentials_path,
                credentials_json=credentials_json,
                dry_run=dry_run,
            )
            return ExportWorkbookResponse(
                success=True,
                dry_run=bool(result.get("dryRun")),
                spreadsheet_id=result.get("spreadsheetId"),
                spreadsheet_url=result.get("spreadsheetUrl"),
                title=result.get("title"),
                tabs=result.get("tabs"),
                account_count=result.get("accountCount") or built.get("accountCount"),
                entry_count=result.get("entryCount") or built.get("entryCount"),
                matrices=result.get("matrices"),
            )
        except (ExportError, artifact_store.ArtifactError) as e:
            logger.warning("export_t_account_workbook failed: %s", e.message)
            return ExportWorkbookResponse(success=False, error=_err(e.code, e.message))
        except Exception as e:
            logger.exception("export_t_account_workbook unexpected")
            return ExportWorkbookResponse(
                success=False, error=_err("INTERNAL", str(e), retryable=True)
            )
