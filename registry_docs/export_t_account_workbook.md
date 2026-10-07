# export_t_account_workbook

Create a Google Sheet with tabs T-accounts and Sơ đồ chữ T from a build artifact. Process-tab narrative is template-based; amounts are only from postings. Live Sheet create is a side effect — prefer catalog HITL confirm; use dry_run for preview.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `artifact_id` | yes | Artifact id from build_t_accounts |
| `title` | no | Google Sheet title |
| `parent_folder_id` | no | Optional Drive folder id |
| `dry_run` | no | If true, return sheet matrices without calling Google. If false, credentials are required (CREDENTIALS_REQUIRED when missing). Prefer catalog ht-nhat-ky-chung-t-account HITL before live export. |
| `tenant_id` | no | Must match tenant_id used when building the artifact |

## Cases

### Typical call

Input:

```json
{
  "artifact_id": "example-id"
}
```

Output:

```json
{
  "success": true,
  "dry_run": false,
  "spreadsheet_id": "example-id",
  "spreadsheet_url": "https://example.com/page",
  "title": "Status update",
  "tabs": [],
  "account_count": "example",
  "entry_count": "example",
  "matrices": []
}
```

### Missing `artifact_id`

The tool rejects the call and does not guess the missing value.

Input:

```json
{}
```

Output:

```json
{
  "success": false,
  "error": {
    "error_code": "invalid_argument",
    "error_message": "artifact_id is required",
    "retryable": false
  }
}
```
