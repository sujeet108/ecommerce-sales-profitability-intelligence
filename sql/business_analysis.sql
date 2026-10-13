-- =====================================================================
-- Business analysis queries. Portable SQL (PostgreSQL 14+ and SQLite 3.25+).
-- Definitions used everywhere:
--   Revenue  = SUM(sales)   (net of discount, net of returns)
--   Profit   = SUM(profit)
--   Orders   = COUNT(DISTINCT order_id)   -- NOT COUNT(*): one order has several lines
--   Margin   = SUM(profit) / SUM(sales)   -- NOT the average of line margins
-- =====================================================================

-- @query Q01_total_revenue_profit
SELECT ROUND(SUM(sales), 2) AS total_revenue, ROUND(SUM(profit), 2) AS total_profit FROM fact_sales;

-- @query Q02_orders_and_units
-- Orders are counted on the order identifier. Units are net of returned quantity.
SELECT COUNT(DISTINCT order_id) AS total_orders, SUM(quantity) AS units_sold, COUNT(*) AS order_lines FROM fact_sales;

-- @query Q03_average_order_value
-- AOV = total revenue / number of distinct orders.
SELECT ROUND(SUM(sales) * 1.0 / COUNT(DISTINCT order_id), 2) AS average_order_value FROM fact_sales;

-- @query Q04_profit_margin
-- Weighted margin: total profit divided by total sales.
SELECT ROUND(100.0 * SUM(profit) / SUM(sales), 2) AS profit_margin_pct FROM fact_sales;

-- @query Q05a_monthly_trend
SELECT d.year_month,
       ROUND(SUM(f.sales), 2)  AS revenue,
       ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct,
       COUNT(DISTINCT f.order_id) AS orders
FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key
GROUP BY d.year_month ORDER BY d.year_month;

-- @query Q05b_yearly_trend
-- YoY growth compares each year with the previous year via LAG.
WITH yearly AS (
    SELECT d.year, SUM(f.sales) AS revenue, SUM(f.profit) AS profit, COUNT(DISTINCT f.order_id) AS orders
    FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key GROUP BY d.year)
SELECT year, ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit,
       ROUND(100.0 * profit / revenue, 2) AS margin_pct, orders,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year)) / LAG(revenue) OVER (ORDER BY year), 2) AS yoy_revenue_growth_pct
FROM yearly ORDER BY year;

-- @query Q06_month_over_month_growth
-- Valid because dq07 proves there are no months without orders in the range.
WITH monthly AS (
    SELECT d.year_month, SUM(f.sales) AS revenue
    FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key GROUP BY d.year_month)
SELECT year_month, ROUND(revenue, 2) AS revenue,
       ROUND(LAG(revenue) OVER (ORDER BY year_month), 2) AS prev_month_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year_month)) / LAG(revenue) OVER (ORDER BY year_month), 2) AS mom_growth_pct
FROM monthly ORDER BY year_month;

-- @query Q07_top10_products_by_revenue
SELECT p.product_id, p.product_name, p.sub_category,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_id, p.product_name, p.sub_category
ORDER BY SUM(f.sales) DESC, p.product_id LIMIT 10;

-- @query Q08_top10_products_by_profit
SELECT p.product_id, p.product_name, p.sub_category,
       ROUND(SUM(f.profit), 2) AS profit, ROUND(SUM(f.sales), 2) AS revenue,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_id, p.product_name, p.sub_category
ORDER BY SUM(f.profit) DESC, p.product_id LIMIT 10;

-- @query Q09a_loss_making_products
-- Net profit below zero over the whole period (returns included, since they are part of net profit).
SELECT p.product_id, p.product_name, p.sub_category,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct,
       ROUND(100.0 * AVG(f.discount), 1) AS avg_discount_pct
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_id, p.product_name, p.sub_category
HAVING SUM(f.profit) < 0
ORDER BY SUM(f.profit);

-- @query Q09b_loss_making_subcategories
-- Shows every sub-category with its loss-making line count so categories that are profitable overall
-- but leak money on individual lines are visible too.
SELECT p.category, p.sub_category,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       SUM(CASE WHEN f.profit < 0 AND f.is_return = 0 THEN 1 ELSE 0 END) AS loss_lines,
       SUM(CASE WHEN f.is_return = 0 THEN 1 ELSE 0 END) AS sale_lines,
       ROUND(100.0 * SUM(CASE WHEN f.profit < 0 AND f.is_return = 0 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN f.is_return = 0 THEN 1 ELSE 0 END), 1) AS loss_line_pct,
       ROUND(SUM(CASE WHEN f.profit < 0 AND f.is_return = 0 THEN f.profit ELSE 0 END), 2) AS profit_lost_on_loss_lines
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category, p.sub_category
ORDER BY SUM(f.profit);

