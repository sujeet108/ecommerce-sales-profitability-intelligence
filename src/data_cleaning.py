"""
Clean the raw sales file and write:
  data/processed/superstore_clean.csv      accepted rows (+ helper flag columns)
  data/processed/rejected_rows.csv         quarantined rows with a reject reason (nothing is silently deleted)
  reports/data_quality_report.md           issues found, actions, before/after validation

Usage:  python src/data_cleaning.py
Design rules: never delete legitimate returns or loss-making sales; never invent values;
quarantine what is provably invalid; flag (but keep) what is merely suspicious.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from data_validation import run_checks

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("RAW_CSV", ROOT / "data/raw/superstore_synthetic_raw.csv"))   # set RAW_CSV to use another file
ENCODING = os.environ.get("RAW_ENCODING", "utf-8")                                        # real Superstore copies often need latin-1
MANIFEST = ROOT / "data/raw/injected_issues.json"
OUT_DIR = ROOT / "data/processed"
REPORT = ROOT / "reports/data_quality_report.md"

COLS = {"Row ID": "row_id", "Order ID": "order_id", "Order Date": "order_date", "Ship Date": "ship_date",
        "Ship Mode": "ship_mode", "Customer ID": "customer_id", "Customer Name": "customer_name",
        "Segment": "segment", "Country": "country", "City": "city", "State": "state",
        "Postal Code": "postal_code", "Region": "region", "Product ID": "product_id", "Category": "category",
        "Sub-Category": "sub_category", "Product Name": "product_name", "Sales": "sales",
        "Quantity": "quantity", "Discount": "discount", "Profit": "profit"}
CANON = {
    "region": ["West", "East", "Central", "South"],
    "segment": ["Consumer", "Corporate", "Home Office"],
    "ship_mode": ["Standard Class", "Second Class", "First Class", "Same Day"],
    "category": ["Furniture", "Office Supplies", "Technology"],
    "sub_category": ["Bookcases", "Chairs", "Furnishings", "Tables", "Appliances", "Art", "Binders", "Envelopes",
                     "Fasteners", "Labels", "Paper", "Storage", "Supplies", "Accessories", "Copiers", "Machines",
                     "Phones"],
    "country": ["United States"],
}
ALIASES = {"category": {"furnitures": "Furniture"}, "country": {"us": "United States", "usa": "United States"}}
DATE_FORMATS = ["%Y-%m-%d", "%d-%b-%Y", "%m/%d/%Y"]


def squash(s: pd.Series) -> pd.Series:
    return s.astype("object").where(s.isna(), s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True))


def parse_dates(s: pd.Series) -> pd.Series:
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(s, format=fmt, errors="coerce").astype("datetime64[ns]")
        out = out.fillna(parsed)
    return out


def load_typed_raw(path: Path = RAW) -> pd.DataFrame:
    """Read everything as text, rename columns, convert types naively (no repair). Used for the BEFORE checks."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding=ENCODING)
    df = raw.rename(columns=COLS)
    for c in ["sales", "quantity", "discount", "profit", "row_id"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["order_date", "ship_date"]:
        df[c] = pd.to_datetime(df[c], format="%Y-%m-%d", errors="coerce").astype("datetime64[ns]")  # naive: one format only
    return df


def clean(path: Path = RAW):
    log = []  # one dict per issue

    def note(issue, found, action, rows_after):
        log.append({"issue": issue, "rows_found": int(found), "action": action, "rows_after_step": int(rows_after)})

    raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding=ENCODING)
    df = raw.rename(columns=COLS).copy()
    note("Raw file loaded", len(df), "Read every column as text so nothing is silently converted", len(df))

    # 1. numeric conversion
    for c in ["sales", "quantity", "discount", "profit", "row_id"]:
        before = df[c].notna().sum()
        df[c] = pd.to_numeric(df[c], errors="coerce")
        bad = before - df[c].notna().sum()
        if bad: note(f"Non-numeric values in {c}", bad, "Converted to missing and sent to quarantine", len(df))
    df["quantity"] = df["quantity"].astype("Int64")

    # 2. text standardisation (trim, collapse spaces, canonical case, known aliases)
    total_changed = 0
    for c in df.columns:
        if df[c].dtype == object or str(df[c].dtype).startswith("str"):
            df[c] = squash(df[c])
    for col, canon in CANON.items():
        lookup = {v.lower(): v for v in canon}; lookup.update(ALIASES.get(col, {}))
        mapped = df[col].str.lower().map(lookup)
        changed = (mapped.notna() & (mapped != df[col])).sum()
        unmapped = (df[col].notna() & mapped.isna()).sum()
        df[col] = mapped.fillna(df[col]); total_changed += changed
        note(f"Inconsistent text in {col}", changed, f"Mapped to canonical spelling ({unmapped} values could not be mapped)", len(df))

    # 3. dates (two formats present)
    n_iso = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce").notna().sum()
    df["order_date"], df["ship_date"] = parse_dates(df["order_date"]), parse_dates(df["ship_date"])
    note("Mixed date formats (YYYY-MM-DD and DD-Mon-YYYY)", df["order_date"].notna().sum() - n_iso,
         "Parsed each format explicitly; no dates left unparseable" if df["order_date"].isna().sum() == 0
         else f"{df['order_date'].isna().sum()} order dates still unparseable -> quarantine", len(df))

    # 4. exact duplicates
    n0 = len(df); df = df.drop_duplicates().reset_index(drop=True)
    note("Exact duplicate rows", n0 - len(df), "Dropped extra copies, kept the first", len(df))
    conflicts = df["row_id"].duplicated().sum()
    note("Same Row ID but different values", conflicts, "None found" if conflicts == 0 else "Needs manual review", len(df))

    # 5. validity rules -> quarantine (returns are legitimate and stay)
    q, s, d = df["quantity"].astype(float), df["sales"], df["discount"]
    df["is_return"] = ((q < 0) & (s < 0)).astype(int)
    ret = df["is_return"] == 1
    reason = np.select(
        [df[["order_date", "sales", "quantity", "discount", "profit"]].isna().any(axis=1),
         (q <= 0) & ~ret, (s <= 0) & ~ret, (d < 0) | (d > 1)],
        ["missing or non-numeric key field", "quantity <= 0 without matching negative sales (not a return)",
         "sales <= 0 on a positive quantity", "discount outside 0-1 (possible percent entry error)"], default="")
    rej = df[reason != ""].assign(reject_reason=reason[reason != ""])
    for r, k in rej["reject_reason"].value_counts().items():
        note(f"Invalid record: {r}", k, "Moved to rejected_rows.csv (not deleted silently)", len(df) - len(rej))
    df = df[reason == ""].reset_index(drop=True)
    note("Legitimate returns (negative quantity, sales and profit)", df["is_return"].sum(),
         "Kept and flagged is_return = 1; they reduce net revenue", len(df))
    neg_profit = ((df["profit"] < 0) & (df["is_return"] == 0)).sum()
    note("Loss-making sales lines (profit < 0, not returns)", neg_profit,
         "Kept - real business outcomes, analysed in the profitability pages", len(df))

    # 6. ship date sanity
    bad_ship = df["ship_date"] < df["order_date"]
    df["ship_date_invalid"] = bad_ship.astype(int)
    df.loc[bad_ship, "ship_date"] = pd.NaT
    note("Ship date earlier than order date", bad_ship.sum(),
         "Ship date set to missing and flagged (sales kept; excluded from shipping-time analysis)", len(df))
    df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days

    # 7. missing values that can be recovered from the data itself
    names = df.dropna(subset=["customer_name"]).groupby("customer_id")["customer_name"].agg(lambda x: x.mode().iat[0])
    miss = df["customer_name"].isna()
    df["customer_name"] = df["customer_name"].fillna(df["customer_id"].map(names)).fillna("Unknown")
    note("Missing customer name", miss.sum(), "Filled from the same Customer ID's other rows; else 'Unknown'", len(df))
    pc = df["postal_code"].str.replace(r"\.0$", "", regex=True)
    short = pc.notna() & pc.str.fullmatch(r"\d{1,4}")
    pc = pc.where(~short, pc.str.zfill(5))
    note("Postal code lost its leading zero", short.sum(), "Left-padded to 5 digits (stored as text)", len(df))
    miss_pc = pc.isna()
    df["postal_code"] = pc.fillna("Unknown")
    note("Missing postal code", miss_pc.sum(), "Not guessable (a city has several ZIPs) -> 'Unknown'", len(df))

    # 8. consistency of keys
    for key, cols in [("customer_id", ["segment"]), ("product_id", ["product_name", "category", "sub_category"])]:
        bad = sum((df.groupby(key)[c].nunique() > 1).sum() for c in cols)
        note(f"{key} mapping to more than one {'/'.join(cols)}", bad, "None found" if bad == 0 else "Needs review", len(df))
    bad = (df.groupby("city")["state"].nunique() > 1).sum() + (df.groupby("state")["region"].nunique() > 1).sum()
    note("City->State or State->Region conflicts", bad, "None found" if bad == 0 else "Needs review", len(df))

    # 9. suspicious prices (flag, don't delete)
    sale = df["is_return"] == 0
    unit_list = (df["sales"] / (df["quantity"].astype(float) * (1 - df["discount"]))).where(sale)
    ratio = unit_list / unit_list.groupby(df["product_id"]).transform("median")
    df["is_price_outlier"] = (ratio > 5).fillna(False).astype(int)
    note("Implied list price > 5x the product's median (possible keying error)", df["is_price_outlier"].sum(),
         "Kept but flagged is_price_outlier = 1; KPI impact quantified below", len(df))

    # 10. derived columns
    df["year"], df["month"] = df["order_date"].dt.year, df["order_date"].dt.month
    df["profit_margin"] = (df["profit"] / df["sales"]).round(4)
    df["quantity"] = df["quantity"].astype(int)
    df["row_id"] = df["row_id"].astype(int)
    return df, rej, log


