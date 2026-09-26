# Changelog — accounting-mcp

## 2026-09-25

### Added

- Tools `parse_nhat_ky_chung`, `build_t_accounts`, `export_t_account_workbook` for deterministic nhật ký chung → T-account Google Sheet export.
- Ingest bridges: Work Item `attachment_id`, Drive `file_id` binary download, `file_base64`.
- Classical **T-accounts** tab and template **Sơ đồ chữ T** process tab; `dry_run` matrices without Sheets.
- Fail-closed `BOOKS_UNBALANCED`, `NO_POSTED_ENTRIES`, `HEADER_NOT_FOUND`, `CREDENTIALS_REQUIRED` (live export without OAuth).
- Tenant-scoped artifact store (`tenant_id` path + payload bind).

Product contract: kit ADR-0106, BR-WI-ACC-1.
