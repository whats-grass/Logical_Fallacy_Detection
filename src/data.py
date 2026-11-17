"""Dataset loading. Rows = one argument; targets = 16 binary fallacy indicators."""
import pandas as pd
from .config import DATA_PATH, META_COLS


def load_dataset(path=DATA_PATH):
    df = pd.read_excel(path, sheet_name="Dataset")
    label_cols = [c for c in df.columns if c not in META_COLS]
    assert len(label_cols) == 16, label_cols
    assert (df[label_cols].sum(axis=1) == df["num_fallacies"]).all()
    return df, label_cols


def get_splits(df, label_cols):
    out = {}
    for s in ["train", "val", "test"]:
        part = df[df["split"] == s].reset_index(drop=True)
        out[s] = (part["argument"], part[label_cols].values.astype(int), part)
    return out