def md_table(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def write_report(raw_checks, clean_checks, log, df, rej, raw_rows):
    before = run_checks_pivot(raw_checks, clean_checks)
    k_all = df["sales"].sum(); k_ok = df.loc[df.is_price_outlier == 0, "sales"].sum()
    p_all = df["profit"].sum(); p_ok = df.loc[df.is_price_outlier == 0, "profit"].sum()
    parts = ["# Data Quality Report\n",
             "> **Dataset is synthetic** (generated by `src/generate_synthetic_data.py`, seed 42). Findings describe the data pipeline, not a real business.\n",
             "## 1. Row flow\n",
             md_table(pd.DataFrame([
                 ["Raw rows read", f"{raw_rows:,}"],
                 ["Exact duplicates removed", f"{raw_rows - len(df) - len(rej):,}"],
                 ["Quarantined (invalid)", f"{len(rej):,}"],
                 ["Clean rows exported", f"{len(df):,}"]], columns=["Step", "Rows"])),
             "## 2. Issues found and corrective actions\n", md_table(pd.DataFrame(log)),
             "## 3. Before / after validation\n",
             "`ISSUE` = rule violated by that many rows. `INFO` = informational, kept on purpose. "
             "After cleaning, remaining non-zero values are explained in section 5.\n", md_table(before)]
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text())
        found = {l["issue"]: l["rows_found"] for l in log}
        rows = [["Exact duplicate rows", m["exact_duplicate_rows"], found["Exact duplicate rows"]],
                ["Ship date before order date", m["ship_date_before_order_date"], found["Ship date earlier than order date"]],
                [f"Missing customer name (planted rows that were also quarantined: {int(rej.customer_name.isna().sum())})",
                 m["missing_customer_name"] - int(rej.customer_name.isna().sum()), found["Missing customer name"]],
                [f"Missing postal code (planted rows that were also quarantined: {int(rej.postal_code.isna().sum())})",
                 m["missing_postal_code"] - int(rej.postal_code.isna().sum()), found["Missing postal code"]],
                ["Price outliers (x40)", m["price_outliers_x40"], found["Implied list price > 5x the product's median (possible keying error)"]],
                ["Invalid quantity/sales/discount rows",
                 m["quantity_zero_with_positive_sales"] + m["quantity_negative_with_positive_sales"]
                 + m["sales_zero_with_positive_quantity"] + m["discount_gt_1_percent_entry_error"], len(rej)],
                ["Valid returns kept", m["valid_return_rows_planted"], int(df.is_return.sum())]]
        t = pd.DataFrame(rows, columns=["Planted problem (answer key)", "Planted", "Detected by cleaning code"])
        t["Match"] = np.where(t.iloc[:, 1] == t.iloc[:, 2], "yes", "NO - investigate")
        parts += ["## 4. Did the cleaning code find what was planted?\n",
                  "Because this dataset is synthetic, the generator wrote an answer key. A real dataset has no answer key, "
                  "so treat this section as a test of the pipeline, not as part of a normal report.\n", md_table(t)]
    parts += ["## 5. Residual items and impact\n",
              f"- **Price-outlier rows** kept but flagged: they hold {k_all - k_ok:,.2f} of {k_all:,.2f} total sales "
              f"({(k_all - k_ok) / k_all:.1%}) and {p_all - p_ok:,.2f} of {p_all:,.2f} total profit ({(p_all - p_ok) / p_all:.1%}). "
              "Power BI and SQL expose the flag so the analyst can show KPIs with and without them.\n",
              f"- **Ship date missing** on {int(df.ship_date_invalid.sum())} rows (invalid dates blanked, flagged `ship_date_invalid`).\n",
              f"- **Postal code 'Unknown'** on {int((df.postal_code == 'Unknown').sum())} rows.\n",
              "- **Quarantined rows** are in `data/processed/rejected_rows.csv` with the reason for each.\n",
              "- **Limitation:** the rules above detect what they were written to detect. Plausible-looking but wrong values "
              "(e.g. a wrong but valid product price within 5x of normal) cannot be found without a source system to compare against.\n"]
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text("\n".join(parts), encoding="utf-8")


