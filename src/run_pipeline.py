"""Run the whole pipeline in order:  python src/run_pipeline.py [--regenerate]
(The notebook is executed separately:  jupyter nbconvert --to notebook --execute --inplace notebooks/ecommerce_eda.ipynb)"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
STEPS = ["generate_synthetic_data.py", "data_cleaning.py", "build_star_schema.py", "sql_runner.py", "reconcile.py", "generate_insights.py"]
if "--regenerate" not in sys.argv:
    STEPS = STEPS[1:] if (SRC.parent / "data/raw/superstore_synthetic_raw.csv").exists() else STEPS
for s in STEPS:
    print(f"\n=== {s}")
    r = subprocess.run([sys.executable, str(SRC / s)])
    if r.returncode:
        sys.exit(f"step failed: {s}")
print("\nPipeline finished.")
