# Teammate Handover

Last updated: 2026-11-15. Written so a teammate can clone the repository and continue. Everything below reflects what was actually done and verified; anything not done is stated as not done.

## 1. Where the project stands

| Phase | Status |
|---|---|
| 1. Business Problem Definition | **Complete.** [business_problem.md](business_problem.md) |
| 2. Dataset Collection and Inspection | **Complete.** 541,909 rows, 8 columns inspected; findings and cleaning decisions in [dataset_description.md](dataset_description.md) |
| 3. PostgreSQL Warehouse Setup | **Complete and verified.** Docker PostgreSQL on `localhost:5434`; connection and permission test passed 26/26. [postgres_setup.md](postgres_setup.md) |
| 4. Airbyte Data Ingestion | **Incomplete. Airbyte is NOT installed and running.** See sections 4 to 6 |
| 5. dbt, 6. Airflow, 7. Streamlit, 8. Final integration | Not started |

**The stack was revised on 2026-11-15:** BigQuery was replaced by local PostgreSQL because the team will not use billing or cloud authentication (reasons: section 18 of [business_problem.md](business_problem.md)). Earlier BigQuery files are kept in `documentation/archive/` and `ingestion/archive/`; BigQuery was never set up.

**No data has been ingested.** The warehouse schemas `raw`, `staging` and `analytics` exist but contain no tables. No Airbyte sync has ever run.

Screenshots `01` to `04` are all still pending (see [screenshot_checklist.md](screenshot_checklist.md)).

## 2. Set up your machine (PowerShell, project root)

Prerequisites: Windows 11, Docker Desktop (WSL2), Git, and a **Python 3.12** interpreter. The system Python 3.14 on the original machine was not used.

