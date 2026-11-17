"""Re-run every experiment notebook in order and refresh the website data.

    python -m src.run_all            # notebooks 04-10 + website export (~45-60 min on a laptop)
    python -m src.run_all --from 06  # resume from a later notebook

Notebooks 01-03 are the original audit/EDA/baseline work and are not re-executed.
"""
import argparse, subprocess, sys
from .config import ROOT

# 04-09 use train/validation only; 10 is the single held-out test evaluation and runs last.
NOTEBOOKS = ["04_tfidf_regularised_models", "05_pca_and_svm", "06_shortcut_analysis",
             "07_thresholds_calibration", "08_representations_imbalance_groups",
             "09_proposal_items", "10_final_test_evaluation"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="start", default="04")
    start = ap.parse_args().start
    for nb in NOTEBOOKS:
        if nb[:2] < start:
            continue
        print(f"==> executing {nb}.ipynb", flush=True)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                        "--inplace", "--ExecutePreprocessor.timeout=3600",
                        str(ROOT / "notebooks" / f"{nb}.ipynb")], check=True)
    subprocess.run([sys.executable, "-m", "src.export_web"], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
