# Dashboard Design and Build Guide

> **Status: design specification only. No `.pbix` file or screenshots exist in this repo** because Power BI Desktop (Windows) was not available while it was built. Follow this guide (about 2-3 hours), then save screenshots to `powerbi/dashboard_screenshots/`. The expected numbers to verify against are in `expected_kpis.csv`; the matching charts already exist as PNGs in `reports/figures/` for visual reference.

## Global settings
* Canvas 16:9 (1280 x 720). Theme colours: Blue `#2E6F9E` (revenue), Teal `#2A9D8F` (profit), Red `#D1495B` (loss / warning), Grey `#8D99AE`.
* Conditional format every margin and profit value: red when below 0.
* Number formats: money `$#,0` or `$#,0,"K"`; margins `0.0%`.
* **Slicers (same on all pages, via View > Sync slicers):** Order date (between), Region, Category, Sub-category, Segment. Add a **Clear all slicers** bookmark button.
* Navigation: a left rail of 5 page-navigation buttons (Insert > Buttons > Navigator > Page navigator).
* Add a footer text box on every page: "Synthetic data for portfolio demonstration".
* Edit interactions so cards are not filtered by the visual that drills them (Format > Edit interactions).

## Page 1 - Executive Overview
| Visual | Fields |
|---|---|
| 6 KPI cards | Total Revenue, Total Profit, Profit Margin %, Total Orders, Units Sold, Average Order Value |
| Line + clustered column | Axis `dim_date[year_month]`; columns Total Revenue; line Total Profit |
| Donut or bar | Legend `dim_product[category]`; values Total Revenue |
| Filled map or bar | `dim_geography[region]` with Total Revenue and Profit Margin % (tooltip) |
Add small "vs previous month" text using `MoM Growth %` under the revenue card.

## Page 2 - Product Profitability
| Visual | Fields |
|---|---|
| Bar (Top 10) | `product_name` by Total Profit, visual filter `Is Top 10 by Profit` = 1 |
| Bar (Bottom 10) | `product_name` by Total Profit, filter Top N = 10, Bottom, by Total Profit |
| Matrix | Rows category > sub_category; values Revenue, Profit, Profit Margin % (conditional colour) |
| Scatter | Details `product_name`; X Total Revenue; Y Total Profit; Colour `sub_category` |
| Table | Loss-making products: `product_name`, Total Revenue, Total Profit, Avg Discount %; filter Total Profit < 0 |
Drill-through target: a hidden page "Product detail" with `product_name` as the drill-through field.

## Page 3 - Regional Performance
| Visual | Fields |
|---|---|
| Clustered bar | region: Total Revenue, Total Profit |
| 100% stacked / donut | region by Revenue Contribution % |
| Bar | region by Profit Margin % with a constant line at company margin (Analytics pane) |
| Matrix with drill-down | Rows region > state > city: Revenue, Profit, Profit Margin % |
| Map | `city` size = Total Revenue, colour = Profit Margin % |

## Page 4 - Discount Analysis
| Visual | Fields |
|---|---|
| Column | Axis `Discount Band`; values Profit Margin %; filter `is_return` = 0 |
| Column | Axis `Discount Band`; values Loss-Making Lines |
| Scatter | Details `sub_category`; X Discounted Lines %; Y Profit Margin %; size Total Revenue |
| Matrix heatmap | Rows `sub_category`; columns `Discount Band`; values Profit Margin % (colour scale red-yellow-green) |
| Table | High sales, low profit: `product_name`, Total Revenue, Profit Margin %; filter Revenue Contribution rank and Margin < 10% |

## Page 5 - Customer and Order Analysis
| Visual | Fields |
|---|---|
| Bar | `segment` by Total Revenue, with Profit Margin % in tooltip |
| Line | `dim_date[year]` > month by Total Orders, legend `segment` |
| Pareto | Top 10 customers by Total Revenue (Top N filter) |
| Cards | Customers, Repeat Customers, Repeat Customer % (note: repeat is within 2022-2025 only) |

## Tooltips and drill-through
* Create a hidden page "Tooltip" (Page size > Tooltip) with Revenue, Profit, Margin, Orders. Assign it to the charts on pages 1-3 (Format visual > General > Tooltips).
* Drill-through pages: **Product detail** (field `product_name`) and **City detail** (field `city`).

## Validation steps (do before screenshots)
1. Clear slicers. Each card must match row 1 of `expected_kpis.csv`.
2. Set Region = Central. Cards must match the `Region = Central` row (revenue 726,322.69, margin 11.59%).
3. Set Order date to 2023 only: revenue 901,075.89, margin 16.90%.
4. Add a visual filter `is_price_outlier = 0`: revenue 3,714,690.75, margin 18.24%.
5. Open Model view: five relationships, all one-to-many, one inactive.
6. Page 1 monthly chart: 48 months (Jan 2022 - Dec 2025), no gaps. `dim_date` runs to Dec 2026 because ship dates fall there; add a page-level filter `dim_date[year] <= 2025` so no empty 2026 months appear on axes.
