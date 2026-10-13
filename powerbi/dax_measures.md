# DAX Measures

> **Status: written and explained, NOT executed.** No Power BI Desktop was available while building this repo, so these measures have not been run against the model. They are checked by design against the SQL and pandas results: after building the report, compare every card with `powerbi/expected_kpis.csv`. If a value differs, the DAX or the model is wrong, not the data.

## Model (create these relationships in Model view)

| From (many) | To (one) | Cardinality / direction | Active |
|---|---|---|---|
| `fact_sales[order_date_key]` | `dim_date[date_key]` | Many-to-one, single | **Yes** |
| `fact_sales[ship_date_key]` | `dim_date[date_key]` | Many-to-one, single | No (use `USERELATIONSHIP`) |
| `fact_sales[customer_key]` | `dim_customer[customer_key]` | Many-to-one, single | Yes |
| `fact_sales[product_key]` | `dim_product[product_key]` | Many-to-one, single | Yes |
| `fact_sales[geography_key]` | `dim_geography[geography_key]` | Many-to-one, single | Yes |

* Mark `dim_date` as the **Date table** (column `full_date`, type Date). It holds every calendar day of every year in the data, with no gaps, which time-intelligence functions require.
* Sort `dim_date[month_name]` by `month_num`.
* Hide the key columns in the fact table so report authors cannot slice by them by mistake.
* Do **not** create a bi-directional relationship; it is the usual source of double counting.

## Why these definitions

| Rule | Reason |
|---|---|
| Orders = `DISTINCTCOUNT(order_id)` | One order has several lines. `COUNTROWS` would count lines (8,679) not orders (3,895). |
| Margin = total profit / total sales | Averaging line margins gives every tiny line the same weight as a large one. On this data the two answers differ. |
| Use `DIVIDE()` | Returns blank, not an error, when the denominator is zero. |
| Returns stay in revenue | Returns have negative sales, so revenue is **net** revenue. |

## Core measures

```DAX
Total Revenue = SUM ( fact_sales[sales] )

Total Profit = SUM ( fact_sales[profit] )

Total Orders = DISTINCTCOUNT ( fact_sales[order_id] )

Units Sold = SUM ( fact_sales[quantity] )          -- net of returned units

Profit Margin % = DIVIDE ( [Total Profit], [Total Revenue] )

Average Order Value = DIVIDE ( [Total Revenue], [Total Orders] )

Order Lines = COUNTROWS ( fact_sales )
```
Expected, no filters: revenue 3,738,533.15 · profit 700,783.13 · margin 18.74% · orders 3,895 · units 33,100 · AOV 959.83.

## Time intelligence

```DAX
Previous Month Revenue =
CALCULATE ( [Total Revenue], PREVIOUSMONTH ( dim_date[full_date] ) )

MoM Growth % =
VAR Prev = [Previous Month Revenue]
RETURN DIVIDE ( [Total Revenue] - Prev, Prev )

Previous Year Revenue =
CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_date[full_date] ) )

YoY Growth % =
VAR Prev = [Previous Year Revenue]
RETURN DIVIDE ( [Total Revenue] - Prev, Prev )

Revenue YTD = TOTALYTD ( [Total Revenue], dim_date[full_date] )
```
* Both measures need the month or year in filter context (use `dim_date[year_month]` or `year` on an axis). On a card with no date filter they return blank, which is correct.
* Years are 2022-2025, so 2022 has no prior year and YoY is blank for 2022. Expected YoY: 2023 +22.8%, 2024 +11.0%, 2025 +10.4%.
* Because `dim_date` is a complete calendar, a month with no sales still exists and the previous-month lookup cannot silently skip it.

## Contribution and ranking

```DAX
Revenue Contribution % =
DIVIDE ( [Total Revenue], CALCULATE ( [Total Revenue], ALLSELECTED () ) )

Profit Contribution % =
DIVIDE ( [Total Profit], CALCULATE ( [Total Profit], ALLSELECTED () ) )

Product Revenue Rank =
RANKX ( ALLSELECTED ( dim_product[product_name] ), [Total Revenue], , DESC, DENSE )

Product Profit Rank =
RANKX ( ALLSELECTED ( dim_product[product_name] ), [Total Profit], , DESC, DENSE )

Is Top 10 by Profit = IF ( [Product Profit Rank] <= 10, 1, 0 )   -- use as a visual-level filter = 1
```
`ALLSELECTED()` keeps slicer selections but ignores the visual's own rows, so a region's share is "of what the slicers currently show", not of the whole company.

