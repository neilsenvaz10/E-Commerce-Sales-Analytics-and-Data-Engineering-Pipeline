"""Simple orchestration DAG: Airbyte Cloud sync -> wait -> dbt run -> dbt test -> validate.

Airflow only sequences the steps. Airbyte (Cloud) ingests, dbt (in Snowflake) transforms.
Trigger it manually (schedule=None). Credentials come from environment variables
(see .env.example); nothing secret is stored in this file.

Airbyte Cloud API (v1): POST /applications/token, POST /jobs, GET /jobs/{jobId}.
Written to run on Airflow 2.11 and 3.x. NOT yet run: no Airbyte or Snowflake account exists.
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timedelta

import requests

try:  # Airflow 3
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2.x
    from airflow.decorators import dag, task

AIRBYTE_API = os.environ.get("AIRBYTE_API_URL", "https://api.airbyte.com/v1").rstrip("/")
POLL_SECONDS = 15
TIMEOUT_SECONDS = 20 * 60
FAILED_STATES = {"failed", "cancelled", "incomplete"}
DBT_BIN = os.environ.get("DBT_BIN", "dbt")
DBT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt_project")


def _token() -> str:
    """Airbyte access token (valid ~15 minutes). The docs spell the grant field two ways, so try both."""
    base = {"client_id": os.environ["AIRBYTE_CLIENT_ID"], "client_secret": os.environ["AIRBYTE_CLIENT_SECRET"]}
    last = None
    for grant_key in ("grant-type", "grant_type"):
        resp = requests.post(f"{AIRBYTE_API}/applications/token",
                             json={**base, grant_key: "client_credentials"}, timeout=30)
        if resp.ok:
            return resp.json()["access_token"]
        last = resp
    last.raise_for_status()


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Accept": "application/json"}


def _dbt(*args: str) -> None:
    """Run a dbt command and fail the task if it fails (output goes to the task log)."""
    cmd = [DBT_BIN, *args, "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"dbt {' '.join(args)} failed with exit code {result.returncode}")


@dag(
    dag_id="ecommerce_pipeline",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["ecommerce", "college-project"],
)
def ecommerce_pipeline():
    @task
    def trigger_airbyte_sync() -> int:
        resp = requests.post(f"{AIRBYTE_API}/jobs", headers=_headers(), timeout=30,
                             json={"connectionId": os.environ["AIRBYTE_CONNECTION_ID"], "jobType": "sync"})
        resp.raise_for_status()
        job_id = resp.json()["jobId"]
        print(f"Started Airbyte job {job_id}")
        return job_id

    @task(retries=0)
    def wait_for_airbyte(job_id: int) -> None:
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            resp = requests.get(f"{AIRBYTE_API}/jobs/{job_id}", headers=_headers(), timeout=30)
            resp.raise_for_status()
            job = resp.json()
            status = job["status"]
            print(f"Airbyte job {job_id}: {status} (rows synced: {job.get('rowsSynced')})")
            if status == "succeeded":
                return
            if status in FAILED_STATES:
                raise RuntimeError(f"Airbyte job {job_id} ended with status '{status}'")
            time.sleep(POLL_SECONDS)
        raise TimeoutError(f"Airbyte job {job_id} did not finish within {TIMEOUT_SECONDS} seconds")

    @task
    def dbt_run() -> None:
        _dbt("run")

    @task
    def dbt_test() -> None:
        _dbt("test")

    @task
    def validate_results() -> None:
        _dbt("run-operation", "assert_fct_sales_not_empty")

    job = trigger_airbyte_sync()
    wait = wait_for_airbyte(job)
    wait >> dbt_run() >> dbt_test() >> validate_results()


ecommerce_pipeline()
