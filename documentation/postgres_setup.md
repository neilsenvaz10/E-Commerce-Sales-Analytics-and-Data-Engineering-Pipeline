# PostgreSQL Warehouse Setup (Phase 3)

This replaces the earlier BigQuery plan (archived in [archive/bigquery_setup.md](archive/bigquery_setup.md)). Reasons are in section 18 of [business_problem.md](business_problem.md).

## 1. Design

| Item | Value |
|---|---|
| Engine | PostgreSQL 17 (official `postgres:17` Docker image) |
| Container | `ecommerce_warehouse_postgres`, service `warehouse-postgres` |
| Host address | `localhost:5434` (bound to 127.0.0.1 only) |
| Database | `ecommerce_analytics` |
| Schemas | `raw`, `staging`, `analytics` |
| Data storage | Docker named volume `ecommerce_analytics_warehouse_pgdata` |
| Existing Windows service | `postgresql-x64-18` on port 5432: **not used and not modified** |

Port 5434 on the host maps to 5432 inside the container. Containers on the same Docker network reach it as `warehouse-postgres:5432`.

**Port change from 5433 to 5434 (approved by the team on 2026-11-15):** when starting the container I found a stopped container from another local Docker project already configured to publish `127.0.0.1:5433`. Using 5433 would have made one of the two projects fail to start whenever both were wanted. Port 5434 was free, so I used it. The port is one variable (`POSTGRES_PORT` in `.env`); change it there to return to 5433 if that other project is stopped. That other project was not started, stopped or modified.

## 2. Roles and permissions (least privilege)

Defined in [`docker/postgres/sql/init_warehouse.sql`](../docker/postgres/sql/init_warehouse.sql). Passwords come from `.env`, never from a tracked file.

| Role | Used by | Access |
|---|---|---|
| `warehouse_admin` | Setup and maintenance only | Superuser of the container's database |
| `airbyte_user` | Airbyte | Owns schema `raw`; can create and write tables there; nothing else |
| `dbt_user` | dbt | Reads `raw`; owns `staging` and `analytics` |
| `streamlit_ro` | Streamlit | Reads `analytics` only; transactions are read-only by default |

Default privileges are set so tables that Airbyte creates in `raw` are readable by dbt, and tables or views that dbt creates in `analytics` are readable by Streamlit. The `public` schema is locked down and not used.

## 3. Files

| File | Purpose |
|---|---|
| [`docker-compose.yml`](../docker-compose.yml) | Warehouse container, port, volume, health check |
| [`docker/postgres/init/01_init_warehouse.sh`](../docker/postgres/init/01_init_warehouse.sh) | Runs once on first start; passes role names and passwords to the SQL |
| [`docker/postgres/sql/init_warehouse.sql`](../docker/postgres/sql/init_warehouse.sql) | Idempotent SQL for roles, schemas and grants |
| [`.env.example`](../.env.example) | Placeholder variables (copy to `.env`) |
| [`ingestion/test_postgres_connection.py`](../ingestion/test_postgres_connection.py) | Connection and privilege test |
| [`dbt_project/profiles.yml.example`](../dbt_project/profiles.yml.example) | dbt profile template (untested; dbt not installed yet) |
| [`.gitattributes`](../.gitattributes) | Keeps LF line endings for files mounted into the Linux container |

## 4. Setup steps (PowerShell, project root)

1. Start **Docker Desktop** and wait until it reports it is running.
2. Create `.env`: copy `.env.example` to `.env` and replace each `change-me` with your own password (letters and digits are safest). Never share these.
3. Start the warehouse:
   ```powershell
   docker compose up -d warehouse-postgres
   docker compose ps
   ```
   The first start downloads the image and runs the init script. Wait until the status shows `healthy`.
4. Run the test:
   ```powershell
   .\.venv\Scripts\python.exe ingestion\test_postgres_connection.py
   ```
   Exit code 0 means every required check passed.

Stop without losing data: `docker compose stop warehouse-postgres`. **Do not run `docker compose down -v`** unless you want to delete the warehouse volume.

If the roles or passwords must be changed later, edit `.env` and re-run the idempotent SQL:
```powershell
docker compose exec -T warehouse-postgres sh /docker-entrypoint-initdb.d/01_init_warehouse.sh
```

## 5. What the test checks

`test_postgres_connection.py` uses real connections and temporary tables named `_connection_test`, which it removes afterwards. It never prints credentials.

