"""Simple orchestration DAG: Python load -> dbt run -> dbt test -> validate.

Airflow only sequences the steps. A Python script loads the sample CSV into Snowflake RAW, and
dbt transforms it inside Snowflake. (Airbyte Cloud was configured first but could not sync
because of a credit restriction, so this Python load replaced it.)

Trigger it manually (schedule=None). Credentials come from environment variables and mounted key
files (see docker-compose.airflow.yml and .env.example); nothing secret is stored here, and the
tasks only log counts and dbt output.
Written to run on Airflow 2.11 and 3.x. All four tasks have passed in Airflow with the dbt
cache fix (separate target/log paths).
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

try:  # Airflow 3
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2.x
    from airflow.decorators import dag, task

INGEST_PYTHON = os.environ.get("INGEST_PYTHON", "python")    # dbt venv: has the Snowflake connector
INGEST_SCRIPT = os.environ.get("INGEST_SCRIPT", "/opt/airflow/ingestion/load_sample_to_snowflake.py")
DBT_BIN = os.environ.get("DBT_BIN", "dbt")
DBT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt_project")


# dbt_project/ is bind-mounted from the Windows host. dbt's partial-parse cache (target/) written
# on Windows holds backslash paths and breaks dbt on Linux (KeyError on macros/...). So the
# container writes its own artifacts and logs to its own filesystem, never to the shared folder.
DBT_TARGET = os.environ.get("DBT_AIRFLOW_TARGET_PATH", "/tmp/dbt_target")
DBT_LOGS = os.environ.get("DBT_AIRFLOW_LOG_PATH", "/tmp/dbt_logs")


def _run(cmd: list[str], label: str, env: dict[str, str] | None = None) -> None:
    """Run a command, show its output in the task log, and fail the task if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")


def _dbt(*args: str) -> None:
    env = {**os.environ, "DBT_TARGET_PATH": DBT_TARGET, "DBT_LOG_PATH": DBT_LOGS}
    _run(
        [DBT_BIN, *args, "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR],
        f"dbt {' '.join(args)}",
        env=env,
    )


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
    def ingest_sample() -> None:
        # Repeatable: the loader replaces all rows in one transaction and rolls back on any error.
        _run([INGEST_PYTHON, INGEST_SCRIPT], "Python ingestion")

    @task
    def dbt_run() -> None:
        _dbt("run")

    @task
    def dbt_test() -> None:
        _dbt("test")

    @task
    def validate_results() -> None:
        # raw 744, valid sales 597, orders 72, revenue 10,210.21, 13 months
        _dbt("run-operation", "validate_sample_results")

    ingest_sample() >> dbt_run() >> dbt_test() >> validate_results()


ecommerce_pipeline()
