# Dataset Description (Phase 2)

All figures below come from running [`dataset/inspect_dataset.py`](../dataset/inspect_dataset.py) against the real workbook. The full output is in [`dataset_inspection_results.txt`](dataset_inspection_results.txt). Nothing in the workbook was modified or cleaned.

## 1. Source

| Item | Value |
|---|---|
| Dataset | UCI Online Retail |
| Page | https://archive.ics.uci.edu/dataset/352/online+retail |
| Download | https://archive.ics.uci.edu/static/public/352/online+retail.zip |
| ZIP size | 23,715,478 bytes |
| ZIP SHA-256 | `F5385CBB54BBEBF7196389109C6B0621FAAB0C304E3702548165E71C84AEDE8B` |
| ZIP contents | one file, `Online Retail.xlsx` |
| Workbook location | `dataset/original/Online Retail.xlsx` (excluded from Git) |
| Workbook size | 23,715,344 bytes |
| Workbook SHA-256 | `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d` |

The workbook hash was re-checked after the inspection runs and is unchanged, so the original file was not modified. Anyone who downloads the same ZIP can compare their hash to confirm they have the same data.

## 2. Structure

- One sheet: `Online Retail`, range `A1:H541910`.
- **541,909 data rows, 8 columns.** The column names match the expected schema exactly.

| Column | Type as read by pandas | Notes |
|---|---|---|
| InvoiceNo | object (mixed) | 532,618 cells are Excel numbers, 9,291 are text (`C…` cancellations and 3 `A…` invoices) |
| StockCode | object | Alphanumeric, e.g. `85123A` |
| Description | object | Free text |
| Quantity | int64 | |
| InvoiceDate | datetime64 | Parsed without errors |
| UnitPrice | float64 | |
| CustomerID | float64 | Float because of missing values; contains whole numbers |
| Country | string | |

Date range: **2010-12-01 08:26 to 2011-12-09 12:50**. December 2011 holds only a partial month (25,525 rows, ending 9 Dec), which matters for monthly trend charts.

First record: invoice 536365, WHITE HANGING HEART T-LIGHT HOLDER, United Kingdom. Last record: invoice 581587, BAKING SET 9 PIECE RETROSPOT, France.

## 3. Verified Findings

| Check | Result |
|---|---|
| Missing `Description` | 1,454 rows (0.27%) |
| Missing `CustomerID` | 135,080 rows (24.93%) |
| Missing in other columns | 0 |
| Exact duplicate rows | 5,268 extra copies (10,147 rows belong to a duplicate group) |
| Distinct invoices (all) | 25,900 |
| Cancelled invoice rows (`InvoiceNo` starts with `C`) | 9,288 rows, 3,836 distinct invoices |
| Positive quantity on a cancelled invoice | 0 |
| Negative quantity rows | 10,624 |
| Negative quantity on non-cancelled invoices | 1,336 |
| Zero quantity rows | 0 |
| Zero unit price rows | 2,515 |
| Negative unit price rows | 2 |
| Invalid or missing invoice dates | 0 |
| Distinct customers (non-null) | 4,372 |
| Distinct stock codes | 4,070 |
| Distinct countries | 38 |
| Stock codes with more than one description | 650 |

United Kingdom has 495,478 of the 541,909 rows (about 91%). The next largest are Germany (9,495), France (8,557) and EIRE (8,196). The country list includes `Unspecified` (446 rows) and `European Community` (61 rows).

Numeric ranges: Quantity runs from -80,995 to 80,995 and UnitPrice from -11,062.06 to 38,970.00, so extreme outliers exist.

### Specific observations

- **Non-cancelled negative quantities (1,336 rows):** all have a unit price of 0, and 862 of them have no description. They look like stock adjustments, not returns.
- **Zero-price rows (2,515):** all 1,454 missing descriptions fall in this group, and 2,475 of the 2,515 also have no `CustomerID`.
- **`A`-prefixed invoices (3 rows):** `A563185`, `A563186`, `A563187` are all "Adjust bad debt" (stock code `B`). One is +11,062.06 and two are -11,062.06. They explain the two negative prices.
- **Cancelled rows without a customer:** 383 of the 9,288.
- **Non-product stock codes:** `POST` (1,256), `DOT` (710), `M` (571), `D` (77), `S` (63), `BANK CHARGES` (37), `AMAZONFEE` (34), `CRUK` (16), `DCGSSGIRL` (13), `DCGSSBOY` (11), `PADS` (4), `B` (3), `m` (1). These look like postage, fees, discounts and manual entries, not products. This is an interpretation of the codes, not something the dataset states.

## 4. Provisional Rule Impact (counts only, no data changed)

Applying the Phase 1 provisional valid-sales rule (not cancelled, quantity > 0, price > 0, identifiers present) to the real data gives:

