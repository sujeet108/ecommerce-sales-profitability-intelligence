# Testing and Validation Checklist

Run `python src/run_pipeline.py` then `python tests/test_pipeline.py`. "Result here" is what happened when this repository was built.

## A. Automated (done)
| # | Check | Expected | Result here |
|---|---|---|---|
| 1 | Row ID unique, no duplicate rows in clean data | 0 duplicates | PASS |
| 2 | Business rules: discount 0-1, positive qty/sales except returns, 5-digit or `Unknown` postal, 4 valid regions | 0 violations | PASS |
| 3 | Returns and loss-making sales kept | both > 0 | PASS |
| 4 | Every raw row accounted for: raw = clean + quarantined + duplicates | equal | PASS (8,747 = 8,679 + 23 + 45) |
| 5 | Star schema: fact rows = clean rows, 0 FK violations, 0 duplicate keys, join fan-out = 0 | all 0 | PASS |
| 6 | SQL vs pandas reconciliation | 31/31 | PASS |
| 7 | Weighted margin differs from average of line margins (proves the definition matters) | differ | PASS |
| 8 | SQL data-quality checks `dq01`-`dq07` | all violations = 0 | PASS |
| 9 | Planted problems found by cleaning code (answer key) | all match | PASS (section 4 of data quality report) |
| 10 | Notebook build-time assertions on commentary claims | all hold | PASS |

## B. SQL on your PostgreSQL (to do)
| # | Step | Expected |
|---|---|---|
| 1 | `psql -f sql/schema.sql`, then `sql/load_data_postgres.sql` | 5 tables; counts 8,679 / 754 / 174 / 72 / 1,826 |
| 2 | Run `sql/data_quality_checks.sql` | every `violations` = 0 |
| 3 | Run `Q01`-`Q04` from `sql/business_analysis.sql` | revenue 3,738,533.15 · profit 700,783.13 · orders 3,895 · margin 18.74% |
| 4 | Compare other results with `reports/sql_results/*.csv` | identical (ties in rankings are broken by product ID) |

## C. Power BI (to do, after building the report)
| # | Check | Expected |
|---|---|---|
| 1 | Row counts after load | fact 8,679; customer 754; product 174; geography 72; date 1,826 |
| 2 | No slicers | Revenue 3,738,533.15 · Profit 700,783.13 · Margin 18.74% · Orders 3,895 · Units 33,100 · AOV 959.83 |
| 3 | Year = 2023 | Revenue 901,075.89 · Margin 16.90% · Orders 931 |
| 4 | Region = Central | Revenue 726,322.69 · Margin 11.59% · Orders 907 |
| 5 | Category = Furniture | Revenue 1,172,045.17 · Margin 5.29% |
| 6 | `is_price_outlier = 0` | Revenue 3,714,690.75 · Margin 18.24% |
| 7 | Monthly chart | 48 months, no gaps |
| 8 | Sum of regional revenue on Page 3 | equals total revenue (no double counting) |
| 9 | Date and slicer sync across pages | same selection on all 5 pages |
| 10 | Drill-through from a product to the detail page | shows only that product |
Full expected table: `powerbi/expected_kpis.csv`.

## D. Excel spot check (optional, 5 minutes)
Open `data/processed/superstore_clean.csv`, insert a PivotTable: Rows = Region, Values = Sum of Sales, Sum of Profit. Totals must equal the Page 3 numbers.
