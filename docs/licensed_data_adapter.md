# Licensed Data Adapter

The dashboard uses the AWS access-key pair, bucket, prefix, and snapshot
boundary supplied through a Maycee Retail licence. The former placeholder
`MAYCEE_LICENCE_KEY` example is not part of the delivery contract.

## Configuration

Create an ignored `.env` in the repository root:

```dotenv
MAYCEE_AWS_ACCESS_KEY_ID=<issued-access-key-id>
MAYCEE_AWS_SECRET_ACCESS_KEY=<issued-secret-access-key>
MAYCEE_AWS_DEFAULT_REGION=ap-southeast-2
MAYCEE_S3_BUCKET=<issued-bucket>
MAYCEE_S3_PREFIX=<issued-prefix>
MAYCEE_SNAPSHOT_THROUGH=YYYY-MM
```

Existing process environment variables take precedence over the local file.

## Fetch And Run

```powershell
.\.venv\Scripts\python.exe scripts/fetch_licensed_data.py --dry-run
.\.venv\Scripts\python.exe scripts/fetch_licensed_data.py
.\.venv\Scripts\python.exe -m streamlit run app/Overview.py
```

The fetcher downloads transaction, item, and return facts through the licensed
snapshot month, plus the latest required customer, store, geography, product,
and category dimensions. It writes only to the ignored
`data/licensed_v1_0/` cache.

The IAM policy remains the authoritative access boundary. The local snapshot
setting narrows listing and download behaviour but cannot broaden S3 access.