## Discount and loss measures

```DAX
Discounted Revenue =
CALCULATE ( [Total Revenue], fact_sales[discount] > 0, fact_sales[is_return] = 0 )

Discounted Profit =
CALCULATE ( [Total Profit], fact_sales[discount] > 0, fact_sales[is_return] = 0 )

Discounted Margin % = DIVIDE ( [Discounted Profit], [Discounted Revenue] )

Discounted Lines % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_sales ), fact_sales[discount] > 0, fact_sales[is_return] = 0 ),
    CALCULATE ( COUNTROWS ( fact_sales ), fact_sales[is_return] = 0 )
)

Avg Discount % = CALCULATE ( AVERAGE ( fact_sales[discount] ), fact_sales[is_return] = 0 )

Loss-Making Lines =
CALCULATE ( COUNTROWS ( fact_sales ), fact_sales[profit] < 0, fact_sales[is_return] = 0 )

Loss-Making Products =
SUMX ( VALUES ( dim_product[product_id] ), IF ( [Total Profit] < 0, 1, 0 ) )

Loss Amount on Loss Lines =
CALCULATE ( [Total Profit], fact_sales[profit] < 0, fact_sales[is_return] = 0 )
```
Returns are excluded from discount measures because they carry the discount of the original sale and would count it twice (SQL query Q13a does the same).
Expected, no filters: discounted lines 39.4% of sale lines; loss-making products: see `reports/sql_results/q_Q09a_loss_making_products.csv` (row count).

## Discount band (calculated column in `fact_sales`)

```DAX
Discount Band =
SWITCH (
    TRUE (),
    fact_sales[discount] = 0,    "0. No discount",
    fact_sales[discount] <= 0.10, "1. Up to 10%",
    fact_sales[discount] <= 0.20, "2. 11-20%",
    fact_sales[discount] <= 0.30, "3. 21-30%",
    fact_sales[discount] <= 0.50, "4. 31-50%",
    "5. Over 50%"
)
```
Put `Discount Band` on a visual axis with `[Profit Margin %]` and filter the visual to `is_return = 0`.

## Customers and shipping

```DAX
Customers = DISTINCTCOUNT ( fact_sales[customer_key] )

Repeat Customers =
COUNTROWS (
    FILTER ( VALUES ( dim_customer[customer_key] ),
             CALCULATE ( DISTINCTCOUNT ( fact_sales[order_id] ) ) >= 2 )
)

Repeat Customer % = DIVIDE ( [Repeat Customers], [Customers] )

Avg Ship Days = AVERAGE ( fact_sales[ship_days] )          -- blank ship days (14 invalid dates) are ignored
```
The first-order date is the start of the data (2022), so "repeat" means two or more orders within the four years.

## Data-quality helpers

```DAX
Revenue excl. Price Outliers =
CALCULATE ( [Total Revenue], fact_sales[is_price_outlier] = 0 )

Profit excl. Price Outliers =
CALCULATE ( [Total Profit], fact_sales[is_price_outlier] = 0 )
```
Expected: revenue 3,714,690.75 · profit 677,449.97 · margin 18.24%.

## How these measures avoid the common errors

| Risk | How it is handled |
|---|---|
| Duplicate joins inflating totals | Star schema, one-to-many relationships only, single-direction filters. SQL check `dq04` proves the joins do not change revenue. |
| Counting lines as orders | `DISTINCTCOUNT(order_id)` |
| Averaging ratios | Every percentage is a ratio of two sums |
| Missing periods | Full-calendar `dim_date` marked as Date table |
| Filter context surprises | Contribution uses `ALLSELECTED()`; discount measures state `is_return = 0` explicitly |
| Divide by zero | `DIVIDE()` |
