"""
Split the clean flat file into a star schema (CSV files) for SQL and Power BI.

Grain of fact_sales: ONE ORDER LINE (one product on one order).
Output: data/processed/star/{dim_customer,dim_product,dim_geography,dim_date,fact_sales}.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed/superstore_clean.csv"
OUT = ROOT / "data/processed/star"


def build():
    df = pd.read_csv(SRC, dtype={"postal_code": str}, parse_dates=["order_date", "ship_date"])
    OUT.mkdir(parents=True, exist_ok=True)

    cust = df[["customer_id", "customer_name", "segment"]].drop_duplicates("customer_id").sort_values("customer_id")
    cust.insert(0, "customer_key", range(1, len(cust) + 1))
    prod = df[["product_id", "product_name", "category", "sub_category"]].drop_duplicates("product_id").sort_values("product_id")
    prod.insert(0, "product_key", range(1, len(prod) + 1))
    geo = df[["country", "state", "region", "city", "postal_code"]].drop_duplicates().sort_values(["region", "state", "city", "postal_code"])
    geo.insert(0, "geography_key", range(1, len(geo) + 1))

    # Calendar covers whole years so months without sales still exist (no "missing periods")
    start = pd.Timestamp(df.order_date.min().year, 1, 1)
    end = pd.Timestamp(max(df.order_date.max(), df.ship_date.max()).year, 12, 31)
    days = pd.date_range(start, end, freq="D")
    dim_date = pd.DataFrame({
        "date_key": days.strftime("%Y%m%d").astype(int), "full_date": days.strftime("%Y-%m-%d"),
        "year": days.year, "quarter": days.quarter, "month_num": days.month, "month_name": days.strftime("%B"),
        "year_month": days.strftime("%Y-%m"), "day_name": days.strftime("%A"),
        "is_weekend": (days.dayofweek >= 5).astype(int)})

    key = lambda s: s.dt.strftime("%Y%m%d").astype("Int64")
    fact = (df.merge(cust[["customer_key", "customer_id"]], on="customer_id")
              .merge(prod[["product_key", "product_id"]], on="product_id")
              .merge(geo[["geography_key", "country", "state", "city", "postal_code"]], on=["country", "state", "city", "postal_code"]))
    fact["order_date_key"], fact["ship_date_key"] = key(fact.order_date), key(fact.ship_date)
    fact["ship_days"] = fact["ship_days"].astype("Int64")   # integer text ("4", not "4.0") so PostgreSQL COPY accepts it
    fact = fact[["row_id", "order_id", "order_date_key", "ship_date_key", "ship_mode", "ship_days", "customer_key",
                 "product_key", "geography_key", "sales", "quantity", "discount", "profit",
                 "is_return", "is_price_outlier", "ship_date_invalid"]].sort_values("row_id")
    assert len(fact) == len(df), "a join duplicated or dropped rows"
    for name, t in [("dim_customer", cust), ("dim_product", prod), ("dim_geography", geo), ("dim_date", dim_date), ("fact_sales", fact)]:
        t.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:14s} {len(t):>7,} rows")


if __name__ == "__main__":
    build()
