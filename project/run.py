"""One command to run the whole project.

    python run.py              full run: check, pipeline, notebook, report
    python run.py --quick      pipeline only, skips the notebook (about 3 seconds)
    python run.py --serve      full run, then start the API on port 5055
    python run.py --check      verify the environment and exit, changes nothing
    python run.py --refit      refit the regime model instead of loading the saved one

Written so that someone who has never seen this repo can clone it, install the
requirements, and get every result with one command. Each stage prints what it is
doing and fails with a message that says what to do about it.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

REQUIRED = [
    "numpy", "pandas", "scipy", "sklearn", "statsmodels", "hmmlearn",
    "yfinance", "matplotlib", "seaborn", "pyarrow", "dotenv", "joblib",
]
NOTEBOOK = ROOT / "notebooks" / "project_pipeline.ipynb"

BAR = "=" * 68


def say(msg: str) -> None:
    print(f"\n{BAR}\n  {msg}\n{BAR}", flush=True)


def check_environment() -> None:
    """Confirm the interpreter and every dependency before doing any work."""
    say("1. environment")
    print(f"  python     {sys.version.split()[0]}")
    print(f"  executable {sys.executable}")

    if sys.version_info < (3, 10):
        raise SystemExit(
            "\n  Python 3.10 or newer is required.\n"
            "  conda create -n fe-course python=3.11 -y && conda activate fe-course"
        )

    missing = []
    for mod in REQUIRED:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        raise SystemExit(
            f"\n  Missing packages: {', '.join(missing)}\n"
            "  Fix with:  pip install -r requirements.txt\n\n"
            "  If pandas is the one failing to import, it is almost certainly a\n"
            "  numpy 2.x against pandas 1.x binary incompatibility. The pinned\n"
            "  versions in requirements.txt are chosen to avoid exactly that."
        )
    print(f"  packages   all {len(REQUIRED)} present")

    if not (ROOT / ".env").exists():
        print("  .env       not found, falling back to config defaults (fine)")
    else:
        print("  .env       found")


def run_pipeline_stage(refit: bool) -> dict:
    """The analysis itself. This is the part that produces every number."""
    say("2. pipeline")
    from src.pipeline import latest_reading, run_pipeline

    started = time.perf_counter()
    result = run_pipeline(refit=refit, save=True)
    reading = latest_reading(result)
    print(f"  completed in {time.perf_counter() - started:.1f}s")

    print("\n  current reading")
    for key in ("as_of", "pair", "correlation", "percentile_vs_history",
                "flagged", "regime", "diversification_ratio"):
        print(f"    {key:24s} {reading[key]}")

    metrics = result["metrics"]
    print("\n  detection against the labelled crisis windows")
    for key in ("precision", "recall", "f1"):
        print(f"    {key:24s} {metrics[key]:.4f}")
    print("    (low by design: see docs/methodology_notes.md, two of the three")
    print("     labelled windows are not diversification breakdowns)")
    return reading


def run_notebook_stage() -> None:
    """Execute the notebook in place, which also regenerates every figure."""
    say("3. notebook")
    if not NOTEBOOK.exists():
        raise SystemExit(f"  notebook not found at {NOTEBOOK}")

    print(f"  executing {NOTEBOOK.name} (about a minute)")
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
         "--execute", "--inplace", NOTEBOOK.name],
        cwd=NOTEBOOK.parent, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
        print("\n".join("  " + line for line in tail))
        raise SystemExit("  notebook failed, see the traceback above")
    print(f"  completed in {time.perf_counter() - started:.1f}s, 0 errors")


def export_stage() -> None:
    """Export the executed notebook so it can be read without Python."""
    say("4. report")
    proc = subprocess.run(
        [sys.executable, "-m", "jupyter", "nbconvert", "--to", "html",
         "--output-dir", str(ROOT / "reports"), str(NOTEBOOK)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("  html export failed, continuing anyway")
    else:
        print(f"  wrote reports/{NOTEBOOK.stem}.html")

    for rel in ("reports/final_report.md", "reports/images/annual_hedge_and_dr.png",
                "data/processed/annual_summary.csv", "model/regime_hmm.pkl"):
        mark = "ok  " if (ROOT / rel).exists() else "MISS"
        print(f"  [{mark}] {rel}")


def serve_stage() -> None:
    say("5. dashboard")
    print("  open  http://127.0.0.1:5055")
    print()
    print("  /            dashboard: regime, chart, annual table")
    print("  /report      the risk memo")
    print("  /notebook    the full executed notebook")
    print("  /reading     the same numbers as JSON")
    print()
    print("  stop with Ctrl+C\n")
    subprocess.run([sys.executable, str(ROOT / "app.py")], cwd=ROOT)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Run the Cross-Asset Diversification Breakdown Monitor.")
    p.add_argument("--quick", action="store_true",
                   help="pipeline only, skip the notebook and export")
    p.add_argument("--serve", action="store_true",
                   help="start the API after running")
    p.add_argument("--check", action="store_true",
                   help="verify the environment and exit")
    p.add_argument("--refit", action="store_true",
                   help="refit the regime model rather than loading the saved one")
    args = p.parse_args()

    overall = time.perf_counter()
    print(f"\n  Cross-Asset Diversification Breakdown Monitor")
    print(f"  working from {ROOT}")

    check_environment()
    if args.check:
        print("\n  environment is fine. Run `python run.py` to do the actual work.\n")
        return 0

    run_pipeline_stage(refit=args.refit)

    if not args.quick:
        run_notebook_stage()
        export_stage()

    say(f"done in {time.perf_counter() - overall:.0f}s")
    print("  read next:")
    print("    reports/final_report.md          the memo, start here")
    print("    reports/project_pipeline.html    every cell with its output")
    print("    docs/project_summary.md          the non-technical version")
    print("    docs/methodology_notes.md        why the statistics are calibrated this way")

    if args.serve:
        serve_stage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
