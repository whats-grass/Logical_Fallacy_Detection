"""Single place for paths, seeds and the pre-declared evaluation protocol."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "logical_fallacy_dataset.xlsx"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
WEB_DATA = ROOT / "website" / "data"
PROCESSED = ROOT / "data" / "processed"
EXTERNAL = ROOT / "data" / "raw" / "external"

SEED = 42
META_COLS = ["id", "argument", "fallacies", "num_fallacies", "split"]

# Pre-declared protocol (written before any test-set evaluation):
#   * model fitting      -> official `train` split only
#   * model selection    -> official `val` split, primary metric = macro-F1
#   * final evaluation   -> official `test` split, run ONCE in notebook 10
#   * near-duplicate cut -> max cosine similarity to any train row, TF-IDF fitted on train only
PRIMARY_METRIC = "macro_f1"
NEAR_DUP_HIGH = 0.80   # "template-seen" bucket
NEAR_DUP_LOW = 0.50    # "novel" bucket

# External data (notebooks 11-12), declared before any model touched it:
#   * notebook 11 evaluates the FROZEN models of results/selection.json, trained on the
#     main train split only, on two out-of-distribution sources; nothing is tuned on them.
#   * notebook 12 (fallacy vs valid): deterministic 70/15/15 split by a hash of a GROUP id
#     (contrastive pair, or near-duplicate cluster for the online comments); C tuned on val,
#     test evaluated once at the end.
#   * notebook 13 trains one 16-label model on main + edu + comments (same splits; edu split by
#     a hash of its near-duplicate cluster); configuration chosen on pooled validation.
EXT_SPLIT = (0.70, 0.15)       # train share, val share; rest = test
