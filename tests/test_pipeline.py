"""Automated checks. Run from the project root:  python tests/test_pipeline.py   (or: python -m pytest tests)"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CLEAN = ROOT / "data/processed/superstore_clean.csv"


def clean():
    return pd.read_csv(CLEAN, dtype={"postal_code": str}, parse_dates=["order_date"])


def test_row_id_unique_and_no_full_duplicates():
    df = clean(); assert df.row_id.is_unique and not df.duplicated().any()


def test_business_rules_hold():
    df = clean(); ret = df.is_return == 1
    assert ((df.discount >= 0) & (df.discount <= 1)).all()
    assert (df.loc[~ret, ["sales", "quantity"]] > 0).all().all()
    assert ((df.loc[ret, "quantity"] < 0) & (df.loc[ret, "sales"] < 0)).all()
    assert (df.postal_code.str.fullmatch(r"\d{5}") | (df.postal_code == "Unknown")).all()
    assert set(df.region) == {"West", "East", "Central", "South"}


def test_losses_and_returns_were_not_deleted():
    df = clean(); assert ((df.profit < 0) & (df.is_return == 0)).sum() > 0 and df.is_return.sum() > 0


def test_quarantine_accounts_for_every_raw_row():
    raw = pd.read_csv(ROOT / "data/raw/superstore_synthetic_raw.csv", dtype=str)
    rej = pd.read_csv(ROOT / "data/processed/rejected_rows.csv")
    n_dups = len(raw) - len(raw.drop_duplicates())
    assert len(raw) == len(clean()) + len(rej) + n_dups


def test_star_schema_integrity():
    db = ROOT / "data/processed/ecommerce.db"; con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0] == len(clean())
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert con.execute("SELECT COUNT(*) - COUNT(DISTINCT row_id) FROM fact_sales").fetchone()[0] == 0
    fan = con.execute("""SELECT ROUND(SUM(f.sales),2) FROM fact_sales f JOIN dim_customer c ON c.customer_key=f.customer_key
        JOIN dim_product p ON p.product_key=f.product_key JOIN dim_geography g ON g.geography_key=f.geography_key
        JOIN dim_date d ON d.date_key=f.order_date_key""").fetchone()[0]
    assert abs(fan - round(clean().sales.sum(), 2)) < 0.01, "join fan-out changed revenue"


def test_sql_matches_pandas():
    import reconcile
    res = reconcile.reconcile(); failed = res[res.status != "PASS"]
    assert failed.empty, failed.to_string()


def test_profit_margin_is_weighted_not_averaged():
    df = clean(); weighted = df.profit.sum() / df.sales.sum(); averaged = df.profit_margin.mean()
    assert abs(weighted - averaged) > 0.001   # proves the two definitions really differ on this data


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    bad = 0
    for n, f in tests:
        try: f(); print(f"PASS  {n}")
        except Exception as e: bad += 1; print(f"FAIL  {n}: {e}")
    print(f"\n{len(tests) - bad}/{len(tests)} passed"); sys.exit(1 if bad else 0)