| Measure | Value |
|---|---|
| Rows passing | 530,104 |
| Rows failing | 11,805 |
| Distinct valid invoices | 19,960 |
| Distinct customers on valid sales | 4,338 |
| Valid-sales rows with missing `CustomerID` | 132,220 |
| Gross valid-sales revenue (Quantity × UnitPrice) | 10,666,684.54 |

These are the **provisional** counts from the inspection script, kept unchanged as historical evidence. They are not official KPI results. The refined rule (Decision 3 in Section 6) lowers revenue to 10,655,622.48 and valid invoices to 19,959. The official figures come from the dbt models in Phase 5, and they may differ once the recommendations below are decided.

## 5. Preliminary Cleaning Recommendations

These are recommendations for Phase 5. **No cleaning has been done.**

1. **Keep the raw layer untouched.** Load all 541,909 rows as they are and apply every rule in dbt.
2. **Cancellations:** identify them with `InvoiceNo` starting with `C`, and exclude them from the main sales measure. The data confirms none have a positive quantity.
3. **Negative quantities on non-cancelled invoices:** exclude them. They are zero-price adjustments, not sales.
4. **Zero and negative prices:** exclude them from sales. This removes two of the three `A…` bad-debt rows (the negative ones). **Correction to an earlier remark:** the third, `A563185` (stock code `B`, +11,062.06), has a positive price and still passes the valid-sales rule; see Section 6.
5. **Missing `CustomerID`:** keep the rows for revenue (about 25% of rows) and exclude nulls from the unique-customer count, as agreed in Phase 1.
6. **Exact duplicates:** decided; see Decision 1 in Section 6.
7. **Non-product stock codes:** decided; see Decision 2 in Section 6.
8. **Missing descriptions:** all are zero-price rows, so the valid-sales rule already removes them.
9. **Multiple descriptions per stock code (650 codes):** identify products by `StockCode` and pick one display description per code in `dim_products`.
10. **Mixed `InvoiceNo` types:** cast `InvoiceNo` to string in staging. Plan the ingestion step with this in mind, since a CSV conversion would make the column text.
11. **`CustomerID` float:** cast to an integer or string identifier in staging.
12. **Partial last month:** December 2011 is incomplete; see Section 7.
13. **Outliers:** the quantity range is exactly -80,995 to +80,995. Whether these two extremes are a matching order and cancellation was not checked in Phase 2. Examine the extreme quantities and prices again in Phase 5.

## 6. Recorded Data-Cleaning Decisions (provisional, for Phase 5)

Decided by the team after reviewing the Phase 2 report. They are provisional until implemented and tested in dbt. The figures come from `dataset_inspection_results.txt`.

### Decision 1: Exact duplicates

- **Raw layer:** keep all 541,909 rows exactly as ingested.
- **Downstream:** do **not** automatically remove the 5,268 extra copies of exact duplicate rows. The dataset has no unique line-item identifier, so an identical row can be a genuine repeat purchase or a data-entry duplicate, and nothing in the data separates the two.
- **Potential impact:** 5,226 of the extra copies pass the provisional valid-sales rule and carry **24,573.74** of revenue, which is **0.23%** of the 10,666,684.54 provisional valid revenue. If they turn out to be true duplicates, revenue is overstated by up to that amount. A further 43 extra copies have no `CustomerID`.
- **Limitation:** the decision accepts a small possible overstatement in return for not deleting legitimate sales. Transaction counts are not affected, because they use distinct invoice numbers. Revenue and quantity totals can be.
- **Required follow-up:** state this limitation next to the revenue KPI in the final report. Any later de-duplication must be a documented, reversible dbt model, never a change to the raw layer.

### Decision 2: Non-product stock codes

- **Raw layer:** keep every row.
- **Classification:** add a flag in staging (for example `is_non_product`) driven by an explicit, version-controlled list of stock codes. A code goes on the list only if its description in the data supports it. Codes with no clear evidence are **not** classified; they stay as merchandise and go to a review list. No product categories are invented.
- **Overall gross valid-sales revenue:** keep valid positive non-product charges (postage, fees and so on), **except the financial adjustment in Decision 3**. **Metric definition:** gross valid-sales revenue is the sum of `Quantity × UnitPrice` over non-cancelled customer-sale rows with quantity > 0 and unit price > 0, including valid non-product charges, before any return deduction, and excluding financial adjustments (Decision 3). It is not net revenue and not merchandise-only revenue.
- **Top-selling merchandise products:** exclude the verified non-product codes. This ranking must be labelled as merchandise only.

**Verified non-product codes** (description evidence from the data; rows and revenue are those passing the provisional valid-sales rule):

