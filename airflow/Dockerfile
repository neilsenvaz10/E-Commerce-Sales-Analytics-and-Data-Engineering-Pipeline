# Minimal Airflow image: official Airflow 2.11 (Python 3.12) plus dbt in its own virtual
# environment, so dbt's dependencies cannot clash with Airflow's. NOT built or run yet.
FROM apache/airflow:2.11.2-python3.12
COPY --chown=airflow:root dbt_project/requirements.txt /tmp/dbt-requirements.txt
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/dbt-requirements.txt
