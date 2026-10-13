-- Data-quality checks on the loaded star schema. EXPECTED RESULT: every "violations" value = 0
-- (except where a comment says otherwise). Runs on PostgreSQL and SQLite.

-- @query dq01_row_counts
SELECT (SELECT COUNT(*) FROM fact_sales)    AS fact_rows,
       (SELECT COUNT(*) FROM dim_customer)  AS customers,
       (SELECT COUNT(*) FROM dim_product)   AS products,
       (SELECT COUNT(*) FROM dim_geography) AS geographies,
       (SELECT COUNT(*) FROM dim_date)      AS dates;

-- @query dq02_duplicate_keys
-- Primary / natural keys must be unique.
SELECT 'fact_sales.row_id'      AS key_checked, COUNT(*) - COUNT(DISTINCT row_id)      AS violations FROM fact_sales
UNION ALL SELECT 'dim_customer.customer_id', COUNT(*) - COUNT(DISTINCT customer_id) FROM dim_customer
UNION ALL SELECT 'dim_product.product_id',   COUNT(*) - COUNT(DISTINCT product_id)  FROM dim_product
UNION ALL SELECT 'dim_date.full_date',       COUNT(*) - COUNT(DISTINCT full_date)   FROM dim_date;

-- @query dq03_orphan_foreign_keys
-- A fact row whose key has no matching dimension row would silently vanish from reports.
SELECT 'customer'  AS relationship, COUNT(*) AS violations FROM fact_sales f LEFT JOIN dim_customer  d ON d.customer_key  = f.customer_key  WHERE d.customer_key  IS NULL
UNION ALL SELECT 'product',   COUNT(*) FROM fact_sales f LEFT JOIN dim_product   d ON d.product_key   = f.product_key   WHERE d.product_key   IS NULL
UNION ALL SELECT 'geography', COUNT(*) FROM fact_sales f LEFT JOIN dim_geography d ON d.geography_key = f.geography_key WHERE d.geography_key IS NULL
UNION ALL SELECT 'order_date',COUNT(*) FROM fact_sales f LEFT JOIN dim_date      d ON d.date_key      = f.order_date_key WHERE d.date_key      IS NULL;

-- @query dq04_join_fanout_check
-- If a join duplicated rows, revenue through the joins would differ from revenue in the fact table.
SELECT ROUND(SUM(f.sales), 2) AS revenue_through_joins,
       (SELECT ROUND(SUM(sales), 2) FROM fact_sales) AS revenue_fact_only,
       ROUND(SUM(f.sales) - (SELECT SUM(sales) FROM fact_sales), 2) AS violations
FROM fact_sales f
JOIN dim_customer  c ON c.customer_key  = f.customer_key
JOIN dim_product   p ON p.product_key   = f.product_key
JOIN dim_geography g ON g.geography_key = f.geography_key
JOIN dim_date      d ON d.date_key      = f.order_date_key;

-- @query dq05_order_level_consistency
-- One order must belong to exactly one customer and one order date.
SELECT COUNT(*) AS violations FROM (
    SELECT order_id FROM fact_sales GROUP BY order_id
    HAVING COUNT(DISTINCT customer_key) > 1 OR COUNT(DISTINCT order_date_key) > 1) x;

-- @query dq06_business_rule_violations
SELECT 'quantity <= 0 and not a return'   AS rule, COUNT(*) AS violations FROM fact_sales WHERE quantity <= 0 AND is_return = 0
UNION ALL SELECT 'sales <= 0 and not a return', COUNT(*) FROM fact_sales WHERE sales <= 0 AND is_return = 0
UNION ALL SELECT 'discount outside 0-1',        COUNT(*) FROM fact_sales WHERE discount < 0 OR discount > 1
UNION ALL SELECT 'negative ship_days',          COUNT(*) FROM fact_sales WHERE ship_days < 0
UNION ALL SELECT 'return row with positive qty or sales', COUNT(*) FROM fact_sales WHERE is_return = 1 AND (quantity >= 0 OR sales >= 0);

-- @query dq07_months_without_orders
-- LAG-based growth is only correct if every month between the first and last order month has data.
WITH bounds AS (
    SELECT MIN(d.year_month) AS first_m, MAX(d.year_month) AS last_m
    FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key),
months AS (SELECT DISTINCT year_month FROM dim_date),
active AS (SELECT DISTINCT d.year_month FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key)
SELECT COUNT(*) AS violations
FROM months m CROSS JOIN bounds b
LEFT JOIN active a ON a.year_month = m.year_month
WHERE m.year_month BETWEEN b.first_m AND b.last_m AND a.year_month IS NULL;

-- @query dq08_expected_nonzero_flags
-- NOT violations: rows deliberately kept but flagged by the cleaning step (see reports/data_quality_report.md).
SELECT SUM(is_return) AS return_rows, SUM(is_price_outlier) AS price_outlier_rows,
       SUM(ship_date_invalid) AS invalid_ship_date_rows FROM fact_sales;
