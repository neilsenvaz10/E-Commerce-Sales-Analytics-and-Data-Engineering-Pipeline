{#- Post-run validation used by the Airflow DAG:  dbt run-operation validate_sample_results
    Checks the finished pipeline against the approved sample's expected results and fails
    (non-zero exit) on any difference. The defaults are the 744-row sample's values:
      raw rows 744, valid-sales rows 597, distinct orders 72, revenue 10,210.21, 13 months.
    Comparisons are done in SQL so Decimal values never meet Python floats. -#}
{% macro validate_sample_results(raw_rows=744, fct_rows=597, orders=72, revenue=10210.21, months=13) %}
    {% if execute %}
        {% set check_sql %}
            select
                (select count(*) from {{ source('raw', 'online_retail_sample') }})  as raw_rows,
                count(*)                                                            as fct_rows,
                count(distinct invoice_no)                                          as orders,
                round(sum(line_revenue), 2)                                         as revenue,
                count(distinct invoice_month)                                       as months
            from {{ ref('fct_sales') }}
        {% endset %}
        {% set result = run_query(check_sql) %}
        {% set actual = {
            'raw_rows': result.columns[0].values()[0] | int,
            'fct_rows': result.columns[1].values()[0] | int,
            'orders':   result.columns[2].values()[0] | int,
            'revenue':  result.columns[3].values()[0] | string,
            'months':   result.columns[4].values()[0] | int
        } %}
        {% set expected = {'raw_rows': raw_rows, 'fct_rows': fct_rows, 'orders': orders,
                           'revenue': revenue | string, 'months': months} %}
        {% set problems = [] %}
        {% for name in ['raw_rows', 'fct_rows', 'orders', 'months'] %}
            {% if actual[name] != expected[name] | int %}
                {% do problems.append(name ~ ': expected ' ~ expected[name] ~ ', found ' ~ actual[name]) %}
            {% endif %}
        {% endfor %}
        {#- revenue: compare as numbers with a half-cent tolerance, in SQL -#}
        {% set revenue_ok = run_query('select abs(' ~ actual['revenue'] ~ ' - ' ~ revenue ~ ') < 0.005').columns[0].values()[0] %}
        {% if not revenue_ok %}
            {% do problems.append('revenue: expected ' ~ revenue ~ ', found ' ~ actual['revenue']) %}
        {% endif %}
        {% if actual['fct_rows'] == 0 %}
            {% do problems.append('fct_sales is empty') %}
        {% elif actual['fct_rows'] > actual['raw_rows'] %}
            {% do problems.append('fct_sales has more rows than raw') %}
        {% endif %}
        {% if problems | length > 0 %}
            {{ exceptions.raise_compiler_error('Validation failed: ' ~ problems | join('; ')) }}
        {% endif %}
        {{ log('Validation OK: raw ' ~ actual['raw_rows'] ~ ' rows, fct_sales ' ~ actual['fct_rows']
               ~ ' rows, ' ~ actual['orders'] ~ ' orders, revenue ' ~ actual['revenue']
               ~ ', ' ~ actual['months'] ~ ' months', info=True) }}
    {% endif %}
{% endmacro %}
