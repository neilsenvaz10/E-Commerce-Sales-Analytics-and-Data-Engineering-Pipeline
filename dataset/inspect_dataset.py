"""Read-only inspection of the UCI Online Retail workbook (Phase 2).

Inspection only: the workbook is opened read-only and nothing is cleaned,
modified, or written back. Output goes to the console and to a text report.

Usage (from the project root, PowerShell):
    .\\.venv\\Scripts\\python.exe dataset\\inspect_dataset.py
"""

from __future__ import annotations

import hashlib
import sys
from io import StringIO
from pathlib import Path

import openpyxl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = PROJECT_ROOT / "dataset" / "original" / "Online Retail.xlsx"
REPORT = PROJECT_ROOT / "documentation" / "dataset_inspection_results.txt"

EXPECTED_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def section(out: StringIO, title: str) -> None:
    out.write(f"\n=== {title} ===\n")


def main() -> int:
    if not WORKBOOK.exists():
        print(f"ERROR: workbook not found: {WORKBOOK}", file=sys.stderr)
        return 1

    out = StringIO()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)

    section(out, "FILE")
    out.write(f"path: {WORKBOOK.relative_to(PROJECT_ROOT)}\n")
    out.write(f"size_bytes: {WORKBOOK.stat().st_size}\n")
    out.write(f"sha256: {sha256_of(WORKBOOK)}\n")

    section(out, "SHEETS")
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    for ws in wb.worksheets:
        out.write(f"sheet: {ws.title!r}, dimensions: {ws.calculate_dimension()}\n")
    wb.close()

    df = pd.read_excel(WORKBOOK, sheet_name=0, engine="openpyxl")

    section(out, "SHAPE AND SCHEMA")
    out.write(f"rows: {len(df)}\ncolumns: {df.shape[1]}\n")
    out.write(f"column names: {list(df.columns)}\n")
    out.write(f"matches expected columns: {list(df.columns) == EXPECTED_COLUMNS}\n")
    out.write("dtypes (as read by pandas):\n")
    out.write(df.dtypes.to_string() + "\n")

    section(out, "FIRST 5 RECORDS")
    out.write(df.head(5).to_string() + "\n")
    section(out, "LAST 5 RECORDS")
    out.write(df.tail(5).to_string() + "\n")

    section(out, "MISSING VALUES")
    missing = df.isna().sum()
    out.write(pd.DataFrame({"missing": missing, "pct": (missing / len(df) * 100).round(2)}).to_string() + "\n")

    section(out, "EXACT DUPLICATE ROWS")
    dup_extra = int(df.duplicated(keep="first").sum())
    dup_all = int(df.duplicated(keep=False).sum())
    out.write(f"extra copies (rows removable if keep first): {dup_extra}\n")
    out.write(f"all rows involved in a duplicate group: {dup_all}\n")

    section(out, "INVOICE NUMBERS")
    inv = df["InvoiceNo"].astype(str)
    cancelled = inv.str.startswith("C")
    out.write(f"InvoiceNo python types: {df['InvoiceNo'].map(type).value_counts().to_dict()}\n")
    out.write(f"distinct invoices (all): {inv.nunique()}\n")
    out.write(f"cancelled invoice rows (InvoiceNo starts with 'C'): {int(cancelled.sum())}\n")
    out.write(f"distinct cancelled invoices: {inv[cancelled].nunique()}\n")
    other_prefix = inv[~inv.str.fullmatch(r"\d{6}") & ~cancelled]
    out.write(f"non-cancelled invoices not matching 6 digits: {len(other_prefix)} "
              f"(examples: {other_prefix.unique()[:5].tolist()})\n")

    section(out, "QUANTITY")
    qty = pd.to_numeric(df["Quantity"], errors="coerce")
    out.write(f"non-numeric quantity: {int(qty.isna().sum() - df['Quantity'].isna().sum())}\n")
    out.write(f"negative quantity rows: {int((qty < 0).sum())}\n")
    out.write(f"zero quantity rows: {int((qty == 0).sum())}\n")
    out.write(f"negative quantity on NON-cancelled invoices: {int(((qty < 0) & ~cancelled).sum())}\n")
    out.write(f"positive quantity on cancelled invoices: {int(((qty > 0) & cancelled).sum())}\n")

    section(out, "UNIT PRICE")
    price = pd.to_numeric(df["UnitPrice"], errors="coerce")
    out.write(f"zero price rows: {int((price == 0).sum())}\n")
    out.write(f"negative price rows: {int((price < 0).sum())}\n")

    section(out, "INVOICE DATE")
    dates = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    out.write(f"missing/unparseable dates: {int(dates.isna().sum())}\n")
    out.write(f"min date: {dates.min()}\nmax date: {dates.max()}\n")
    out.write("rows per month:\n" + dates.dt.to_period("M").value_counts().sort_index().to_string() + "\n")

    section(out, "DISTINCT COUNTS")
    out.write(f"distinct customers (non-null): {df['CustomerID'].nunique()}\n")
    out.write(f"distinct stock codes: {df['StockCode'].astype(str).nunique()}\n")
    out.write(f"distinct countries: {df['Country'].nunique()}\n")
    out.write(f"distinct descriptions: {df['Description'].nunique()}\n")

    section(out, "COUNTRY DISTRIBUTION (rows)")
    out.write(df["Country"].value_counts().to_string() + "\n")

    section(out, "STOCK CODES THAT LOOK NON-PRODUCT (no digit)")
    sc = df["StockCode"].astype(str)
    nonprod = sc[~sc.str.contains(r"\d")]
    out.write(nonprod.value_counts().to_string() + "\n")

    section(out, "DESCRIPTIONS")
    out.write(f"missing descriptions: {int(df['Description'].isna().sum())}\n")
    out.write("stock codes mapped to more than one distinct description: "
              f"{int((df.groupby(df['StockCode'].astype(str))['Description'].nunique() > 1).sum())}\n")

    section(out, "DESCRIPTIVE STATISTICS (numeric)")
    out.write(df[["Quantity", "UnitPrice", "CustomerID"]].describe().to_string() + "\n")

    section(out, "PRELIMINARY RULE IMPACT (counts only, no data changed)")
    valid = (~cancelled) & (qty > 0) & (price > 0) & df["InvoiceNo"].notna() & df["StockCode"].notna()
    out.write(f"rows passing provisional valid-sales rule: {int(valid.sum())}\n")
    out.write(f"rows failing it: {int((~valid).sum())}\n")
    vs = df[valid]
    out.write(f"valid sales: distinct invoices: {vs['InvoiceNo'].astype(str).nunique()}\n")
    out.write(f"valid sales: distinct customers: {vs['CustomerID'].nunique()}\n")
    out.write(f"valid sales: rows with missing CustomerID: {int(vs['CustomerID'].isna().sum())}\n")
    out.write(f"valid sales: gross revenue (Quantity*UnitPrice): {(qty[valid] * price[valid]).sum():.2f}\n")

    section(out, "EXACT DUPLICATES: IMPACT ON PROVISIONAL VALID SALES")
    dup_flag = df.duplicated(keep="first")
    dup_valid = valid & dup_flag
    dup_rev = (qty[dup_valid] * price[dup_valid]).sum()
    total_rev = (qty[valid] * price[valid]).sum()
    out.write(f"extra duplicate copies passing valid rule: {int(dup_valid.sum())}\n")
    out.write(f"revenue carried by those copies: {dup_rev:.2f} ({dup_rev / total_rev * 100:.2f}% of valid revenue)\n")
    out.write(f"extra duplicate copies with missing CustomerID: {int(df.loc[dup_flag, 'CustomerID'].isna().sum())}\n")

    section(out, "NON-STANDARD STOCK CODES IN VALID SALES (evidence for classification)")
    code = df["StockCode"].astype(str)
    nonstd = valid & ~code.str.fullmatch(r"\d{5}[A-Za-z]{0,2}")
    rows = []
    for sc, grp in df[nonstd].groupby(code[nonstd]):
        rev = (qty[grp.index] * price[grp.index]).sum()
        descs = "; ".join(sorted(set(grp["Description"].dropna().astype(str)))[:3])
        rows.append((sc, len(grp), round(rev, 2), descs))
    out.write(pd.DataFrame(rows, columns=["StockCode", "rows", "revenue", "descriptions"])
              .sort_values("rows", ascending=False).to_string(index=False) + "\n")
    out.write(f"total non-standard rows: {int(nonstd.sum())}, "
              f"revenue: {(qty[nonstd] * price[nonstd]).sum():.2f}\n")

    section(out, "SPECIAL CODES ACROSS ALL ROWS (D, CRUK)")
    for sc in ("D", "CRUK"):
        sub = df[code == sc]
        out.write(f"{sc}: rows={len(sub)}, descriptions={sorted(set(sub['Description'].dropna().astype(str)))}, "
                  f"negative quantity rows={int((qty[sub.index] < 0).sum())}\n")

    text = out.getvalue()
    print(text)
    REPORT.write_text(text, encoding="utf-8")
    print(f"\nReport written to {REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
