"""PostgreSQL warehouse connection and privilege test (Phase 3).

Checks, using the real database from docker-compose.yml:
  1. required settings exist in .env and are not placeholders
  2. each role can connect and run SELECT 1 (admin, airbyte, dbt, streamlit)
  3. the schemas raw, staging and analytics exist
  4. least-privilege rules hold, by actually attempting operations as each role
  5. one informational probe: Airbyte's `CREATE SCHEMA IF NOT EXISTS raw`

Temporary tables named _connection_test are created and removed. Nothing else is
changed, no credentials are printed, and the existing Windows PostgreSQL service
(port 5432) is never contacted.

Usage (project root, PowerShell):
    .\\.venv\\Scripts\\python.exe ingestion\\test_postgres_connection.py
Exit code 0 = every required check passed, 1 = something failed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import errors, sql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
    "POSTGRES_ADMIN_USER", "POSTGRES_ADMIN_PASSWORD",
    "AIRBYTE_DB_USER", "AIRBYTE_DB_PASSWORD",
    "DBT_DB_USER", "DBT_DB_PASSWORD",
    "STREAMLIT_DB_USER", "STREAMLIT_DB_PASSWORD",
    "PG_RAW_SCHEMA", "PG_STAGING_SCHEMA", "PG_ANALYTICS_SCHEMA",
]
TEST_TABLE = "_connection_test"
DENIED = (errors.InsufficientPrivilege, errors.ReadOnlySqlTransaction)

results: list[tuple[str, bool]] = []


def record(label: str, passed: bool, detail: str = "") -> None:
    results.append((label, passed))
    print(f"{'PASS' if passed else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def short(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc).strip().splitlines()[0][:160]}"


def connect(user_env: str, password_env: str) -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ[user_env],
        password=os.environ[password_env],
        connect_timeout=5,
        autocommit=True,
    )


def qualified(schema: str) -> sql.Composed:
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(TEST_TABLE))


def expect_ok(label: str, conn: psycopg.Connection, statement: sql.Composable) -> bool:
    try:
        conn.execute(statement)
        record(label, True)
        return True
    except psycopg.Error as exc:
        record(label, False, short(exc))
        return False


def expect_denied(label: str, conn: psycopg.Connection, statement: sql.Composable) -> bool:
    try:
        conn.execute(statement)
        record(label, False, "operation succeeded but should have been refused")
        return False
    except DENIED as exc:
        record(label, True, f"refused: {type(exc).__name__}")
        return True
    except psycopg.Error as exc:
        record(label, False, f"unexpected error: {short(exc)}")
        return False


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    bad = [n for n in REQUIRED if not os.getenv(n) or os.getenv(n) == "change-me"]
    if bad:
        print(f"FAIL: set these in .env first: {', '.join(bad)}", file=sys.stderr)
        return 1

    raw, stg, ana = (os.environ[n] for n in ("PG_RAW_SCHEMA", "PG_STAGING_SCHEMA", "PG_ANALYTICS_SCHEMA"))
    print(f"target: {os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']} database={os.environ['POSTGRES_DB']}")

    roles = {
        "admin": ("POSTGRES_ADMIN_USER", "POSTGRES_ADMIN_PASSWORD"),
        "airbyte": ("AIRBYTE_DB_USER", "AIRBYTE_DB_PASSWORD"),
        "dbt": ("DBT_DB_USER", "DBT_DB_PASSWORD"),
        "streamlit": ("STREAMLIT_DB_USER", "STREAMLIT_DB_PASSWORD"),
    }
    conns: dict[str, psycopg.Connection] = {}
    try:
        # 1. connect + SELECT 1 for every role
        for name, (u, p) in roles.items():
            try:
                conns[name] = connect(u, p)
                one = conns[name].execute("SELECT 1").fetchone()[0]
                who = conns[name].execute("SELECT current_user").fetchone()[0]
                record(f"{name}: connect and SELECT 1 (as {who})", one == 1)
            except psycopg.Error as exc:
                record(f"{name}: connect and SELECT 1", False, short(exc))
        if len(conns) < len(roles):
            print("\nCannot continue: not every role could connect. Is the container running and healthy?")
            return 1

        version = conns["admin"].execute("SHOW server_version").fetchone()[0]
        print(f"server_version: {version}")

        # 2. schemas and owners
        owners = dict(conns["admin"].execute(
            "SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = ANY(%s)",
            ([raw, stg, ana],)).fetchall())
        expected_owner = {raw: os.environ["AIRBYTE_DB_USER"], stg: os.environ["DBT_DB_USER"],
                          ana: os.environ["DBT_DB_USER"]}
        for schema in (raw, stg, ana):
            record(f"schema {schema} exists, owner {expected_owner[schema]}",
                   owners.get(schema) == expected_owner[schema], f"owner={owners.get(schema)}")

        a, d, s = conns["airbyte"], conns["dbt"], conns["streamlit"]
        cols = sql.SQL("(id integer, note text)")

        # 3. Airbyte: writes raw only
        print("\n-- privilege checks (real operations, temporary tables) --")
        expect_ok(f"airbyte can CREATE TABLE in {raw}", a, sql.SQL("CREATE TABLE {} {}").format(qualified(raw), cols))
        expect_ok(f"airbyte can INSERT into {raw}", a, sql.SQL("INSERT INTO {} VALUES (1, 'x')").format(qualified(raw)))
        expect_denied(f"airbyte cannot CREATE TABLE in {stg}", a, sql.SQL("CREATE TABLE {} {}").format(qualified(stg), cols))
        expect_denied(f"airbyte cannot CREATE TABLE in {ana}", a, sql.SQL("CREATE TABLE {} {}").format(qualified(ana), cols))

        # 4. dbt: reads raw, writes staging and analytics
        expect_ok(f"dbt can SELECT from table created by airbyte in {raw}", d,
                  sql.SQL("SELECT * FROM {}").format(qualified(raw)))
        expect_denied(f"dbt cannot INSERT into {raw}", d, sql.SQL("INSERT INTO {} VALUES (2, 'y')").format(qualified(raw)))
        expect_denied(f"dbt cannot CREATE TABLE in {raw}", d,
                      sql.SQL("CREATE TABLE {} {}").format(sql.SQL("{}.{}").format(
                          sql.Identifier(raw), sql.Identifier(TEST_TABLE + "_dbt")), cols))
        expect_ok(f"dbt can CREATE TABLE in {stg}", d, sql.SQL("CREATE TABLE {} {}").format(qualified(stg), cols))
        expect_ok(f"dbt can CREATE TABLE in {ana}", d, sql.SQL("CREATE TABLE {} {}").format(qualified(ana), cols))
        expect_ok(f"dbt can CREATE VIEW in {ana}", d, sql.SQL("CREATE VIEW {} AS SELECT * FROM {}").format(
            sql.SQL("{}.{}").format(sql.Identifier(ana), sql.Identifier(TEST_TABLE + "_view")), qualified(ana)))

        # 5. Streamlit: read-only on analytics
        expect_ok(f"streamlit can SELECT from table created by dbt in {ana}", s,
                  sql.SQL("SELECT * FROM {}").format(qualified(ana)))
        expect_ok(f"streamlit can SELECT from view created by dbt in {ana}", s, sql.SQL("SELECT * FROM {}").format(
            sql.SQL("{}.{}").format(sql.Identifier(ana), sql.Identifier(TEST_TABLE + "_view"))))
        expect_denied(f"streamlit cannot INSERT into {ana}", s, sql.SQL("INSERT INTO {} VALUES (3, 'z')").format(qualified(ana)))
        expect_denied(f"streamlit cannot CREATE TABLE in {ana}", s, sql.SQL("CREATE TABLE {} {}").format(
            sql.SQL("{}.{}").format(sql.Identifier(ana), sql.Identifier(TEST_TABLE + "_st")), cols))
        expect_denied(f"streamlit cannot SELECT from {raw}", s, sql.SQL("SELECT * FROM {}").format(qualified(raw)))
        expect_denied(f"streamlit cannot SELECT from {stg}", s, sql.SQL("SELECT * FROM {}").format(qualified(stg)))
        ro = s.execute("SHOW default_transaction_read_only").fetchone()[0]
        record("streamlit role defaults to read-only transactions", ro == "on", f"value={ro}")

        # Second layer: even with read-only mode switched off, the grants must still refuse writes.
        try:
            rw = psycopg.connect(
                host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"]),
                dbname=os.environ["POSTGRES_DB"], user=os.environ["STREAMLIT_DB_USER"],
                password=os.environ["STREAMLIT_DB_PASSWORD"], connect_timeout=5, autocommit=True,
                options="-c default_transaction_read_only=off")
            conns["streamlit_rw"] = rw
            expect_denied(f"streamlit (read-only mode off) still cannot INSERT into {ana}", rw,
                          sql.SQL("INSERT INTO {} VALUES (4, 'w')").format(qualified(ana)))
            expect_denied(f"streamlit (read-only mode off) still cannot CREATE TABLE in {ana}", rw,
                          sql.SQL("CREATE TABLE {} {}").format(sql.SQL("{}.{}").format(
                              sql.Identifier(ana), sql.Identifier(TEST_TABLE + "_rw")), cols))
        except psycopg.Error as exc:
            record("streamlit grant-level write refusal check", False, short(exc))

        # 6. informational probe (not a pass/fail requirement)
        print("\n-- informational probe (Phase 4 relevance) --")
        try:
            a.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(raw)))
            print(f"INFO  airbyte 'CREATE SCHEMA IF NOT EXISTS {raw}': allowed")
        except psycopg.Error as exc:
            print(f"INFO  airbyte 'CREATE SCHEMA IF NOT EXISTS {raw}': refused ({short(exc)}). "
                  "Airbyte may run this statement; if its connection test fails on it, grant CREATE on "
                  "the database to the airbyte role (documented in documentation/postgres_setup.md).")
    finally:
        # cleanup by the owning roles; failures are reported, never hidden
        cleanup = [
            ("dbt", f"DROP VIEW IF EXISTS {ana}.{TEST_TABLE}_view"),
            ("dbt", f"DROP TABLE IF EXISTS {ana}.{TEST_TABLE}"),
            ("dbt", f"DROP TABLE IF EXISTS {stg}.{TEST_TABLE}"),
            ("airbyte", f"DROP TABLE IF EXISTS {raw}.{TEST_TABLE}"),
        ]
        print("\n-- cleanup --")
        for role, stmt in cleanup:
            conn = conns.get(role)
            if conn is None:
                print(f"SKIP  {stmt} (no connection)")
                continue
            try:
                conn.execute(stmt)
                print(f"OK    {stmt}")
            except psycopg.Error as exc:
                print(f"WARN  {stmt} failed: {short(exc)}")
        for conn in conns.values():
            conn.close()

    failed = [label for label, ok in results if not ok]
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL'}  ({len(results) - len(failed)}/{len(results)} checks passed)")
    for label in failed:
        print(f"  failed: {label}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
