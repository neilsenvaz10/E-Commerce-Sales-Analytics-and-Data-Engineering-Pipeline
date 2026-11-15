{#-
    Staging: one row per raw line, typed and flagged. No rows are removed here.
    Raw columns are TEXT (loaded by ingestion/load_sample_to_snowflake.py exactly as in the CSV,
    blanks as NULL), so every number and timestamp is converted explicitly below. A value that
    does not convert becomes NULL (try_*), and the dbt tests and validate_sample_results catch it.
    Column names are unquoted, matching the upper-case columns the loader creates (INVOICENO, ...).
-#}
with source as (

    select * from {{ source('raw', 'online_retail_sample') }}

),

typed as (

    select
        invoiceno                                              as invoice_no,        -- stays text (C... / A... prefixes)
        stockcode                                              as stock_code,
        nullif(trim(description), '')                          as description,
        try_to_number(quantity, 38, 0)                         as quantity,          -- whole number
        try_to_timestamp_ntz(invoicedate, 'YYYY-MM-DD HH24:MI:SS') as invoice_ts,
        try_to_decimal(unitprice, 18, 4)                       as unit_price,
        try_to_number(customerid, 38, 0)                       as customer_id,       -- NULL when missing
        country                                                as country
    from source

)

select
    *,
    -- cancelled invoices start with 'C' (approved Phase 2 rule)
    invoice_no like 'C%'                                       as is_cancelled,
    -- invoices starting with 'A' are "Adjust bad debt" entries, not customer sales
    invoice_no like 'A%'                                       as is_financial_adjustment,
    -- verified non-product charges (postage, fees, vouchers, manual entries, ...)
    (   stock_code in ('POST', 'DOT', 'M', 'm', 'C2', 'BANK CHARGES', 'AMAZONFEE', 'B', 'S', 'D', 'CRUK')
     or stock_code like 'gift_0001_%'
    )                                                          as is_non_product
from typed
