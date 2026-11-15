-- Returns rows that break the revenue rule (the test fails if any row comes back):
-- line_revenue must be positive and equal quantity x unit_price.
select invoice_no, stock_code, quantity, unit_price, line_revenue
from {{ ref('fct_sales') }}
where line_revenue <= 0
   or abs(line_revenue - quantity * unit_price) > 0.0001