1. **Clone** the repository and open it in VS Code.
2. **Create the virtual environment and install packages**
   ```powershell
   <path-to-python-3.12> -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   (`dbt-postgres`, Airflow and Streamlit are not installed yet; they are commented out in `requirements.txt`.)
3. **Get the dataset** (it is not in Git). Download https://archive.ics.uci.edu/static/public/352/online+retail.zip, extract `Online Retail.xlsx` into `dataset/original/`, and compare its SHA-256 with the value in [dataset_description.md](dataset_description.md). Do not edit the workbook.
   ```powershell
   Get-FileHash -LiteralPath "dataset\original\Online Retail.xlsx" -Algorithm SHA256
   ```
4. **Create your local `.env`** (it is Git-ignored and must never be committed or shared):
   ```powershell
   Copy-Item .env.example .env
   ```
   Open `.env` and replace every `change-me` with your own password (letters and digits are safest). There are four: `POSTGRES_ADMIN_PASSWORD`, `AIRBYTE_DB_PASSWORD`, `DBT_DB_PASSWORD`, `STREAMLIT_DB_PASSWORD`. Each teammate chooses their own; they only protect your local database. **Set them before the first `docker compose up`**, because the init script applies them only when the data volume is first created.
5. **Start the warehouse and test it**
   ```powershell
   docker compose up -d warehouse-postgres
   docker compose ps          # wait for "healthy"
   .\.venv\Scripts\python.exe ingestion\test_postgres_connection.py
   ```
   Expected: `RESULT: PASS  (26/26 checks passed)`. One informational line about `CREATE SCHEMA IF NOT EXISTS raw` being refused is expected (see section 5).

Never run `docker compose down -v` unless you intend to wipe the warehouse. Stop it safely with `docker compose stop warehouse-postgres`.

## 3. PostgreSQL warehouse summary

- Container `ecommerce_warehouse_postgres` (`postgres:17`), published on `127.0.0.1:5434`. Port 5434 was used because a Windows PostgreSQL service uses 5432 and another local Docker project used 5433 on the original machine. If 5434 is busy on your machine, change `POSTGRES_PORT` in `.env`.
- Database `ecommerce_analytics`, schemas `raw`, `staging`, `analytics`.
- Roles: `airbyte_user` (owns `raw`), `dbt_user` (reads `raw`, owns `staging` and `analytics`), `streamlit_ro` (read-only on `analytics`).
- Verification on the original machine: connection test **26/26 passed**, including deliberate permission-denial checks. Full results: [postgres_setup.md](postgres_setup.md), section 7.

## 4. Phase 4 (Airbyte): what happened

- **Method chosen:** the official `abctl` installer, which runs Airbyte in a local Kubernetes (kind) cluster inside Docker.
- **abctl v0.30.4 was prepared locally:** `abctl-v0.30.4-windows-amd64.zip` (20,125,129 bytes) from the official GitHub release, SHA-256 `215c59f084d5b8dad4357b36e152353ee95811ee768c3b49c04ba33d566358c2` (matched the digest GitHub publishes). Only `abctl.exe` was extracted, to `.tools/abctl/` (Git-ignored). **You will not get this from Git; download it yourself** (section 6).
- **The installation stopped part way because of low Windows RAM.** The command was `abctl local install --low-resource-mode --no-browser` with `DO_NOT_TRACK=1`. While Docker pulled and unpacked Airbyte's images (about 1.3 GB each), the Docker/WSL VM grew from 1.3 GB to about 7.3 GB, and Windows available RAM dropped from 6.5 GB to about 370 MB. A safety check stopped the install at that point.
- **State left behind (on the original machine only):**
  - the kind cluster container `airbyte-abctl-control-plane` was created and is **stopped** (not deleted)
  - 8 Airbyte and Temporal images are already downloaded in the local Docker image store
  - the Airbyte application itself never started: no web UI, no pods running
- **No Airbyte sync has run, and the full dataset has not been ingested.** Nothing about Airbyte compatibility (source, destination, `InvoiceNo` as text, Full Refresh Overwrite) has been tested yet.
- **The proposed `.wslconfig` change was NOT approved and NOT applied.** `%USERPROFILE%\.wslconfig` does not exist. The proposal was `memory=6GB` with `autoMemoryReclaim=gradual`; it remains only a proposal and needs the project owner's approval before anyone applies it.

## 5. Known issues and risks for Phase 4

1. **Memory.** Airbyte recommends 4 or more CPUs and at least 8 GB of memory (2 CPUs and 8 GB in low-resource mode). Docker Desktop's VM was capped near 8.2 GB on the original machine, and the install needs more headroom on Windows than was available. Close memory-heavy apps first (a browser used about 2.4 GB) and make sure at least about 4 GB of Windows RAM is available before installing.
2. **`CREATE SCHEMA` permission.** `airbyte_user` is refused `CREATE SCHEMA IF NOT EXISTS raw` even though the schema exists. If Airbyte's destination connection test fails on this, the fix would be `GRANT CREATE ON DATABASE ecommerce_analytics TO airbyte_user;`. **Do not apply it without the project owner's approval**; it slightly widens least privilege.
3. **Airbyte reaching the warehouse.** Airbyte runs in its own cluster and must reach PostgreSQL at `host.docker.internal:5434`. The container is bound to `127.0.0.1` only, so this is **unverified** and may need a binding or network change.
4. **Reading the Excel file.** The Airbyte File source supports Excel and Full Refresh only. Local files may need an HTTP URL or a volume mount; `abctl` handling of local paths is unconfirmed. Plan to set the source reader option so `InvoiceNo` stays a string (`{"dtype": "string"}`), then verify the column type in PostgreSQL.
5. **dbt version.** A dry run resolved a pre-release `dbt-core`; pin a stable version in Phase 5 before installing.

## 6. Resuming Phase 4 safely

Do these in order and stop if anything looks wrong. The project owner asked for a spike first, then the full load.

1. **Free memory.** Close browsers and other heavy apps. Check:
   ```powershell
   (Get-Counter '\Memory\Available MBytes').CounterSamples.CookedValue
   ```
   Continue only if about 4000 or more.
2. **Confirm the warehouse is healthy** (`docker compose ps`).
3. **Get abctl** (if `.tools\abctl\abctl.exe` is missing): download `abctl-v0.30.4-windows-amd64.zip` from https://github.com/airbytehq/abctl/releases/tag/v0.30.4, check its SHA-256 against the value in section 4, and extract only `abctl.exe` into `.tools\abctl\`.
4. **Install or resume Airbyte** with telemetry off:
   ```powershell
   $env:DO_NOT_TRACK = '1'
   .\.tools\abctl\abctl.exe local install --low-resource-mode --no-browser
   ```
   On the original machine the cluster container already exists in a stopped state, so running the same command is expected to reuse it (not tested). Watch memory while it runs; stop if available RAM falls below about 1 GB. It can take up to 30 minutes. A `503 readiness probe` warning during install can be harmless.
5. **Open Airbyte** at http://localhost:8000. `abctl local credentials` shows the login and API client credentials. Treat them as secrets: do not paste them into chat, documents or commits.
6. **Phase 4A spike (small test).** Build the 744-row sample (written to Git-ignored `dataset/processed/`):
   ```powershell
   .\.venv\Scripts\python.exe ingestion\make_spike_sample.py
   ```
   Configure the File source and PostgreSQL destination (host `host.docker.internal`, port `5434`, database `ecommerce_analytics`, user `airbyte_user`, default schema `raw`), run one Full Refresh Overwrite sync, then check row count, `InvoiceNo` type and the `raw` schema.
7. **Phase 4B:** only if the spike works, ingest the real workbook and compare row counts (source 541,909). Document the connector's metadata columns, update `documentation/`, and capture screenshots `05` and `06`.

Do not modify `.wslconfig`, grant database permissions, or delete Docker volumes without the project owner's approval.

## 7. Approved data decisions to keep (Phase 2)

Raw data stays untouched. Exact duplicates are kept. A verified list of non-product stock codes (postage, fees, vouchers and so on) stays in gross valid-sales revenue but is excluded from merchandise rankings. Invoice `A563185` is a financial adjustment excluded from gross valid-sales revenue. "Highest revenue month" compares complete months only (Dec 2010 to Nov 2011), and the monthly trend shows December 2011 labelled as partial. Details and figures: [dataset_description.md](dataset_description.md).

## 8. What is and is not in Git

**In Git:** source, documentation, `docker-compose.yml`, init SQL and scripts, `.env.example`, and archived BigQuery files.

**Never in Git (and not available after cloning):** `.env` and passwords, `.venv/`, `.tools/`, `dataset/original/` (the workbook), `dataset/processed/` (generated samples), Docker volumes, and Kubernetes or `abctl` files under your user profile.

## 9. Useful commands

```powershell
docker compose ps                                  # warehouse status
docker compose stop warehouse-postgres             # stop, keeps data
.\.venv\Scripts\python.exe ingestion\test_postgres_connection.py
.\.venv\Scripts\python.exe dataset\inspect_dataset.py   # re-run dataset inspection
```
