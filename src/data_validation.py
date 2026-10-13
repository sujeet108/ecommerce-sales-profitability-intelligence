"""
Reusable data-quality checks.

run_checks() takes a DataFrame with snake_case column names, numeric columns as
numbers and date columns as datetimes (NaT where unparseable) and returns one
row per check: how many rows violate it. Running it BEFORE and AFTER cleaning
gives the before/after validation table in the data-quality report.
"""
from __future__ import annotations

import pandas as pd

CANONICAL = {
    "region": {"West", "East", "Central", "South"},
    "segment": {"Consumer", "Corporate", "Home Office"},
    "ship_mode": {"Standard Class", "Second Class", "First Class", "Same Day"},
    "category": {"Furniture", "Office Supplies", "Technology"},
    "country": {"United States"},
}
CRITICAL_COLS = ["order_id", "order_date", "ship_date", "customer_id", "customer_name", "product_id",
                 "postal_code", "sales", "quantity", "discount", "profit"]


def run_checks(df: pd.DataFrame, stage: str) -> pd.DataFrame:
    rows = []

    def add(check: str, n: int, note: str = "", info: bool = False) -> None:
        status = "INFO" if info else ("PASS" if n == 0 else "ISSUE")
        rows.append({"stage": stage, "check": check, "rows_flagged": int(n), "status": status, "note": note})

    q, s, d = df["quantity"], df["sales"], df["discount"]
    is_return = (q < 0) & (s < 0)          # a legitimate return reverses quantity AND sales

    add("duplicate_full_rows", df.duplicated().sum(), "extra copies of identical rows")
    add("duplicate_row_id", df["row_id"].duplicated().sum(), "Row ID must be unique")
    for c in CRITICAL_COLS:
        if c in df:
            add(f"missing_{c}", df[c].isna().sum() + (df[c].astype(str).str.strip() == "").sum()
                if df[c].dtype == object or str(df[c].dtype).startswith("str") else df[c].isna().sum())
    add("ship_before_order", (df["ship_date"] < df["order_date"]).sum(), "ship date earlier than order date")
    add("quantity_nonpositive_not_a_return", ((q <= 0) & ~is_return).sum())
    add("sales_nonpositive_not_a_return", ((s <= 0) & ~is_return).sum())
    add("discount_outside_0_to_1", ((d < 0) | (d > 1)).sum(), "discount must be a fraction between 0 and 1")
    add("profit_greater_than_sales", ((df["profit"] > s) & (s > 0)).sum(), "impossible unless cost is negative")
    for c, allowed in CANONICAL.items():
        add(f"non_canonical_{c}", (~df[c].isin(allowed)).sum(), "case, spacing or alias differences")
    add("non_canonical_sub_category_or_typo", (df["sub_category"].astype(str) != df["sub_category"].astype(str).str.strip()).sum()
        + (df["sub_category"].astype(str).str.lower() == df["sub_category"].astype(str)).sum(), "whitespace / lowercase variants")
    pc = df["postal_code"].astype(str)
    add("postal_code_not_5_digits", (~pc.str.fullmatch(r"\d{5}") & (pc != "Unknown") & df["postal_code"].notna()).sum(),
        "leading zero lost or bad format ('Unknown' is an accepted placeholder)")
    add("customer_id_with_multiple_segments", (df.groupby("customer_id")["segment"].nunique() > 1).sum(), "counted in customers")
    add("product_id_with_multiple_categories", (df.groupby("product_id")["category"].nunique() > 1).sum(), "counted in products")
    add("valid_return_rows", is_return.sum(), "kept on purpose: negative qty, sales and profit", info=True)
    if "is_price_outlier" in df:
        add("price_outlier_rows_flagged", df["is_price_outlier"].sum(), "kept but flagged for review", info=True)
    return pd.DataFrame(rows)
