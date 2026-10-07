# parse_nhat_ky_chung

Parse Sổ nhật ký chung (.xlsx) into a persisted artifact. Detects header TK nợ / TK có / Giá trị. Does not send the full journal to an LLM.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `attachment_id` | no | Work Item / MCBP attachment id (xlsx). Requires agent_base_url or DATUMBRIDGE_AGENT_INTERNAL_URL. |
| `file_id` | no | Google Drive file id of uploaded .xlsx (binary download). Requires OAuth credentials. |
| `file_base64` | no | Base64-encoded .xlsx bytes (tests / small files). |
| `sheet_name` | no | Optional worksheet name; defaults to Nhật ký chung / first sheet. |
| `agent_base_url` | no | datumbridge-agent base URL for attachment download |
| `bearer_token` | no | Bearer for attachment API (or AGENT_INTERNAL_TOKEN) |
| `tenant_id` | no | Tenant scope for attachment API and artifact store (required in multi-tenant hosts) |

## Cases

### Typical call

Input:

```json
{}
```

Output:

```json
{
  "success": true,
  "artifact_id": "example-id",
  "entry_count": "example",
  "skipped_rows": [],
  "mst": "example",
  "company": "example",
  "date_min": "2026-09-08",
  "date_max": "2026-09-08",
  "sample_entries": [],
  "source": "example"
}
```
