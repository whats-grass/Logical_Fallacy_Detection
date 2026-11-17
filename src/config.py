"""Single place for paths, seeds and the pre-declared evaluation protocol."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "logical_fallacy_dataset.xlsx"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
WEB_DATA = ROOT / "website" / "data"
PROCESSED = ROOT / "data" / "processed"

SEED = 42
META_COLS = ["id", "argument", "fallacies", "num_fallacies", "split"]

# Pre-declared protocol (written before any test-set evaluation):
#   * model fitting      -> official `train` split only
#   * model selection    -> official `val` split, primary metric = macro-F1
#   * final evaluation   -> official `test` split, run ONCE in notebook 08
#   * near-duplicate cut -> max cosine similarity to any train row, TF-IDF fitted on train only
PRIMARY_METRIC = "macro_f1"
NEAR_DUP_HIGH = 0.80   # "template-seen" bucket
NEAR_DUP_LOW = 0.50    # "novel" bucket
