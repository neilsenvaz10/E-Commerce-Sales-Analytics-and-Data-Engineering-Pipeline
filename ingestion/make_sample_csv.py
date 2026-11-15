"""Build the 744-row UCI sample CSV for Airbyte Cloud, reproducibly, from the original workbook.

Airbyte Cloud cannot read local files, so the sample is published as a CSV in the repository
(dataset/sample/) and read from its public GitHub URL.

Selection is deterministic (no randomness) and uses only genuine, unmodified source rows, each
at most once, with no exact-duplicate content, kept in the original order:
  * 585 valid sales: 45 per month for all 13 months (Dec 2010 .. Dec 2011), as 3 blocks of 15
    consecutive rows per month so invoices keep their line items together
  *  12 valid non-product charges (POST, DOT, M, ... ) spread over the date range
  *  70 cancelled invoices ('C...')
  *   3 bad-debt adjustment rows ('A...')
  *  40 rows with a missing Description (zero price)
  *  24 negative quantities on non-cancelled invoices (stock adjustments)
  *  10 zero-price rows that still have a description
"Valid sale" = not cancelled, not an 'A...' adjustment, quantity > 0, unit price > 0,
invoice number and stock code present.

CSV text form of each cell: InvoiceNo as text, CustomerID as a whole number, InvoiceDate as
'YYYY-MM-DD HH:MM:SS', blanks stay blank. The script re-reads the CSV and verifies it.

Usage (project root, PowerShell; needs dataset/original/Online Retail.xlsx, takes about a minute):
    .\\.venv\\Scripts\\python.exe ingestion\\make_sample_csv.py
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_XLSX = ROOT / "dataset" / "original" / "Online Retail.xlsx"
TARGET_CSV = ROOT / "dataset" / "sample" / "online_retail_sample.csv"
HEADER = ["InvoiceNo", "StockCode", "Description", "Quantity",
          "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
EXPECTED_ROWS = 744
BLOCKS_PER_MONTH, BLOCK_SIZE = 3, 15
NON_PRODUCT = {"POST", "DOT", "M", "m", "C2", "BANK CHARGES", "AMAZONFEE", "B", "S",
               "D", "CRUK"}


def fmt(column: str, value) -> str:
    """Text form of one workbook cell, exactly as it should appear in the CSV."""
    if value is None:
        return ""
    if column == "InvoiceDate":
        return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else str(value)
    if column == "CustomerID" and isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return repr(value)
    return str(value)


def read_original() -> list[list]:
    wb = openpyxl.load_workbook(ORIGINAL_XLSX, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    wb.close()
    if list(rows[0]) != HEADER:
        raise SystemExit(f"unexpected header: {rows[0]}")
    return [list(r[:8]) for r in rows[1:]]


class Picker:
    """Collects row positions without repeating a row or its exact content."""

    def __init__(self, rows: list[list]):
        self.rows, self.taken, self.seen = rows, set(), set()

    def add(self, i: int) -> bool:
        key = tuple(fmt(c, v) for c, v in zip(HEADER, self.rows[i]))
        if i in self.taken or key in self.seen:
            return False
        self.taken.add(i)
        self.seen.add(key)
        return True

    def evenly(self, candidates: list[int], n: int) -> None:
        """Take n rows spread evenly over candidates; skip ones already taken, then move on."""
        pool = [i for i in candidates if i not in self.taken]
        if len(pool) < n:
            raise SystemExit(f"only {len(pool)} candidates for {n} rows")
        want, step, pos = n, len(pool) / n, 0.0
        used = 0
        while used < n:
            start = int(pos)
            while start < len(pool) and not self.add(pool[start]):
                start += 1
            if start >= len(pool):   # ran past the end: fill from the front
                start = next(j for j in range(len(pool)) if self.add(pool[j]))
            used += 1
            pos += step


def select(rows: list[list]) -> list[int]:
    n = len(rows)
    inv = [str(r[0]) for r in rows]
    qty = [r[3] for r in rows]
    price = [r[5] for r in rows]
    valid = [i for i in range(n)
             if not inv[i].startswith(("C", "A")) and qty[i] is not None and qty[i] > 0
             and price[i] is not None and price[i] > 0 and rows[i][1] is not None]
    pick = Picker(rows)

    by_month: dict[str, list[int]] = {}
    for i in valid:
        by_month.setdefault(rows[i][4].strftime("%Y-%m"), []).append(i)
    for month in sorted(by_month):
        idx = by_month[month]
        for k in range(BLOCKS_PER_MONTH):
            start = int(len(idx) * (0.15 + 0.35 * k))
            added = 0
            for i in idx[start:]:
                if added == BLOCK_SIZE:
                    break
                added += pick.add(i)

    pick.evenly([i for i in valid if str(rows[i][1]) in NON_PRODUCT], 12)
    pick.evenly([i for i in range(n) if inv[i].startswith("C")], 70)
    pick.evenly([i for i in range(n) if inv[i].startswith("A")], 3)
    pick.evenly([i for i in range(n) if rows[i][2] is None], 40)
    pick.evenly([i for i in range(n) if qty[i] is not None and qty[i] < 0 and not inv[i].startswith("C")], 24)
    pick.evenly([i for i in range(n) if price[i] == 0 and rows[i][2] is not None
                 and qty[i] is not None and qty[i] > 0], 10)
    return sorted(pick.taken)


def main() -> int:
    if not ORIGINAL_XLSX.exists():
        print(f"ERROR: missing {ORIGINAL_XLSX}", file=sys.stderr)
        return 1
    rows = read_original()
    chosen = select(rows)
    text_rows = [[fmt(c, v) for c, v in zip(HEADER, rows[i])] for i in chosen]

    TARGET_CSV.parent.mkdir(parents=True, exist_ok=True)
    with TARGET_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(text_rows)

    # ---- verification ----
    with TARGET_CSV.open(newline="", encoding="utf-8") as handle:
        back = list(csv.reader(handle))
    ok = True

    def check(label: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and passed
        print(f"{'PASS' if passed else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))

    body = back[1:]
    check("header matches", back[0] == HEADER)
    check(f"exactly {EXPECTED_ROWS} data rows", len(body) == EXPECTED_ROWS, f"found {len(body)}")
    check("every CSV row equals the original workbook cell text", body == text_rows)
    check("no row repeated (positions and content)", len(set(chosen)) == len(chosen) == len({tuple(r) for r in body}))

    def is_valid(r):
        q, p = float(r[3] or 0), float(r[5] or 0)
        return not r[0].startswith(("C", "A")) and q > 0 and p > 0 and r[0] != "" and r[1] != ""

    valid = [r for r in body if is_valid(r)]
    revenue_by_month: dict[str, float] = {}
    for r in valid:
        revenue_by_month[r[4][:7]] = revenue_by_month.get(r[4][:7], 0.0) + float(r[3]) * float(r[5])
    check("valid sales in at least 6 different months", len(revenue_by_month) >= 6, f"{len(revenue_by_month)} months")
    check("cancellations present", any(r[0].startswith("C") for r in body))
    check("adjustment (A...) rows present", any(r[0].startswith("A") for r in body))
    check("missing Description present", any(r[2] == "" for r in body))
    check("missing CustomerID present", any(r[6] == "" for r in body))

    refined = [r for r in valid]   # is_valid already excludes C and A invoices
    orders = {r[0] for r in refined}
    total = sum(float(r[3]) * float(r[5]) for r in refined)
    merch = [r for r in refined if not (r[1] in NON_PRODUCT or r[1].startswith("gift_0001_"))]
    print("\n--- expected results for this sample (same rules as dbt fct_sales) ---")
    print(f"fct_sales rows (valid sales lines): {len(refined)}")
    print(f"orders (distinct invoices): {len(orders)}")
    print(f"total revenue: {total:.2f}")
    print(f"non-product lines in valid sales: {len(refined) - len(merch)}")
    print("monthly revenue:")
    for month in sorted(revenue_by_month):
        print(f"  {month}  {revenue_by_month[month]:.2f}")
    print(f"sample composition: cancelled={sum(r[0].startswith('C') for r in body)}, "
          f"A-invoices={sum(r[0].startswith('A') for r in body)}, "
          f"missing description={sum(r[2] == '' for r in body)}, "
          f"missing customer={sum(r[6] == '' for r in body)}, "
          f"countries={len({r[7] for r in body})}, "
          f"date range={min(r[4] for r in body)} .. {max(r[4] for r in body)}")
    print(f"written: {TARGET_CSV.relative_to(ROOT)} ({TARGET_CSV.stat().st_size} bytes)")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
