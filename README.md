# Accounting MCP

Deterministic **Sổ nhật ký chung (.xlsx) → T-accounts → Google Sheet** tools for Weaver Deep / MCBP.

| Tool | Purpose |
|------|---------|
| `parse_nhat_ky_chung` | Ingest Work Item `attachment_id`, Drive `file_id`, or `file_base64`; stream-parse `TK nợ` / `TK có` / `Giá trị` |
| `build_t_accounts` | Double-entry post; fail closed if books do not balance |
| `export_t_account_workbook` | Create Google Sheet tabs **T-accounts** + **Sơ đồ chữ T** (or `dry_run` matrices) |

Amounts are never invented by an LLM. Local `~/Downloads` is out of scope — upload to the Work Item or Drive.

## Run locally

```bash
cd mcp/accounting-mcp
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements_dev.txt
pytest -q
uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
```

Health: `GET /health` → `{"status":"ok","service":"accounting-mcp"}`.

## Env

| Variable | Purpose |
|----------|---------|
| `ACCOUNTING_ARTIFACT_DIR` | Artifact JSON store (default `/tmp/accounting-artifacts`); tenant subdirs |
| `DATUMBRIDGE_AGENT_INTERNAL_URL` | Agent base for attachment download |
| `AGENT_INTERNAL_TOKEN` | Bearer for attachment API |

Pass matching `tenant_id` on parse → build → export. Live export (`dry_run=false`) requires Google OAuth; missing credentials → `CREDENTIALS_REQUIRED`.

Drive `file_id` and Sheet export require Google OAuth `credentials_json` / `credentials_path` (same pass-through pattern as `google-drive-mcp`).

## Docker

```bash
docker build -t accounting-mcp .
docker run --rm -p 8000:8000 accounting-mcp
```

## Product docs

Kit ADR-0106, BR-WI-ACC-1, `docs/organization/hanoi-tax-department/hanoi-tax-department-seed.md`.
