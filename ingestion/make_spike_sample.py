"""Build a small, representative test workbook for the Phase 4A Airbyte spike.

The original workbook is only READ. The sample is written to dataset/processed/
(Git-ignored) and keeps the original cell values and types, so InvoiceNo stays a
mix of numbers and text exactly as in the source. Nothing is cleaned or changed.

Selected rows (all taken unchanged from the original):
  - the first 500 rows
  - 100 cancelled invoices (InvoiceNo starting with 'C')
  - the 3 'A...' bad-debt adjustment rows
  - 50 rows with a missing Description and 100 with a missing CustomerID

Usage (project root, PowerShell):
    .\\.venv\\Scripts\\python.exe ingestion\\make_spike_sample.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dataset" / "original" / "Online Retail.xlsx"
TARGET = ROOT / "dataset" / "processed" / "online_retail_spike_sample.xlsx"


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: missing {SOURCE}", file=sys.stderr)
        return 1
    df = pd.read_excel(SOURCE, engine="openpyxl")
    inv = df["InvoiceNo"].astype(str)
    parts = [
        df.head(500),
        df[inv.str.startswith("C")].head(100),
        df[inv.str.startswith("A")],
        df[df["Description"].isna()].head(50),
        df[df["CustomerID"].isna()].iloc[1000:1100],
    ]
    sample = pd.concat(parts).drop_duplicates()
    # Keep original row order; do not modify any value.
    sample = sample.sort_index()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    sample.to_excel(TARGET, index=False, sheet_name="Online Retail", engine="openpyxl")

    check = pd.read_excel(TARGET, engine="openpyxl")
    types = check["InvoiceNo"].map(lambda v: type(v).__name__).value_counts().to_dict()
    print(f"sample rows: {len(sample)} (columns: {list(check.columns)})")
    print(f"InvoiceNo cell types in sample: {types}")
    print(f"written: {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
