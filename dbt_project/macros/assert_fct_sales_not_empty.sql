{#- Post-run validation used by the Airflow DAG:  dbt run-operation assert_fct_sales_not_empty
    Fails (non-zero exit) if fct_sales is empty or has more rows than the raw table. -#}
{% macro assert_fct_sales_not_empty() %}
    {% if execute %}
        {% set check_sql %}
            select
                (select count(*) from {{ ref('fct_sales') }})                       as fct_rows,
                (select count(*) from {{ source('raw', 'online_retail_sample') }})  as raw_rows
        {% endset %}
        {% set result = run_query(check_sql) %}
        {% set fct_rows = result.columns[0].values()[0] %}
        {% set raw_rows = result.columns[1].values()[0] %}
        {% if fct_rows == 0 %}
            {{ exceptions.raise_compiler_error('Validation failed: fct_sales is empty (raw rows: ' ~ raw_rows ~ ')') }}
        {% elif fct_rows > raw_rows %}
            {{ exceptions.raise_compiler_error('Validation failed: fct_sales has more rows (' ~ fct_rows ~ ') than raw (' ~ raw_rows ~ ')') }}
        {% endif %}
        {{ log('Validation OK: fct_sales rows = ' ~ fct_rows ~ ', raw rows = ' ~ raw_rows, info=True) }}
    {% endif %}
{% endmacro %}
