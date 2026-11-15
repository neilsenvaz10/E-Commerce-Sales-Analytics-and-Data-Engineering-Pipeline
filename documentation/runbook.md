# Runbook: college demo (Airbyte Cloud + Snowflake)

Status: **prepared, not yet run.** No Airbyte Cloud or Snowflake account exists. Do the steps in order. Never paste keys, secrets or `.env` values into chat or commits.

## 1. Accounts (free trials, no payment details)
- **Snowflake** (30-day trial starts at signup): sign up at signup.snowflake.com with an email, skip any payment prompt, set up MFA for your own login, and note the account identifier (Snowsight: your name > Account > View account details).
- **Airbyte Cloud** (14-day trial starts at your **first successful sync**, so do this last): sign up, create a workspace, check that the **File** source and **Snowflake** destination are available, and create an application (User settings > Applications) to get a client ID and secret.

## 2. Keys (PowerShell; keep the files outside the repo)
```powershell
$ssl = 'C:\Program Files\Git\usr\bin\openssl.exe'
New-Item -ItemType Directory -Force "$HOME\.snowflake" | Out-Null
foreach ($n in 'airbyte','transform','reader') {
  & $ssl genrsa -out "$HOME\.snowflake\$($n)_rsa.pem" 2048
  & $ssl pkcs8 -topk8 -inform PEM -in "$HOME\.snowflake\$($n)_rsa.pem" -out "$HOME\.snowflake\$($n)_key.p8" -nocrypt
  & $ssl rsa -in "$HOME\.snowflake\$($n)_key.p8" -pubout -out "$HOME\.snowflake\$($n)_key.pub"
}
```
Open each `.pub` file and copy the text **between** the BEGIN/END lines as one line.

## 3. Snowflake setup
Paste [`snowflake/setup.sql`](../snowflake/setup.sql) into a Snowsight worksheet, replace the three `<...PUBLIC_KEY>` placeholders with those one-line public keys, and run it as `ACCOUNTADMIN`. Then run `DESC USER AIRBYTE_USER;` and check that `RSA_PUBLIC_KEY_FP` is filled in (same for the other two users).

## 4. Airbyte Cloud connection (one source, one destination, one connection)
- **Source: File.** Provider HTTPS, URL `https://raw.githubusercontent.com/neilsenvaz10/E-Commerce-Sales-Analytics-and-Data-Engineering-Pipeline/main/dataset/sample/online_retail_sample.csv` (works once the file is pushed to GitHub), format `csv`, dataset name `online_retail_sample`, reader options `{"dtype": "string"}` so `InvoiceNo` stays text.
- **Destination: Snowflake.** Host `<account>.snowflakecomputing.com`, role `AIRBYTE_ROLE`, warehouse `ECOMMERCE_WH`, database `ECOMMERCE_ANALYTICS`, default schema `RAW`, internal table schema `AIRBYTE_INTERNAL`, user `AIRBYTE_USER`, key-pair auth (paste the private key from `airbyte_key.p8` into the Airbyte form yourself).
- **Connection:** sync mode **Full Refresh | Overwrite**, schedule **manual**. Copy the connection ID from the page URL into `.env`.
- Open question to check at the first sync: if Airbyte's connection test needs `CREATE SCHEMA` on the database, tell the project owner (do not grant it silently).

## 5. Local settings
Copy `.env.example` to `.env` and fill in the `AIRBYTE_*` and `SNOWFLAKE_*` values (key paths with forward slashes). Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml`.

## 6. Run the pieces
```powershell
# dbt on its own (separate environment)
<python-3.12> -m venv .venv-dbt
.\.venv-dbt\Scripts\python.exe -m pip install -r dbt_project\requirements.txt
cd dbt_project ; ..\.venv-dbt\Scripts\dbt.exe run ; ..\.venv-dbt\Scripts\dbt.exe test ; cd ..

# Airflow (Docker Desktop must be running; build takes several minutes)
docker compose -f docker-compose.airflow.yml up -d --build
# open http://localhost:8080 , unpause and trigger the DAG "ecommerce_pipeline"

# Streamlit
.\.venv\Scripts\streamlit.exe run streamlit_app\app.py
```
Expected: the DAG shows 5 green tasks; Snowflake has `RAW.ONLINE_RETAIL_SAMPLE` (744 rows), view `STAGING.STG_ONLINE_RETAIL` and table `ANALYTICS.FCT_SALES`; the app answers the three questions.

## 7. Check the results against a local calculation
`python ingestion\make_sample_csv.py` prints these expected values for the sample (same rules as `fct_sales`): **597** `fct_sales` rows (15 of them non-product charges), **72** orders, total revenue **10,210.21**, and revenue in 13 months:

| Month | Revenue | Month | Revenue | Month | Revenue |
|---|---|---|---|---|---|
| 2010-12 | 348.44 | 2011-05 | 1,516.52 | 2011-10 | 1,037.66 |
| 2011-01 | 353.19 | 2011-06 | 920.60 | 2011-11 | 503.70 |
| 2011-02 | 836.60 | 2011-07 | 639.31 | 2011-12 | 925.76 (partial month) |
| 2011-03 | 675.88 | 2011-08 | 1,009.18 | | |
| 2011-04 | 1,147.94 | 2011-09 | 295.43 | | |

If Snowflake differs, investigate before trusting the dashboard.

## 8. Before the trials end
Capture the screenshots in [screenshot_checklist.md](screenshot_checklist.md) and, if possible, a short screen recording, while the accounts are active. After the Airbyte trial (14 days) a card is needed to keep syncing; after the Snowflake trial (30 days) the account is suspended.
