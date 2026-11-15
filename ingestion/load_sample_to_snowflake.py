"""Load dataset/sample/online_retail_sample.csv into Snowflake RAW.ONLINE_RETAIL_SAMPLE.

Replaces the Airbyte Cloud step (Airbyte could not sync because of a credit restriction).
The login identity AIRBYTE_USER / AIRBYTE_ROLE is kept from the original design; the names are
historical: they now belong to this Python loader.

What it does
  * keeps every one of the 8 source columns as text, exactly as in the CSV, plus _LOADED_AT
  * blank CSV cells become NULL (the original workbook had empty cells)
  * removes nothing: cancellations, adjustments, missing values and repeated rows all load
  * repeatable: in ONE transaction it deletes the old rows and inserts all rows; any error or
    mismatch rolls back, so the table holds either the previous data or all rows, never both
  * refuses to touch a table it did not create (checked by column layout and table comment)
  * logs in with the private key file named by SNOWFLAKE_INGEST_PRIVATE_KEY_PATH; keys and
    credentials are never printed; output is counts only

Modes (project root, PowerShell):
  python ingestion\\load_sample_to_snowflake.py --dry-run   offline: validate the CSV, no connection
  python ingestion\\load_sample_to_snowflake.py --check     read-only Snowflake check, no changes
  python ingestion\\load_sample_to_snowflake.py             load (writes RAW.ONLINE_RETAIL_SAMPLE)
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = Path(os.getenv("INGEST_CSV_PATH", ROOT / "dataset" / "sample" / "online_retail_sample.csv"))

HEADER = ["InvoiceNo", "StockCode", "Description", "Quantity",
          "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
EXPECTED_ROWS = 744                      # the approved sample
SCHEMA, TABLE = "RAW", "ONLINE_RETAIL_SAMPLE"
FULL_NAME = f"{SCHEMA}.{TABLE}"
MARKER = "Loaded by ingestion/load_sample_to_snowflake.py (Python replaces Airbyte Cloud)"

COLUMNS = [c.upper() for c in HEADER]                      # INVOICENO ... COUNTRY (unquoted)
EXPECTED_LAYOUT = [(c, "TEXT") for c in COLUMNS] + [("_LOADED_AT", "TIMESTAMP_NTZ")]

SQL_COLUMNS = ("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
               f"WHERE TABLE_SCHEMA = '{SCHEMA}' AND TABLE_NAME = '{TABLE}' ORDER BY ORDINAL_POSITION")
SQL_COMMENT = ("SELECT COMMENT FROM INFORMATION_SCHEMA.TABLES "
               f"WHERE TABLE_SCHEMA = '{SCHEMA}' AND TABLE_NAME = '{TABLE}'")
SQL_CREATE = (f"CREATE TABLE {FULL_NAME} ("
              + ", ".join(f"{c} VARCHAR" for c in COLUMNS)
              + ", _LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()) "
              + f"COMMENT = '{MARKER}'")
SQL_DELETE = f"DELETE FROM {FULL_NAME}"
SQL_INSERT = (f"INSERT INTO {FULL_NAME} ({', '.join(COLUMNS)}) "
              f"VALUES ({', '.join(['%s'] * len(COLUMNS))})")
SQL_VERIFY = ("SELECT COUNT(*), COUNT(DISTINCT INVOICENO), COUNT_IF(INVOICENO LIKE 'C%'), "
              "COUNT_IF(DESCRIPTION IS NULL), COUNT_IF(CUSTOMERID IS NULL) "
              f"FROM {FULL_NAME}")


class IngestError(Exception):
    """A problem we can explain to the user (nothing was changed in Snowflake)."""


# ---------------------------------------------------------------- CSV ---------------------------
def read_csv(path: Path = CSV_PATH) -> list[tuple]:
    """Rows as tuples of text, blanks as None. Validates header, width and row count."""
    if not path.is_file():
        raise IngestError(f"CSV not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != HEADER:
            raise IngestError(f"unexpected CSV header: {header}")
        rows = []
        for number, row in enumerate(reader, start=2):
            if len(row) != len(HEADER):
                raise IngestError(f"line {number} has {len(row)} fields, expected {len(HEADER)}")
            rows.append(tuple(value if value != "" else None for value in row))
    if len(rows) != EXPECTED_ROWS:
        raise IngestError(f"expected {EXPECTED_ROWS} data rows, found {len(rows)}")
    return rows


def csv_stats(rows: list[tuple]) -> tuple:
    """(rows, distinct invoices, cancelled-invoice rows, missing descriptions, missing customers)."""
    return (len(rows),
            len({r[0] for r in rows}),
            sum(r[0].startswith("C") for r in rows),
            sum(r[2] is None for r in rows),
            sum(r[6] is None for r in rows))


# ---------------------------------------------------------- Snowflake ---------------------------
def table_state(cur) -> str:
    """'absent', 'ours' (matches layout and marker) or 'unexpected'."""
    cur.execute(SQL_COLUMNS)
    layout = [(name, kind) for name, kind in cur.fetchall()]
    if not layout:
        return "absent"
    cur.execute(SQL_COMMENT)
    row = cur.fetchone()
    comment = row[0] if row else None
    return "ours" if layout == EXPECTED_LAYOUT and comment == MARKER else "unexpected"


def load(conn, rows: list[tuple]) -> tuple:
    """Create the table if absent, then replace its rows atomically. Returns verified counts."""
    cur = conn.cursor()
    state = table_state(cur)
    if state == "unexpected":
        raise IngestError(f"{FULL_NAME} already exists but was not created by this loader "
                          "(different columns or no loader marker). Nothing was changed.")
    if state == "absent":
        cur.execute(SQL_CREATE)          # DDL commits by itself
    expected = csv_stats(rows)
    try:
        cur.execute("BEGIN")
        cur.execute(SQL_DELETE)
        cur.executemany(SQL_INSERT, rows)
        cur.execute(SQL_VERIFY)
        actual = tuple(int(v) for v in cur.fetchone())
        if actual != expected:
            raise IngestError(f"verification failed: Snowflake {actual} vs CSV {expected} "
                              "(rows, distinct invoices, cancelled, missing description, missing customer)")
        cur.execute("COMMIT")
    except BaseException:
        try:
            cur.execute("ROLLBACK")
        except Exception:        # keep the original error; it is the useful one
            pass
        raise
    return actual


def check(cur) -> dict:
    """Read-only look at the target. Names and counts only; changes nothing."""
    cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_WAREHOUSE()")
    user, role, database, warehouse = cur.fetchone()
    found = {}
    for schema in ("RAW", "AIRBYTE_INTERNAL"):
        cur.execute(f"SHOW TABLES IN SCHEMA {schema}")
        found[schema] = [r[1] for r in cur.fetchall()]       # column 2 of SHOW TABLES is the name
    state = table_state(cur)
    count = None
    if state == "ours":
        cur.execute(f"SELECT COUNT(*) FROM {FULL_NAME}")
        count = int(cur.fetchone()[0])
    return {"user": user, "role": role, "database": database, "warehouse": warehouse,
            "tables": found, "target_state": state, "target_rows": count}


def connect():
    """Key-pair login. The key file is read in memory only and never printed."""
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    logging.getLogger("snowflake.connector").setLevel(logging.WARNING)

    needed = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_INGEST_PRIVATE_KEY_PATH"]
    missing = [n for n in needed if not os.getenv(n)]
    if missing:
        raise IngestError("set these environment variables (see .env.example): " + ", ".join(missing))
    key_file = Path(os.environ["SNOWFLAKE_INGEST_PRIVATE_KEY_PATH"])
    if not key_file.is_file():
        raise IngestError("the file named by SNOWFLAKE_INGEST_PRIVATE_KEY_PATH does not exist")
    private_key = serialization.load_pem_private_key(key_file.read_bytes(), password=None)
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.getenv("SNOWFLAKE_INGEST_USER", "AIRBYTE_USER"),       # historical name
        private_key=private_key.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
        role=os.getenv("SNOWFLAKE_INGEST_ROLE", "AIRBYTE_ROLE"),       # historical name
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ECOMMERCE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ECOMMERCE_ANALYTICS"),
        schema=SCHEMA,
        autocommit=False,
        login_timeout=30,
        network_timeout=120,
    )


# ---------------------------------------------------------------- CLI ---------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="validate the CSV only; no connection")
    mode.add_argument("--check", action="store_true", help="read-only Snowflake check; no changes")
    args = parser.parse_args(argv)

    try:
        rows = read_csv()
        stats = csv_stats(rows)
        print(f"CSV OK: {stats[0]} rows, {stats[1]} distinct invoices, {stats[2]} cancelled-invoice rows, "
              f"{stats[3]} missing descriptions, {stats[4]} missing customer IDs")
        if args.dry_run:
            print(f"DRY RUN: would load into {FULL_NAME} in one transaction (DELETE + INSERT, rollback on error). "
                  "No connection was made.")
            return 0
        conn = connect()
        try:
            if args.check:
                info = check(conn.cursor())
                print(f"Connected as {info['user']} with role {info['role']} "
                      f"(database {info['database']}, warehouse {info['warehouse']}); read-only check.")
                for schema, names in info["tables"].items():
                    print(f"  tables in {schema}: {', '.join(names) if names else '(none)'}")
                print(f"  {FULL_NAME}: {info['target_state']}"
                      + (f", {info['target_rows']} rows" if info["target_rows"] is not None else ""))
                return 0
            actual = load(conn, rows)
            print(f"LOADED {FULL_NAME}: {actual[0]} rows, {actual[1]} distinct invoices, {actual[2]} cancelled, "
                  f"{actual[3]} missing descriptions, {actual[4]} missing customers (all match the CSV).")
            return 0
        finally:
            conn.close()
    except IngestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:                      # unexpected: show the type and first line only
        print(f"ERROR: {type(exc).__name__}: {str(exc).splitlines()[0][:200] if str(exc) else ''}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
