# build_t_accounts

Deterministic double-entry post: each line debits TK nợ and credits TK có by Giá trị. Fails closed if books do not balance or no lines post. Never invents account codes or amounts.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `artifact_id` | yes | Artifact id from parse_nhat_ky_chung |
| `circular` | no | Officer-selected circular: TT200 or TT133 (labels only; posting is mechanical). |
| `account_filter` | no | Optional account codes (list or comma-separated string); omit for full chart. |
| `tenant_id` | no | Must match tenant_id used when parsing the artifact |

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
  "artifact_id": "example-id",
  "circular": "example",
  "entry_count": "example",
  "account_count": "example",
  "total_debit": "example",
  "total_credit": "example",
  "balanced": "example",
  "accounts_preview": "example"
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
