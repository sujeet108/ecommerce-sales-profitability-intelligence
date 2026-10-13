# SQL-to-Python Reconciliation Report

SQL results come from `sql/business_analysis.sql` run on the star schema (SQLite). The pandas values are computed separately from `data/processed/superstore_clean.csv` and do not use the SQL files or the star schema.

**Result: 31 of 31 checks PASS.**

| check | SQL result | pandas result | abs diff | status |
|---|---|---|---|---|
| Total revenue | 3,738,533.15 | 3,738,533.15 | 0.0000 | PASS |
| Total profit | 700,783.13 | 700,783.13 | 0.0000 | PASS |
| Total orders (distinct Order ID) | 3,895.00 | 3,895.00 | 0.0000 | PASS |
| Units sold (net of returns) | 33,100.00 | 33,100.00 | 0.0000 | PASS |
| Order lines | 8,679.00 | 8,679.00 | 0.0000 | PASS |
| Average order value | 959.83 | 959.83 | 0.0012 | PASS |
| Profit margin % (weighted) | 18.74 | 18.74 | 0.0049 | PASS |
| Yearly revenue (max abs diff, 4 yrs) | 0.00 | 0.00 | 0.0000 | PASS |
| Yearly profit (max abs diff, 4 yrs) | 0.00 | 0.00 | 0.0000 | PASS |
| Monthly revenue (max abs diff, 48 months) | 0.00 | 0.00 | 0.0000 | PASS |
| MoM growth, Mar-2022 | 158.46 | 158.46 | 0.0012 | PASS |
| YoY growth 2025 % | 10.36 | 10.36 | 0.0039 | PASS |
| Running total ends at total revenue | 3,738,533.15 | 3,738,533.15 | 0.0000 | PASS |
| Top-10 products by revenue (same IDs, same order) | ['TEC-PH-10169', 'TEC-CO-10152', 'TEC-PH-10167', 'TEC-PH-101 | ['TEC-PH-10169', 'TEC-CO-10152', 'TEC-PH-10167', 'TEC-PH-101 |  | PASS |
| Top-10 revenue: sum of revenue | 1,485,226.99 | 1,485,226.99 | 0.0000 | PASS |
| Top-10 products by profit (same IDs, same order) | ['TEC-CO-10152', 'TEC-PH-10169', 'TEC-PH-10174', 'TEC-PH-101 | ['TEC-CO-10152', 'TEC-PH-10169', 'TEC-PH-10174', 'TEC-PH-101 |  | PASS |
| Loss-making products: count | 19.00 | 19.00 | 0.0000 | PASS |
| Loss-making products: total loss | -89,306.55 | -89,306.55 | 0.0000 | PASS |
| Region revenue (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Region profit (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Cities in Q10b | 27.00 | 27.00 | 0.0000 | PASS |
| Sub-category profit (max abs diff, 17) | 0.00 | 0.00 | 0.0000 | PASS |
| Segment revenue (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Discount-band revenue (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Discount-band profit (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Discount-band line counts (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Orders by ship mode (max abs diff) | 0.00 | 0.00 | 0.0000 | PASS |
| Avg ship days, Standard Class | 5.50 | 5.50 | 0.0034 | PASS |
| Repeat-customer buckets (1 / 2-4 / 5+) | [132, 289, 333] | [132, 289, 333] |  | PASS |
| Distinct customers | 754.00 | 754.00 | 0.0000 | PASS |
| Unit-price outliers: SQL (leave-one-out) vs cleaning flag, same row IDs | [108, 537, 1579, 2306, 3489, 6108] | [108, 537, 1579, 2306, 3489, 6108] |  | PASS |


## Expected KPI values for Power BI

Build the report, then clear all slicers and compare each card with the first row below; apply one slicer at a time and compare with the other rows. These numbers come from the same clean data, so a difference means a modelling or DAX error in Power BI.

| filter_context | total_revenue | total_profit | profit_margin_pct | total_orders | units_sold | avg_order_value |
|---|---|---|---|---|---|---|
| All data | 3738533.15 | 700783.13 | 18.74 | 3895 | 33100 | 959.83 |
| Year = 2022 | 733610.92 | 140675.73 | 19.18 | 768 | 6482 | 955.22 |
| Year = 2023 | 901075.89 | 152305.94 | 16.9 | 931 | 8156 | 967.86 |
| Year = 2024 | 1000098.34 | 189378.33 | 18.94 | 1036 | 8673 | 965.35 |
| Year = 2025 | 1103748.0 | 218423.13 | 19.79 | 1160 | 9789 | 951.51 |
| Region = West | 1051305.46 | 215990.19 | 20.54 | 1072 | 8977 | 980.7 |
| Region = South | 1003127.84 | 211171.72 | 21.05 | 936 | 8196 | 1071.72 |
| Region = East | 957777.16 | 189405.52 | 19.78 | 980 | 8170 | 977.32 |
| Region = Central | 726322.69 | 84215.7 | 11.59 | 907 | 7757 | 800.8 |
| Category = Furniture | 1172045.17 | 62041.23 | 5.29 | 1574 | 7583 | 744.63 |
| Category = Office Supplies | 580181.44 | 173102.83 | 29.84 | 2984 | 18854 | 194.43 |
| Category = Technology | 1986306.54 | 465639.07 | 23.44 | 1414 | 6663 | 1404.74 |
| Excluding 6 flagged price outliers | 3714690.75 | 677449.97 | 18.24 | 3893 | 33089 | 954.2 |