-- @query Q10a_region_performance
SELECT g.region, ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct,
       ROUND(100.0 * SUM(f.sales) / SUM(SUM(f.sales)) OVER (), 2)  AS revenue_share_pct,
       ROUND(100.0 * SUM(f.profit) / SUM(SUM(f.profit)) OVER (), 2) AS profit_share_pct,
       ROUND(100.0 * AVG(f.discount), 1) AS avg_discount_pct
FROM fact_sales f JOIN dim_geography g ON g.geography_key = f.geography_key
GROUP BY g.region ORDER BY SUM(f.sales) DESC;

-- @query Q10b_city_performance
SELECT g.city, g.state, g.region, COUNT(DISTINCT f.order_id) AS orders,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct
FROM fact_sales f JOIN dim_geography g ON g.geography_key = f.geography_key
GROUP BY g.city, g.state, g.region ORDER BY SUM(f.sales) DESC;

-- @query Q11_category_subcategory_profitability
SELECT p.category, p.sub_category,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct,
       ROUND(100.0 * SUM(f.profit) / SUM(SUM(f.profit)) OVER (), 2) AS share_of_total_profit_pct,
       RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.profit) DESC) AS profit_rank_in_category
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category, p.sub_category
ORDER BY p.category, profit_rank_in_category;

-- @query Q12_customer_segment
SELECT c.segment, COUNT(DISTINCT c.customer_key) AS customers, COUNT(DISTINCT f.order_id) AS orders,
       ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct,
       ROUND(SUM(f.sales) * 1.0 / COUNT(DISTINCT f.order_id), 2) AS avg_order_value,
       ROUND(100.0 * SUM(f.sales) / SUM(SUM(f.sales)) OVER (), 2) AS revenue_share_pct
FROM fact_sales f JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY c.segment ORDER BY SUM(f.sales) DESC;

-- @query Q13a_discount_band_profitability
-- Returns are excluded: they carry the discount of the original sale and would double count it.
SELECT CASE WHEN discount = 0 THEN '0. No discount'
            WHEN discount <= 0.10 THEN '1. Up to 10%'
            WHEN discount <= 0.20 THEN '2. 11-20%'
            WHEN discount <= 0.30 THEN '3. 21-30%'
            WHEN discount <= 0.50 THEN '4. 31-50%'
            ELSE '5. Over 50%' END AS discount_band,
       COUNT(*) AS lines, ROUND(SUM(sales), 2) AS revenue, ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2) AS margin_pct,
       ROUND(100.0 * SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS loss_line_pct
FROM fact_sales WHERE is_return = 0
GROUP BY 1 ORDER BY 1;

-- @query Q13b_discount_by_category
SELECT p.category,
       CASE WHEN f.discount = 0 THEN '0. No discount' WHEN f.discount <= 0.20 THEN '1. 1-20%'
            WHEN f.discount <= 0.40 THEN '2. 21-40%' ELSE '3. Over 40%' END AS discount_band,
       COUNT(*) AS lines, ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
       ROUND(100.0 * SUM(f.profit) / SUM(f.sales), 2) AS margin_pct
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
WHERE f.is_return = 0
GROUP BY p.category, 2 ORDER BY p.category, 2;

-- @query Q14_shipping_mode_performance
-- Average ship days ignores rows whose source ship date was invalid (NULL).
SELECT ship_mode, COUNT(DISTINCT order_id) AS orders, ROUND(SUM(sales), 2) AS revenue,
       ROUND(SUM(profit), 2) AS profit, ROUND(100.0 * SUM(profit) / SUM(sales), 2) AS margin_pct,
       ROUND(AVG(ship_days), 2) AS avg_ship_days, COUNT(ship_days) AS lines_with_valid_ship_date
FROM fact_sales GROUP BY ship_mode ORDER BY SUM(sales) DESC;

-- @query Q15a_repeat_customers
WITH cust AS (
    SELECT customer_key, COUNT(DISTINCT order_id) AS orders, SUM(sales) AS revenue
    FROM fact_sales GROUP BY customer_key)
SELECT CASE WHEN orders = 1 THEN '1. One-time' WHEN orders <= 4 THEN '2. 2-4 orders' ELSE '3. 5+ orders' END AS customer_type,
       COUNT(*) AS customers, SUM(orders) AS orders, ROUND(SUM(revenue), 2) AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM cust), 2) AS revenue_share_pct
FROM cust GROUP BY 1 ORDER BY 1;

-- @query Q15b_new_vs_returning_by_year
-- "New" means first order seen in this dataset. Every 2022 customer is "new" by construction
-- (the data starts in 2022), so read 2022 as the baseline.
WITH first_year AS (
    SELECT f.customer_key, MIN(d.year) AS first_year
    FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key GROUP BY f.customer_key),
