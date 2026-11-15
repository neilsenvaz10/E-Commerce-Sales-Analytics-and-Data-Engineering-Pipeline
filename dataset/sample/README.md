# Sample data: UCI Online Retail (744 rows)

`online_retail_sample.csv` is a small subset of the UCI Online Retail dataset, published so that Airbyte Cloud can read it from a public URL.

**Source and licence**

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33

The dataset is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). Original: https://archive.ics.uci.edu/dataset/352/online+retail

**Changes made (as CC BY 4.0 requires us to state)**

- Only 744 of the 541,909 original rows are included, each at most once, in the original order. They are chosen by fixed rules (no randomness) in `ingestion/make_sample_csv.py`: 585 valid sales (45 in each of the 13 months, Dec 2010 to Dec 2011), 12 valid non-product charges, 70 cancelled invoices (`C...`), the 3 `A...` bad-debt rows, 40 rows with a missing description, 24 negative-quantity stock adjustments and 10 zero-price rows with a description.
- Converted from Excel to CSV by the same script. Values are unchanged. `InvoiceNo` is text, `CustomerID` is written as a whole number, and dates are written as `YYYY-MM-DD HH:MM:SS`. The script checks the row count, the month coverage and that no row repeats. Re-running it on the original workbook gives the same file.

This sample is not endorsed by the dataset's creator or by UCI. It contains no personal data (customer IDs are anonymous numbers). Results computed from it describe the sample, not the whole dataset.
