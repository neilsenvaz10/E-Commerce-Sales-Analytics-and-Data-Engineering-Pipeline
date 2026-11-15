"""Read-only BigQuery connection test (Phase 3).

Checks, in order:
  1. required settings are present in .env / environment
  2. credentials load (key file or Application Default Credentials)
  3. a trivial query runs (SELECT 1)
  4. each expected dataset exists and is in the expected location

It never prints credentials and never creates, changes, or deletes anything.

Usage (project root, PowerShell):
    .\\.venv\\Scripts\\python.exe ingestion\\test_bigquery_connection.py
    .\\.venv\\Scripts\\python.exe ingestion\\test_bigquery_connection.py --readonly
        (--readonly uses STREAMLIT_BQ_CREDENTIALS, the dashboard's read-only key)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.api_core.exceptions import GoogleAPIError, NotFound
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["GCP_PROJECT_ID", "BQ_LOCATION", "BQ_RAW_DATASET", "BQ_ANALYTICS_DATASET"]
OPTIONAL_DATASETS = ["BQ_STAGING_DATASET"]
PLACEHOLDERS = {
    "your-gcp-project-id",
    "path/to/pipeline-service-account-key.json",
    "path/to/read-only-dashboard-key.json",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def resolve_key_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_client(project_id: str, location: str, key_env: str) -> bigquery.Client:
    key_value = os.getenv(key_env, "")
    if key_value and key_value not in PLACEHOLDERS:
        key_path = resolve_key_path(key_value)
        if not key_path.is_file():
            raise FileNotFoundError(f"{key_env} points to a missing file: {key_path}")
        creds = service_account.Credentials.from_service_account_file(
            str(key_path), scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        print(f"auth: service account key file via {key_env} ({creds.service_account_email})")
        return bigquery.Client(project=project_id, credentials=creds, location=location)
    print("auth: Application Default Credentials (no key file configured)")
    return bigquery.Client(project=project_id, location=location)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only BigQuery connection test")
    parser.add_argument("--readonly", action="store_true",
                        help="use STREAMLIT_BQ_CREDENTIALS instead of GOOGLE_APPLICATION_CREDENTIALS")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    missing = [name for name in REQUIRED if not os.getenv(name) or os.getenv(name) in PLACEHOLDERS]
    if missing:
        return fail(f"set these in .env first: {', '.join(missing)}")

    project_id = os.environ["GCP_PROJECT_ID"]
    location = os.environ["BQ_LOCATION"]
    key_env = "STREAMLIT_BQ_CREDENTIALS" if args.readonly else "GOOGLE_APPLICATION_CREDENTIALS"
    print(f"project: {project_id}\nlocation: {location}\nmode: {'read-only (dashboard)' if args.readonly else 'pipeline'}")

    try:
        client = build_client(project_id, location, key_env)
        rows = list(client.query("SELECT 1 AS ok").result())
        if rows[0]["ok"] != 1:
            return fail("SELECT 1 returned an unexpected value")
        print("query: SELECT 1 -> OK")
    except (GoogleAPIError, FileNotFoundError, OSError, ValueError) as exc:
        return fail(f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # credential discovery errors are not GoogleAPIError
        return fail(f"{type(exc).__name__}: {exc}")

    wanted = [os.environ[n] for n in REQUIRED[2:]]
    wanted += [os.environ[n] for n in OPTIONAL_DATASETS if os.getenv(n)]
    ok = True
    for name in wanted:
        try:
            ds = client.get_dataset(f"{project_id}.{name}")
        except NotFound:
            print(f"dataset {name}: NOT FOUND")
            ok = False
            continue
        except GoogleAPIError as exc:
            print(f"dataset {name}: ERROR {exc}")
            ok = False
            continue
        same = ds.location.upper() == location.upper()
        print(f"dataset {name}: found, location={ds.location}" + ("" if same else f"  MISMATCH (expected {location})"))
        ok = ok and same

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
