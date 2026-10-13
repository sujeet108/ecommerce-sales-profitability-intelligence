# Methodology

## Stages and what each does (plain English)
| # | Stage | Script | Purpose |
|---|---|---|---|
| 1 | Create data | `src/generate_synthetic_data.py` | Make a retail-style file with realistic mistakes planted on purpose, and an answer key of those mistakes |
| 2 | Clean | `src/data_cleaning.py`, `src/data_validation.py` | Fix what can be fixed safely, quarantine what is invalid, flag what is merely unusual, report before and after |
| 3 | Model | `src/build_star_schema.py`, `sql/schema.sql` | Split the flat file into a fact table and four dimensions so BI tools filter and aggregate correctly |
| 4 | Query | `sql/business_analysis.sql`, `sql/data_quality_checks.sql`, `src/sql_runner.py` | Answer the business questions in SQL and prove the database is sound |
| 5 | Explore | `notebooks/ecommerce_eda.ipynb` | Charts and statistics, with commentary built from the computed numbers |
| 6 | Reconcile | `src/reconcile.py`, `tests/test_pipeline.py` | Recompute everything independently in pandas and compare to SQL |
| 7 | Report | `src/generate_insights.py` | Findings and recommendations with the supporting metric and assumption |
| 8 | Dashboard | `powerbi/` | Power BI model, DAX and build guide |

## Metric definitions
* **Revenue** = sum of `sales` (net of discount and of returns).
* **Profit** = sum of `profit`. **Margin** = total profit / total sales.
* **Orders** = distinct `order_id`. **Units** = sum of `quantity` (net of returns). **AOV** = revenue / orders.
* **Loss-making line** = non-return line with profit < 0. **Loss-making product** = product whose net profit over the period is < 0.
* **Discount band** edges: 0, up to 10%, up to 20%, up to 30%, up to 50%, above 50%. Returns excluded.

## Cleaning rules (and why)
1. Read every field as text first, so nothing is silently converted.
2. Trim and standardise text to a fixed list of valid values; map known aliases (`USA`, `Furnitures`).
3. Parse each known date format explicitly; never guess day/month order.
4. Drop **exact** duplicate rows only (same Row ID and identical values).
5. **Quarantine** (do not delete silently) rows that cannot be right: quantity or sales not positive when it is not a return, discount outside 0-1, missing key fields. They go to `rejected_rows.csv` with a reason.
6. **Keep** legitimate returns (negative quantity and sales) and all loss-making sales. They are real business outcomes.
7. **Flag, don't delete,** suspicious values: price more than 5x the product's median, ship date before order date.
8. Recover missing values only from the data itself (customer name from the same customer ID). Postal code is not guessable, so it becomes `Unknown`.

## Verification: what was actually run
| Item | Run here? | Evidence |
|---|---|---|
| Data generation, cleaning, star schema | Yes | `reports/data_quality_report.md` |
| SQL schema and all 34 queries | Yes, on **SQLite 3.45** | `reports/sql_results/` |
| SQL on **PostgreSQL / MySQL** | **No** (no server available) | The SQL is written in portable syntax (no `::`, `DATE_TRUNC`, `ILIKE`); run it once yourself and expect identical results |
| SQL vs pandas reconciliation | Yes, 31/31 pass | `reports/reconciliation_report.md` |
| Automated tests | Yes, 7/7 pass | `python tests/test_pipeline.py` |
| Notebook | Executed by a custom runner that embeds outputs; re-run in Jupyter to refresh | `notebooks/ecommerce_eda.ipynb` |
| Power BI report, DAX | **No** | Specification only; `.pbix` not produced |
| Excel | Not used for delivery | Optional check: open the clean CSV, insert a PivotTable of Sum of Sales by Region and compare with `expected_kpis.csv` |

## Assumptions
* Discount is a fraction of list price; `Sales` already reflects it.
* A return is a partial reversal booked against the original order.
* The 5x price-outlier threshold is a judgement. Lines 2-5x above normal are not flagged.
* Customer "new" means first order within the data window.

## Limitations
See `docs/data_dictionary.md` and `reports/business_insights.md`. Chief among them: the data is synthetic, so no real-world conclusions are drawn, and discount effects are associations in observational data.
