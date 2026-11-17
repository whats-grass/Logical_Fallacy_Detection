"""Export the small JSON files the static website needs (run after notebook 08).

    python -m src.export_web

Writes to website/data/. Only derived numbers and short test-set arguments from the dataset are
exported; no credentials or personal data are involved.
"""
import json, warnings
import numpy as np, pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC
from sklearn.metrics import precision_recall_curve

from .config import RESULTS, WEB_DATA, SEED, FIGURES
from .data import load_dataset, get_splits
from .features import word_tfidf
from .models import logreg
from .text import RHETORICAL_CUES, FUNCTION_WORDS
from .shortcuts import linear_coefs

warnings.filterwarnings("ignore")


def _clean(o):
    """Replace NaN/inf with None so the output is strict JSON (browsers reject NaN)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


def main():
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    df, LABELS = load_dataset()
    S = get_splits(df, LABELS)
    X_tr, Y_tr, _ = S["train"]; X_te, Y_te, te_df = S["test"]
    sel = json.loads((RESULTS / "selection.json").read_text())
    cw = lambda s: None if s in (None, "None") else "balanced"

    vec = word_tfidf(ngram_range=(1, 2)); A = vec.fit_transform(X_tr); T = vec.transform(X_te)
    vocab = vec.get_feature_names_out().tolist()

    # ---- 1. Lasso model for the perturbation inspector --------------------------------
    s1 = sel["LR-L1"]
    l1 = logreg("l1", s1["C"], cw(s1["class_weight"])).fit(A, Y_tr)
    W, b = linear_coefs(l1)
    coefs = {}
    for k, lab in enumerate(LABELS):
        nz = np.nonzero(W[k])[0]
        coefs[lab] = {"idx": nz.tolist(), "w": np.round(W[k, nz], 5).tolist()}
    model = {"labels": LABELS, "vocab": vocab, "idf": np.round(vec.idf_, 6).tolist(),
             "intercept": np.round(b, 6).tolist(), "coef": coefs, "config": s1,
             "cues": sorted(RHETORICAL_CUES), "function_words": sorted(FUNCTION_WORDS)}
    (WEB_DATA / "lasso_model.json").write_text(json.dumps(model, separators=(",", ":")))

    # reference probabilities so the JS implementation can be checked against Python
    P_l1 = l1.predict_proba(T)

    # ---- 2. Example arguments for the inspector ----------------------------------------
    preds = pd.read_csv(RESULTS / "test_predictions.csv")
    rng = np.random.default_rng(SEED)
    picks = set()
    for k, lab in enumerate(LABELS):                     # up to 8 per label
        idx = np.where(Y_te[:, k] == 1)[0]
        picks.update(rng.choice(idx, size=min(8, len(idx)), replace=False).tolist())
    wrong = np.where(preds.status.values != "correct")[0]
    picks.update(rng.choice(wrong, size=min(30, len(wrong)), replace=False).tolist())
    ex = []
    for i in sorted(picks):
        ex.append({"i": int(i), "text": X_te.iloc[i], "labels": te_df.fallacies.iloc[i].split("; "),
                   "bucket": preds.bucket.iloc[i], "max_sim": round(float(preds.max_sim.iloc[i]), 3),
                   "status": preds.status.iloc[i], "pred": preds.predicted.iloc[i], "py_prob": np.round(P_l1[i], 4).tolist()})
    (WEB_DATA / "examples.json").write_text(json.dumps(ex))

    # ---- 3. Calibrated SVM test probabilities for the threshold tool ------------------
    s = sel["LinearSVM"]
    cal = OneVsRestClassifier(CalibratedClassifierCV(
        LinearSVC(C=s["C"], class_weight=cw(s["class_weight"]), max_iter=20000),
        method="sigmoid", cv=5)).fit(A, Y_tr)
    P = cal.predict_proba(T)
    thr = {"labels": LABELS, "prob": np.round(P.T, 4).tolist(), "y": Y_te.T.astype(int).tolist(),
           "f1_threshold_val": [sel["thresholds"]["f1_tuned_on_val"][l] for l in LABELS]}
    (WEB_DATA / "threshold_data.json").write_text(json.dumps(thr, separators=(",", ":")))

    # ---- 4. Result tables --------------------------------------------------------------
    summary = json.loads((RESULTS / "test_summary.json").read_text())
    summary["val_shortcuts"] = json.loads((RESULTS / "shortcut_val.json").read_text())
    summary["selection"] = sel
    summary["val_grid_linear"] = pd.read_csv(RESULTS / "val_grid_linear.csv")[
        ["model", "family", "ngram", "penalty", "C", "class_weight", "macro_f1", "micro_f1", "nonzero_frac"]
    ].replace({np.nan: None}).to_dict("records")
    summary["val_grid_dense"] = pd.read_csv(RESULTS / "val_grid_dense.csv")[
        ["model", "family", "k", "C", "class_weight", "macro_f1", "micro_f1"]].replace({np.nan: None}).to_dict("records")
    # notebooks 08-09: script research questions and proposal items (train/val only)
    summary["q2"] = pd.read_csv(RESULTS / "val_q2_representations.csv").to_dict("records")
    summary["q4"] = pd.read_csv(RESULTS / "val_q4_imbalance.csv", index_col=0).reset_index(names="label").to_dict("records")
    summary["q6"] = pd.read_csv(RESULTS / "val_q6_group_cv.csv").to_dict("records")
    summary["q6_per_label"] = pd.read_csv(RESULTS / "val_q6_per_label.csv", index_col=0).reset_index(names="label").to_dict("records")
    summary["proposal"] = json.loads((RESULTS / "proposal_items_val.json").read_text())
    summary["split_prevalence"] = pd.read_csv(RESULTS / "split_prevalence.csv", index_col=0).reset_index(names="label").to_dict("records")
    split_counts = df.split.value_counts().to_dict()
    summary["data"] = {"n": int(len(df)), "splits": split_counts,
                       "label_counts": df[LABELS].sum().astype(int).to_dict(),
                       "labels_per_arg": df.num_fallacies.value_counts().sort_index().astype(int).to_dict(),
                       "word_count": df.argument.str.split().str.len().describe().round(1).to_dict()}
    (WEB_DATA / "results.json").write_text(json.dumps(_clean(summary), indent=1, allow_nan=False))
    # figures used by the site
    import shutil
    fig_dir = WEB_DATA.parent / "figures"; fig_dir.mkdir(exist_ok=True)
    for f in FIGURES.glob("*.png"):
        shutil.copy2(f, fig_dir / f.name)
    print("exported to", WEB_DATA, "and", fig_dir)


if __name__ == "__main__":
    main()