active AS (
    SELECT DISTINCT f.customer_key, d.year
    FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key)
SELECT a.year, COUNT(*) AS active_customers,
       SUM(CASE WHEN a.year = fy.first_year THEN 1 ELSE 0 END) AS new_customers,
       SUM(CASE WHEN a.year > fy.first_year THEN 1 ELSE 0 END) AS returning_customers
FROM active a JOIN first_year fy ON fy.customer_key = a.customer_key
GROUP BY a.year ORDER BY a.year;

-- @query Q16a_running_total_revenue
SELECT year_month, ROUND(revenue, 2) AS revenue,
       ROUND(SUM(revenue) OVER (ORDER BY year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total_all_time,
       ROUND(SUM(revenue) OVER (PARTITION BY SUBSTR(year_month, 1, 4) ORDER BY year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total_ytd
FROM (SELECT d.year_month, SUM(f.sales) AS revenue
      FROM fact_sales f JOIN dim_date d ON d.date_key = f.order_date_key GROUP BY d.year_month) m
ORDER BY year_month;

-- @query Q16b_top3_products_per_category
SELECT category, revenue_rank, product_name, revenue, profit FROM (
    SELECT p.category, p.product_name, ROUND(SUM(f.sales), 2) AS revenue, ROUND(SUM(f.profit), 2) AS profit,
           RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.sales) DESC) AS revenue_rank
    FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
    GROUP BY p.category, p.product_id, p.product_name) r
WHERE revenue_rank <= 3 ORDER BY category, revenue_rank;

-- @query Q16c_customer_pareto_top10
WITH cust AS (
    SELECT c.customer_id, c.customer_name, SUM(f.sales) AS revenue
    FROM fact_sales f JOIN dim_customer c ON c.customer_key = f.customer_key GROUP BY c.customer_id, c.customer_name),
ranked AS (
    SELECT customer_id, customer_name, revenue,
           RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
           SUM(revenue) OVER (ORDER BY revenue DESC, customer_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_revenue,
           SUM(revenue) OVER () AS total_revenue
    FROM cust)
SELECT revenue_rank, customer_id, customer_name, ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * revenue / total_revenue, 2) AS share_pct,
       ROUND(100.0 * running_revenue / total_revenue, 2) AS cumulative_share_pct
FROM ranked WHERE revenue_rank <= 10 ORDER BY revenue_rank;

-- @query Q17a_unusual_unit_price
-- Implied list price per unit = sales / (quantity x (1 - discount)). A line is suspicious when it is more than
-- 5x the average of the product's OTHER lines (leave-one-out, so the suspicious line cannot hide inside its own average).
WITH priced AS (
    SELECT f.row_id, f.order_id, p.product_id, p.product_name, f.sales, f.quantity, f.discount, f.profit,
           f.sales * 1.0 / (f.quantity * (1 - f.discount)) AS unit_list
    FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
    WHERE f.is_return = 0 AND f.quantity > 0),
bench AS (
    SELECT *, (SUM(unit_list) OVER (PARTITION BY product_id) - unit_list) * 1.0
              / (COUNT(*) OVER (PARTITION BY product_id) - 1) AS avg_other_lines
    FROM priced)
SELECT row_id, order_id, product_name, ROUND(sales, 2) AS sales, quantity, discount,
       ROUND(unit_list, 2) AS unit_price_this_line, ROUND(avg_other_lines, 2) AS avg_unit_price_other_lines,
       ROUND(unit_list / avg_other_lines, 1) AS ratio
FROM bench WHERE avg_other_lines > 0 AND unit_list > 5 * avg_other_lines ORDER BY ratio DESC;

-- @query Q17b_largest_loss_lines
SELECT f.row_id, f.order_id, p.product_name, f.quantity, f.discount, ROUND(f.sales, 2) AS sales, ROUND(f.profit, 2) AS profit
FROM fact_sales f JOIN dim_product p ON p.product_key = f.product_key
WHERE f.is_return = 0 ORDER BY f.profit LIMIT 10;

-- @query Q17c_flag_summary
SELECT 'Valid returns (negative qty/sales)' AS flag, COUNT(*) AS lines FROM fact_sales WHERE is_return = 1
UNION ALL SELECT 'Price outliers flagged by cleaning step', COUNT(*) FROM fact_sales WHERE is_price_outlier = 1
UNION ALL SELECT 'Invalid ship date blanked', COUNT(*) FROM fact_sales WHERE ship_date_invalid = 1
UNION ALL SELECT 'Loss-making lines (profit < 0, not a return)', COUNT(*) FROM fact_sales WHERE profit < 0 AND is_return = 0
UNION ALL SELECT 'Lines sold at discount > 50%', COUNT(*) FROM fact_sales WHERE discount > 0.5 AND is_return = 0;
