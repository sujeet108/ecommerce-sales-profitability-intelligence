"""
Build a local SQLite copy of the star schema and run the project's SQL files against it.
(SQLite is used because it needs no server; the SQL files are written to be portable to PostgreSQL.)

  python src/sql_runner.py            # build DB, run data_quality_checks.sql + business_analysis.sql
Results -> reports/sql_results/<query_name>.csv ; database -> data/processed/ecommerce.db
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/ecommerce.db"
STAR = ROOT / "data/processed/star"
OUT = ROOT / "reports/sql_results"
TABLES = ["dim_customer", "dim_product", "dim_geography", "dim_date", "fact_sales"]


def build_db() -> sqlite3.Connection:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((ROOT / "sql/schema.sql").read_text())
    for t in TABLES:
        df = pd.read_csv(STAR / f"{t}.csv", dtype={"postal_code": str})
        df = df.astype(object).where(df.notna(), None)
        cols = ",".join(df.columns)
        con.executemany(f"INSERT INTO {t} ({cols}) VALUES ({','.join('?' * len(df.columns))})", df.values.tolist())
    con.commit()
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    assert not bad, f"foreign key violations: {bad[:3]}"
    return con


def run_file(con, sql_file: Path, prefix: str) -> dict[str, pd.DataFrame]:
    """Split a .sql file on '-- @query <name>' markers and run each statement."""
    text = sql_file.read_text()
    parts = re.split(r"^-- @query\s+(\S+)\s*$", text, flags=re.M)[1:]
    results = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in zip(parts[::2], parts[1::2]):
        df = pd.read_sql_query(body.strip().rstrip(";"), con)
        results[name] = df
        df.to_csv(OUT / f"{prefix}_{name}.csv", index=False)
    return results


def main():
    con = build_db()
    for t in TABLES:
        print(f"{t:14s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7,} rows")
    qc = run_file(con, ROOT / "sql/data_quality_checks.sql", "dq")
    ba = run_file(con, ROOT / "sql/business_analysis.sql", "q")
    print(f"ran {len(qc)} data-quality checks and {len(ba)} analysis queries")
    return con, qc, ba


if __name__ == "__main__":
    main()