def run_checks_pivot(raw_checks, clean_checks):
    m = raw_checks[["check", "rows_flagged"]].merge(clean_checks[["check", "rows_flagged", "status"]], on="check", suffixes=("_before", "_after"))
    m.columns = ["check", "before", "after", "status_after"]
    return m


def main():
    raw_typed = load_typed_raw()
    before = run_checks(raw_typed, "before")
    df, rej, log = clean()
    after = run_checks(df.assign(postal_code=df["postal_code"]), "after")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_cols = ["row_id", "order_id", "order_date", "ship_date", "ship_days", "ship_mode", "customer_id", "customer_name",
                "segment", "country", "state", "city", "postal_code", "region", "product_id", "product_name", "category",
                "sub_category", "sales", "quantity", "discount", "profit", "profit_margin", "year", "month",
                "is_return", "is_price_outlier", "ship_date_invalid"]
    df[out_cols].to_csv(OUT_DIR / "superstore_clean.csv", index=False, date_format="%Y-%m-%d")
    rej.to_csv(OUT_DIR / "rejected_rows.csv", index=False, date_format="%Y-%m-%d")
    write_report(before, after, log, df, rej, len(raw_typed))
    print(f"Clean rows: {len(df):,} | quarantined: {len(rej):,} | report: {REPORT}")
    print(after[after.status != "PASS"].to_string(index=False))


if __name__ == "__main__":
    main()