- every role connects and runs `SELECT 1`
- the three schemas exist with the expected owners
- Airbyte can create and write in `raw` but not in `staging` or `analytics`
- dbt can read what Airbyte created, write to `staging` and `analytics`, create views, but not write to `raw`
- Streamlit can read tables and views in `analytics`, but cannot write, create objects, or read `raw` and `staging`
- an informational probe records whether `airbyte_user` may run `CREATE SCHEMA IF NOT EXISTS raw`, which Airbyte may do in Phase 4

## 6. Phase 4 notes (not done yet)

- Airbyte runs in its own local cluster and must reach the warehouse at `host.docker.internal:5434`. The container is currently bound to 127.0.0.1; if Airbyte cannot connect, binding or Docker network settings will need review. This is **unverified**.
- **Observed:** `airbyte_user` is refused `CREATE SCHEMA IF NOT EXISTS raw` (permission denied for the database), even though the schema already exists. If Airbyte's connection test runs that statement, it will fail. The fix, to be applied only if needed, is `GRANT CREATE ON DATABASE ecommerce_analytics TO airbyte_user;`, a small widening of least privilege.
- Docker Desktop's Linux VM currently reports about 8.2 GB of memory. Airbyte recommends at least 8 GB and Airflow at least 4 GB, so running both together will need a memory decision later (not changed here).
- Airbyte's typed column names keep their case (for example `InvoiceNo`), so dbt staging must quote or rename them.

## 7. Verification results (run on 2026-11-15, real output)

**Environment:** Docker Engine 29.9.2 then 29.9.3 (Docker Desktop updated itself during the session), Docker Compose v5.6.1, image `postgres:17`, server `PostgreSQL 17.11`.

| Check | Result |
|---|---|
| `docker compose config` | Valid (exit 0) |
| `docker compose up -d warehouse-postgres` | Container, network and volume created; only this service started |
| Health check | `healthy`; `docker compose ps` shows `127.0.0.1:5434->5432/tcp` |
| Init script (first start) | Ran once, no `ERROR` lines: 3 roles created, 3 schemas created, grants applied |
| Database | `ecommerce_analytics` exists |
| Schemas and owners | `raw` owned by `airbyte_user`; `staging` and `analytics` owned by `dbt_user` |
| Roles | `airbyte_user`, `dbt_user`, `streamlit_ro`: login, not superuser, no CREATEDB, no CREATEROLE. `streamlit_ro` has `default_transaction_read_only=on` |
| Schema privileges | `airbyte_user`: raw (usage, create) only. `dbt_user`: raw (usage), staging and analytics (usage, create). `streamlit_ro`: analytics (usage) only. No role can use `public` |
| `ingestion/test_postgres_connection.py` | **26 of 26 checks passed**, exit code 0 |
| Idempotent re-apply of the init SQL | Ran again with exit 0 and no errors; the test passed again afterwards |
| Restart persistence | Docker Desktop updated and restarted the engine mid-session; the container came back, skipped initialisation ("database directory appears to contain a database"), and the test then passed against the same data |
| Leftover test objects | 0 tables and 0 views in the three schemas after the run |

**Test details (all PASS):**
- all four roles connect and run `SELECT 1`
- Airbyte can create and write tables in `raw`; it is refused in `staging` and `analytics` (InsufficientPrivilege)
- dbt reads a table Airbyte created in `raw`; it is refused `INSERT` and `CREATE TABLE` in `raw`; it can create tables in `staging` and `analytics` and a view in `analytics`
- Streamlit reads the table and the view dbt created in `analytics`; it is refused `INSERT` and `CREATE TABLE` there, and refused `SELECT` on `raw` and `staging`
- Streamlit's read-only default is `on`, and with that default switched off its writes are **still refused by the grants** (InsufficientPrivilege), so there are two separate protections

**Informational finding:** `airbyte_user` cannot run `CREATE SCHEMA IF NOT EXISTS raw` (see section 6).

**Existing Windows PostgreSQL service:** `postgresql-x64-18` was `Running` before and after, still listening on port 5432 with the same process ID (7448). It was never connected to or modified.

**Other Docker projects:** no other container or volume was started, stopped, removed or modified. The Docker host lists 15 containers (the 14 that existed before, plus ours). No remove or prune command was run, and `docker compose down -v` was never run.

**Secret check:** none of the four generated password values appears in any file outside the Git-ignored `.env`.

**Not verified here:** Airbyte reaching the database from its own cluster, dbt, Airflow and Streamlit connections (none installed yet), and the `04_postgres_setup.png` screenshot.
