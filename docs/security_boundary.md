# Licensed Dashboard Security Boundary

This SData BI dashboard uses a paid Maycee Retail entitlement. Credentials and
licensed Parquet files stay local to the runtime and are excluded from source
control.

## Allowed In Source Control

- Dashboard code, tests, and documentation.
- Placeholder environment variable names in `.env.example`.
- Non-sensitive S3 bucket and product-prefix examples.
- Aggregated screenshots approved for the SData website or blog.

## Never Commit Or Render

- `.env` or `.streamlit/secrets.toml`.
- AWS access key IDs or secret access keys.
- Downloaded licensed Parquet files or local cache metadata.
- Licence manifests, customer fulfilment records, or retrieval tokens.
- Customer-specific files or private operational data.

The dashboard reads credentials only while downloading the entitled snapshot.
It renders aggregates from the ignored local cache and never displays the
credential values, licence manifest, IAM username, or local cache path.

Run the repository boundary check before every commit:

```powershell
.\.venv\Scripts\python.exe scripts/check_repository_boundary.py
```
