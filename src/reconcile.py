"""
Reconcile SQL results (computed on the star schema in SQLite) against an INDEPENDENT pandas
calculation done on the flat clean CSV. Also writes the expected KPI values to check Power BI against.

  python src/reconcile.py   -> reports/reconciliation_report.md, powerbi/expected_kpis.csv
Exit code 1 if any check fails.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "reports/sql_results"
TOL = 0.011   # SQL rounds to 2 decimals


def sql(name: str, prefix: str = "q") -> pd.DataFrame:
    return pd.read_csv(RES / f"{prefix}_{name}.csv")


def discount_band(d: pd.Series) -> pd.Series:
    return pd.Series(np.select([d == 0, d <= .10, d <= .20, d <= .30, d <= .50],
                               ["0. No discount", "1. Up to 10%", "2. 11-20%", "3. 21-30%", "4. 31-50%"],
                               default="5. Over 50%"), index=d.index)


def reconcile() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data/processed/superstore_clean.csv", parse_dates=["order_date"])
    rows = []

    def check(name, sql_v, py_v, tol=TOL):
        if isinstance(sql_v, (list, tuple, np.ndarray)) or isinstance(py_v, (list, tuple, np.ndarray)):
            ok = list(sql_v) == list(py_v); diff = "" if ok else "lists differ"
            rows.append([name, str(sql_v)[:60], str(py_v)[:60], diff, "PASS" if ok else "FAIL"]); return
        diff = abs(float(sql_v) - float(py_v)); ok = diff <= tol
        rows.append([name, f"{float(sql_v):,.2f}", f"{float(py_v):,.2f}", f"{diff:.4f}", "PASS" if ok else "FAIL"])

    # --- headline KPIs
    revenue, profit = df.sales.sum(), df.profit.sum()
    orders = df.order_id.nunique()
    check("Total revenue", sql("Q01_total_revenue_profit").total_revenue[0], revenue)
    check("Total profit", sql("Q01_total_revenue_profit").total_profit[0], profit)
    check("Total orders (distinct Order ID)", sql("Q02_orders_and_units").total_orders[0], orders, 0)
    check("Units sold (net of returns)", sql("Q02_orders_and_units").units_sold[0], df.quantity.sum(), 0)
    check("Order lines", sql("Q02_orders_and_units").order_lines[0], len(df), 0)
    check("Average order value", sql("Q03_average_order_value").average_order_value[0], revenue / orders)
    check("Profit margin % (weighted)", sql("Q04_profit_margin").profit_margin_pct[0], 100 * profit / revenue)

    # --- trends
    y = df.groupby(df.order_date.dt.year).agg(r=("sales", "sum"), p=("profit", "sum"))
    s = sql("Q05b_yearly_trend").set_index("year")
    check("Yearly revenue (max abs diff, 4 yrs)", (s.revenue - y.r).abs().max(), 0)
    check("Yearly profit (max abs diff, 4 yrs)", (s.profit - y.p).abs().max(), 0)
    m = df.groupby(df.order_date.dt.strftime("%Y-%m")).sales.sum()
    sm = sql("Q05a_monthly_trend").set_index("year_month")
    check("Monthly revenue (max abs diff, 48 months)", (sm.revenue - m).abs().max(), 0)
    mom = sql("Q06_month_over_month_growth").set_index("year_month").mom_growth_pct
    check("MoM growth, Mar-2022", mom["2022-03"], 100 * (m["2022-03"] / m["2022-02"] - 1))
    check("YoY growth 2025 %", s.loc[2025, "yoy_revenue_growth_pct"], 100 * (y.r[2025] / y.r[2024] - 1))
    check("Running total ends at total revenue", sql("Q16a_running_total_revenue").running_total_all_time.iloc[-1], revenue)

    # --- products
    pr = df.groupby("product_id").agg(r=("sales", "sum"), p=("profit", "sum")).reset_index()
    t = pr.sort_values(["r", "product_id"], ascending=[False, True]).head(10)
    check("Top-10 products by revenue (same IDs, same order)", list(sql("Q07_top10_products_by_revenue").product_id), list(t.product_id))
    check("Top-10 revenue: sum of revenue", sql("Q07_top10_products_by_revenue").revenue.sum(), t.r.sum())
    t = pr.sort_values(["p", "product_id"], ascending=[False, True]).head(10)
    check("Top-10 products by profit (same IDs, same order)", list(sql("Q08_top10_products_by_profit").product_id), list(t.product_id))
    loss = pr[pr.p < 0]
    check("Loss-making products: count", len(sql("Q09a_loss_making_products")), len(loss), 0)
    check("Loss-making products: total loss", sql("Q09a_loss_making_products").profit.sum(), loss.p.sum())

    # --- geography / category / segment
    rg = df.groupby("region").agg(r=("sales", "sum"), p=("profit", "sum"))
    sr = sql("Q10a_region_performance").set_index("region")
    check("Region revenue (max abs diff)", (sr.revenue - rg.r).abs().max(), 0)
    check("Region profit (max abs diff)", (sr.profit - rg.p).abs().max(), 0)
    check("Cities in Q10b", len(sql("Q10b_city_performance")), df.groupby(["city", "state"]).ngroups, 0)
    sc = df.groupby(["category", "sub_category"]).profit.sum()
    ss = sql("Q11_category_subcategory_profitability").set_index(["category", "sub_category"]).profit
    check("Sub-category profit (max abs diff, 17)", (ss - sc).abs().max(), 0)
    sg = df.groupby("segment").sales.sum(); ssg = sql("Q12_customer_segment").set_index("segment").revenue
    check("Segment revenue (max abs diff)", (ssg - sg).abs().max(), 0)

    # --- discount & shipping
    nr = df[df.is_return == 0]
    nr = nr.assign(band=discount_band(nr.discount)).groupby("band").agg(r=("sales", "sum"), p=("profit", "sum"), n=("sales", "size"))
    sd = sql("Q13a_discount_band_profitability").set_index("discount_band")
    check("Discount-band revenue (max abs diff)", (sd.revenue - nr.r).abs().max(), 0)
    check("Discount-band profit (max abs diff)", (sd.profit - nr.p).abs().max(), 0)
    check("Discount-band line counts (max abs diff)", (sd.lines - nr.n).abs().max(), 0)
    sh = df.groupby("ship_mode").order_id.nunique(); ssh = sql("Q14_shipping_mode_performance").set_index("ship_mode").orders
    check("Orders by ship mode (max abs diff)", (ssh - sh).abs().max(), 0)
    check("Avg ship days, Standard Class", sql("Q14_shipping_mode_performance").set_index("ship_mode").avg_ship_days["Standard Class"],
          df[df.ship_mode == "Standard Class"].ship_days.mean())

    # --- customers
    oc = df.groupby("customer_id").order_id.nunique()
    py_counts = [int((oc == 1).sum()), int(oc.between(2, 4).sum()), int((oc >= 5).sum())]
    check("Repeat-customer buckets (1 / 2-4 / 5+)", list(sql("Q15a_repeat_customers").customers), py_counts)
    check("Distinct customers", sql("Q15a_repeat_customers").customers.sum(), df.customer_id.nunique(), 0)

    # --- anomalies
    check("Unit-price outliers: SQL (leave-one-out) vs cleaning flag, same row IDs",
          sorted(sql("Q17a_unusual_unit_price").row_id), sorted(df.loc[df.is_price_outlier == 1, "row_id"]))
    return pd.DataFrame(rows, columns=["check", "SQL result", "pandas result", "abs diff", "status"])


def expected_kpis(df: pd.DataFrame) -> pd.DataFrame:
    def kp(d, label):
        rev, pro = d.sales.sum(), d.profit.sum()
        return {"filter_context": label, "total_revenue": round(rev, 2), "total_profit": round(pro, 2),
                "profit_margin_pct": round(100 * pro / rev, 2), "total_orders": d.order_id.nunique(),
                "units_sold": int(d.quantity.sum()), "avg_order_value": round(rev / d.order_id.nunique(), 2)}
    rows = [kp(df, "All data")]
    rows += [kp(df[df.order_date.dt.year == y], f"Year = {y}") for y in sorted(df.order_date.dt.year.unique())]
    rows += [kp(df[df.region == r], f"Region = {r}") for r in ["West", "South", "East", "Central"]]
    rows += [kp(df[df.category == c], f"Category = {c}") for c in sorted(df.category.unique())]
    rows += [kp(df[df.is_price_outlier == 0], "Excluding 6 flagged price outliers")]
    return pd.DataFrame(rows)


def main() -> int:
    res = reconcile()
    df = pd.read_csv(ROOT / "data/processed/superstore_clean.csv", parse_dates=["order_date"])
    kp = expected_kpis(df)
    (ROOT / "powerbi").mkdir(exist_ok=True)
    kp.to_csv(ROOT / "powerbi/expected_kpis.csv", index=False)
    n_fail = int((res.status == "FAIL").sum())
    md = ["# SQL-to-Python Reconciliation Report\n",
          "SQL results come from `sql/business_analysis.sql` run on the star schema (SQLite). The pandas values are computed "
          "separately from `data/processed/superstore_clean.csv` and do not use the SQL files or the star schema.\n",
          f"**Result: {len(res) - n_fail} of {len(res)} checks PASS.**\n",
          "| " + " | ".join(res.columns) + " |\n|" + "---|" * 5 + "\n" +
          "\n".join("| " + " | ".join(map(str, r)) + " |" for r in res.itertuples(index=False)),
          "\n\n## Expected KPI values for Power BI\n",
          "Build the report, then clear all slicers and compare each card with the first row below; apply one slicer at a time and compare "
          "with the other rows. These numbers come from the same clean data, so a difference means a modelling or DAX error in Power BI.\n",
          kp.to_markdown(index=False) if hasattr(kp, "to_markdown") and _has_tabulate() else _md(kp)]
    (ROOT / "reports/reconciliation_report.md").write_text("\n".join(md), encoding="utf-8")
    print(res.to_string(index=False)); print(f"\n{len(res) - n_fail}/{len(res)} PASS")
    return 1 if n_fail else 0


def _has_tabulate():
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


def _md(d: pd.DataFrame) -> str:
    return "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns) + "\n" + "\n".join(
        "| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False))


if __name__ == "__main__":
    sys.exit(main())
