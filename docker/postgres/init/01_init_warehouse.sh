#!/bin/sh
# Runs once, when the data volume is first created (official postgres image behaviour).
# Passes the role names and passwords from the container environment to the SQL file
# as psql variables, so no password is stored in a tracked file.
set -eu

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v dbname="$POSTGRES_DB" \
  -v airbyte_user="$AIRBYTE_DB_USER"     -v airbyte_password="$AIRBYTE_DB_PASSWORD" \
  -v dbt_user="$DBT_DB_USER"             -v dbt_password="$DBT_DB_PASSWORD" \
  -v streamlit_user="$STREAMLIT_DB_USER" -v streamlit_password="$STREAMLIT_DB_PASSWORD" \
  -f /sql/init_warehouse.sql
