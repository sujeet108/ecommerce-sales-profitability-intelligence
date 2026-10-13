# Resume Description and Interview Preparation

## Resume bullets (adjust to what you actually built)
**E-commerce Sales & Profitability Intelligence** - Python, SQL (PostgreSQL), Power BI, DAX | GitHub link

* Built an end-to-end analytics pipeline on a **synthetic 8,700-line retail dataset** (3,895 orders, 2022-2025): automated cleaning that found and quarantined invalid rows, standardised text and dates, and kept returns and loss-making sales, with a before/after data-quality report.
* Designed a star schema (1 fact, 4 dimensions) and wrote 26 analytical SQL queries (CTEs, window functions, cohort-style repeat-customer analysis) plus 8 data-quality checks; reconciled SQL against an independent pandas calculation on 31 metrics.
* Produced an EDA notebook and business report identifying that 3 sub-categories lose money despite 28% of revenue, that one region earns a 11.6% margin against 20.5% elsewhere, and that lines discounted over 30% lose money - each recommendation stated with its metric and assumption.
* *(Add only after you build it)* Designed a 5-page interactive Power BI report with DAX time-intelligence, ranking and discount measures, validated against SQL KPIs.

Say "synthetic" in the project title or the first line of the README. Interviewers respect that; they penalise data presented as real.

## Interview questions and answers

**1. Why a star schema?** It separates what happened (the fact table, one row per order line) from the descriptions (customer, product, geography, date). BI tools filter dimensions and aggregate the fact, so measures stay correct and fast, and relationships are one-to-many.

**2. How did you count orders, and why not COUNT(*)?** `COUNT(DISTINCT order_id)`. An order has several lines, so `COUNT(*)` gives 8,679 lines instead of 3,895 orders and would inflate average order value by more than double.

**3. Why is profit margin total profit / total sales and not the average of line margins?** The average treats a USD 5 line like a USD 5,000 line. The weighted version is the margin of the business. In this data the two differ (a test proves it).

**4. How did you handle negative profit and returns?** I did not delete them. Losses are real outcomes and are the point of the profitability analysis. Returns (negative quantity and sales) stay and are flagged. Only provably invalid rows, such as quantity 0 with positive sales, were quarantined with a reason.

**5. What is the difference between quarantining and deleting?** Quarantined rows are written to a file with the reason, so nothing disappears silently and the row count reconciles: 8,747 raw = 8,679 clean + 23 quarantined + 45 duplicates.

**6. How did you find suspicious prices?** Implied list price = sales / (quantity x (1 - discount)). A line more than 5x its product's median is flagged. I kept them (a human must decide) and showed KPIs with and without: they hold 0.6% of revenue but 3.3% of profit. SQL used a leave-one-out average and found the same 6 lines.

**7. What does the discount analysis show, and can you say discounts cause lower profit?** Margin falls from 32% undiscounted and turns negative from the 21-30% discount band, and the pattern holds within sub-categories. But it is observational: no volume counterfactual, discounts are not random, and this data is synthetic with fixed costs, so the mechanism is built in. I would recommend a controlled price test before acting.

**8. How would you prove SQL and Power BI agree?** Compute expected KPIs independently (`expected_kpis.csv`), then compare each Power BI card under several slicer states. A difference means a DAX or model error, because the underlying data is the same.

**9. Explain `ALLSELECTED` in Revenue Contribution %.** It removes the filters coming from the visual's own rows but keeps slicers, so each region's share is of what the user currently selected rather than of the whole company.

**10. How do you avoid double counting in Power BI?** One-to-many relationships, single-direction filtering, no bi-directional links, a complete date table, and `DISTINCTCOUNT` for orders. SQL check `dq04` proves the joins do not change revenue.

**11. What would you do with real data that you could not do here?** Verify the source and licence, compare to the finance system, get a cost field, check returns reasons, and run the cleaning rules against real error patterns instead of planted ones.

**12. What are the limits of this project?** Synthetic data; SQL verified on SQLite not PostgreSQL; Power BI report is specified but not built in this repo; no cost data; four years of one country.

**13. Window functions: how did you compute month-over-month growth?** `LAG(revenue) OVER (ORDER BY year_month)`. It is only valid if no month is missing, so a check (`dq07`) proves every month in range has orders.

**14. Which finding would you present first to a manager?** Three sub-categories (Tables, Bookcases, Machines) bring 27.8% of revenue and lose USD 70,422, driven largely by deep discounts, while revenue rankings alone make them look healthy.
