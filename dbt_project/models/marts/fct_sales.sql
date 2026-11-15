{#-
    Valid sales lines only (approved Phase 2 rules): not cancelled, not a financial adjustment,
    positive quantity and unit price, invoice number and stock code present.
    Non-product charges stay in (gross valid-sales revenue) and are flagged with is_non_product,
    so merchandise rankings can exclude them. Revenue here is gross, before any returns.
-#}
select
    invoice_no,
    stock_code,
    description,
    quantity,
    unit_price,
    quantity * unit_price                       as line_revenue,
    invoice_ts,
    date_trunc('month', invoice_ts)::date       as invoice_month,
    customer_id,
    country,
    is_non_product
from {{ ref('stg_online_retail') }}
where not is_cancelled
  and not is_financial_adjustment
  and quantity > 0
  and unit_price > 0
  and invoice_no is not null
  and stock_code is not null
