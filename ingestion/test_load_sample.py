"""Offline tests for the Snowflake loader, using a fake connection (no Snowflake needed).

Run:  .\\.venv\\Scripts\\python.exe ingestion\\test_load_sample.py
"""

import contextlib
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import load_sample_to_snowflake as ld

failures = 0


def check(label: str, passed: bool, detail: str = "") -> None:
    global failures
    failures += not passed
    print(("PASS" if passed else "FAIL"), label, f"[{detail}]" if detail else "")


class FakeCursor:
    """Records every statement; answers the queries the loader makes."""

    def __init__(self, layout, comment, verify):
        self.log, self.layout, self.comment, self.verify_row = [], layout, comment, verify
        self._last, self.inserted = "", 0

    def execute(self, sql, params=None):
        self.log.append(sql.split(" (")[0][:48])
        self._last = sql
        if sql.startswith("DELETE") and ld.SQL_DELETE != sql:
            raise AssertionError("unexpected DELETE")

    def executemany(self, sql, rows):
        assert sql == ld.SQL_INSERT
        self.log.append("INSERT many")
        self.inserted = len(rows)

    def fetchall(self):
        return self.layout if "INFORMATION_SCHEMA.COLUMNS" in self._last else []

    def fetchone(self):
        if "INFORMATION_SCHEMA.TABLES" in self._last:
            return (self.comment,) if self.comment is not None else None
        if self._last == ld.SQL_VERIFY:
            return self.verify_row
        return None


class FakeConn:
    def __init__(self, cursor):
        self._c = cursor

    def cursor(self):
        return self._c


rows = ld.read_csv()
good = ld.csv_stats(rows)
check("CSV has the 744 approved rows", len(rows) == 744, str(good))
check("InvoiceNo kept as text with C/A prefixes", any(r[0].startswith("C") for r in rows) and any(r[0].startswith("A") for r in rows))
check("blank cells become None (not empty text)", any(r[2] is None for r in rows) and not any(v == "" for r in rows for v in r))
check("no row removed: 70 cancelled, 3 adjustments loaded", good[2] == 70 and sum(r[0].startswith("A") for r in rows) == 3)

# 1. first load: table absent -> create, then BEGIN, DELETE, INSERT, VERIFY, COMMIT
cur = FakeCursor([], None, good)
result = ld.load(FakeConn(cur), rows)
steps = [s.split()[0] for s in cur.log]
check("absent table: create then delete+insert+verify+commit in one transaction",
      "CREATE" in steps and steps.index("BEGIN") < steps.index("DELETE") < steps.index("INSERT") < steps.index("COMMIT")
      and "ROLLBACK" not in steps and cur.inserted == 744 and result == good, " > ".join(steps))

# 2. repeat run: table is ours -> no CREATE, same replace-all flow (no duplicates: DELETE first)
cur = FakeCursor(ld.EXPECTED_LAYOUT, ld.MARKER, good)
ld.load(FakeConn(cur), rows)
steps = [s.split()[0] for s in cur.log]
check("existing loader table: no CREATE, rows replaced (DELETE before INSERT)", "CREATE" not in steps and steps.index("DELETE") < steps.index("INSERT"), " > ".join(steps))

# 3. verification mismatch -> rollback, never commit
cur = FakeCursor(ld.EXPECTED_LAYOUT, ld.MARKER, (1488, 72, 70, 55, 290))
try:
    ld.load(FakeConn(cur), rows)
    check("count mismatch is rejected", False)
except ld.IngestError:
    steps = [s.split()[0] for s in cur.log]
    check("count mismatch: rolled back and not committed", "ROLLBACK" in steps and "COMMIT" not in steps, " > ".join(steps))

# 4. failure while inserting -> rollback
class Boom(FakeCursor):
    def executemany(self, sql, rows):
        raise RuntimeError("network error")

cur = Boom(ld.EXPECTED_LAYOUT, ld.MARKER, good)
try:
    ld.load(FakeConn(cur), rows)
    check("insert failure propagates", False)
except RuntimeError:
    steps = [s.split()[0] for s in cur.log]
    check("insert failure: rolled back and not committed", "ROLLBACK" in steps and "COMMIT" not in steps)

# 5. unexpected existing table (other columns, or no marker) -> refuse, run no DML/DDL
for label, layout, comment in (("different columns", [("X", "NUMBER")], ld.MARKER),
                               ("no loader marker", ld.EXPECTED_LAYOUT, "Created by Airbyte")):
    cur = FakeCursor(layout, comment, good)
    try:
        ld.load(FakeConn(cur), rows)
        check(f"unexpected table ({label}) refused", False)
    except ld.IngestError:
        bad = [s for s in cur.log if s.split()[0] in ("CREATE", "DELETE", "BEGIN", "INSERT", "COMMIT")]
        check(f"unexpected table ({label}): refused, nothing written", not bad, " > ".join(cur.log))

# 6. SQL text sanity
for name in ("SQL_CREATE", "SQL_DELETE", "SQL_INSERT", "SQL_VERIFY", "SQL_COLUMNS", "SQL_COMMENT"):
    sql = getattr(ld, name)
    check(f"{name} contains no CREATE OR REPLACE / DROP / TRUNCATE", not re.search(r"(?i)\b(replace|drop|truncate)\b", sql))
check("INSERT lists all 8 source columns with placeholders", ld.SQL_INSERT.count("%s") == 8)

# 7. dry run prints counts only and never opens a connection
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = ld.main(["--dry-run"])
out = buf.getvalue()
check("dry run succeeds offline", code == 0 and "No connection was made" in out, out.strip().splitlines()[0])

print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures})")
sys.exit(1 if failures else 0)