| StockCode | Description in data | Rows | Revenue |
|---|---|---|---|
| `POST` | POSTAGE | 1,126 | 78,101.88 |
| `DOT` | DOTCOM POSTAGE | 706 | 206,248.77 |
| `M` | Manual | 321 | 78,110.27 |
| `m` | Manual | 1 | 2.55 |
| `C2` | CARRIAGE | 141 | 7,051.00 |
| `BANK CHARGES` | Bank Charges | 12 | 165.00 |
| `AMAZONFEE` | AMAZON FEE | 2 | 13,761.09 |
| `B` | Adjust bad debt (financial adjustment, see Decision 3) | 1 | 11,062.06 |
| `S` | SAMPLES | 2 | 63.05 |
| `gift_0001_10`, `_20`, `_30`, `_40`, `_50` | Dotcomgiftshop Gift Voucher (£10 to £50) | 31 | 685.81 |
| **Total** | | **2,343** | **395,251.48** |

That is about 3.7% of provisional valid revenue. Merchandise revenue excluding these codes would be about 10,271,433.06. The official figure comes from dbt in Phase 5.

`D` (Discount, 77 rows) and `CRUK` (CRUK Commission, 16 rows) are also non-product by their descriptions, but every row is a negative quantity on a cancelled invoice, so they never enter valid sales. Include them in the list for completeness.

**Not classified (kept as merchandise, flagged for review):** `DCGSSGIRL` (GIRLS PARTY BAG), `DCGSSBOY` (BOYS PARTY BAG), `DCGS0003`, `DCGS0004`, `DCGS0069`, `DCGS0070`, `DCGS0076`, and `PADS` (PADS TO MATCH ALL CUSHIONS, with a unit price of 0.001 on some rows). Their descriptions read like goods. Together they pass 36 valid-sales rows worth 398.45. The inspection did not confirm what they are, so the team should decide in Phase 5.

### Decision 3: Financial adjustment `A563185` (supersedes the earlier open point)

- **Raw layer:** keep invoice `A563185` exactly as ingested (stock code `B`, "Adjust bad debt", quantity 1, unit price +11,062.06, dated 2011-08-12 14:50, no `CustomerID`, United Kingdom).
- **Classification:** treat its positive amount as a **financial adjustment**, not a valid customer sale. It is one of three `A…` bad-debt rows; the other two (`A563186`, `A563187`, each -11,062.06) are already excluded by the price rule.
- **Effect:** exclude it from the finalized gross valid-sales revenue and from merchandise product rankings. Implement it as an explicit classification (for example a `transaction_type` of `financial_adjustment`), not as a hidden filter.
- **Refined figures** (one-off check against the real workbook; the official values come from dbt in Phase 5):

| Measure | Provisional rule | Refined rule |
|---|---|---|
| Valid-sales rows | 530,104 | 530,103 |
| Distinct valid invoices | 19,960 | 19,959 |
| Distinct valid customers | 4,338 | 4,338 (the row has no `CustomerID`) |
| Gross valid-sales revenue | 10,666,684.54 | 10,655,622.48 |

- **Evidence kept as is:** `dataset_inspection_results.txt` still reports the provisional figures. It is historical inspection evidence and is deliberately not edited. The refined rule is documented here, separately.
- The remaining valid non-product charges (all verified codes except `B`) total 384,189.42 and stay in gross valid-sales revenue.

## 7. Partial Month: December 2011

The data ends on **2011-12-09 12:50**, so December 2011 covers only the first nine days (25,525 rows). December 2010 is covered from 2010-12-01, so a December 2011 versus December 2010 comparison is not like-for-like.

Decisions:
- **Highest-revenue month:** compare **complete calendar months only**, which are December 2010 to November 2011 (12 months). December 2011 is excluded from this comparison. The dashboard must state this.
- **Monthly revenue trend:** show **all 13 available months**, including December 2011, and clearly label December 2011 as a **partial month** (for example "Dec 2011 (partial, to 9 Dec)").
- Do not read the lower December 2011 figure as a decline in sales.
- December 2010 is treated as complete: the data starts on 2010-12-01.

Check against the real data (refined rule from Decision 3, one-off check): the highest complete month is **2011-11 with 1,509,496.33**. Including the partial month does not change the answer, because December 2011 (638,792.68 to 9 Dec) is lower. The rule is still applied so the answer cannot change with data updates. Official values come from dbt in Phase 5.

## 8. Reproducing the Inspection

From the project root in PowerShell, using the project virtual environment (Python 3.12, pandas 3.1.1, openpyxl 3.1.5):

```powershell
.\.venv\Scripts\python.exe dataset\inspect_dataset.py
```

Two consecutive runs produced byte-identical reports (same SHA-256), so the results are reproducible.

## 9. Limitations

- The dataset has no product categories, no unique transaction ID, and limited customer detail.
- About 25% of rows have no customer, so customer-level analysis covers 4,372 customers only.
- Findings about what the odd rows "look like" (adjustments, fees) are interpretations to confirm in Phase 5.
