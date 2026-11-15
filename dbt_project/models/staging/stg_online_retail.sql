{#-
    Staging: one row per raw line, typed and flagged. No rows are removed here.
    Column names below are unquoted, so they match Airbyte's upper-case Snowflake columns
    (INVOICENO, ...). UNVERIFIED until the first real sync: if Airbyte created quoted
    mixed-case columns ("InvoiceNo"), quote the names here instead.
    Every value goes through to_varchar() first, so this works whether Airbyte typed the
    columns as text or as numbers/timestamps.
-#}
with source as (

    select * from {{ source('raw', 'online_retail_sample') }}

),

typed as (

    select
        to_varchar(invoiceno)                                  as invoice_no,
        to_varchar(stockcode)                                  as stock_code,
        nullif(trim(to_varchar(description)), '')              as description,
        try_to_number(to_varchar(quantity))                    as quantity,
        try_to_timestamp_ntz(to_varchar(invoicedate))          as invoice_ts,
        try_to_decimal(to_varchar(unitprice), 18, 4)           as unit_price,
        try_to_number(to_varchar(customerid))                  as customer_id,
        to_varchar(country)                                    as country
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
