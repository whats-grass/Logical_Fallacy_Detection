"""Metrics, bootstrap uncertainty and threshold helpers for multi-label output."""
import numpy as np
from sklearn.metrics import (f1_score, precision_score, recall_score, hamming_loss,
                             accuracy_score, average_precision_score)


def scores(y_true, y_pred, y_score=None):
    out = {
        "micro_f1": f1_score(y_true, y_pred, average="micro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "micro_precision": precision_score(y_true, y_pred, average="micro", zero_division=0),
        "micro_recall": recall_score(y_true, y_pred, average="micro", zero_division=0),
        "hamming_loss": hamming_loss(y_true, y_pred),
        "subset_accuracy": accuracy_score(y_true, y_pred),
    }
    if y_score is not None:
        aps = [average_precision_score(y_true[:, k], y_score[:, k])
               for k in range(y_true.shape[1]) if y_true[:, k].any()]
        out["macro_avg_precision"] = float(np.mean(aps))
    return {k: float(v) for k, v in out.items()}


def per_class_f1(y_true, y_pred):
    return f1_score(y_true, y_pred, average=None, zero_division=0)


def bootstrap_ci(y_true, y_pred, metric="macro_f1", n_boot=1000, seed=0, y_pred_b=None):
    """Percentile CI over argument-level resampling. If y_pred_b is given, returns the
    CI of the paired difference metric(a) - metric(b) on the same resamples."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    avg = metric.split("_")[0]
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        a = f1_score(y_true[idx], y_pred[idx], average=avg, zero_division=0)
        if y_pred_b is not None:
            a -= f1_score(y_true[idx], y_pred_b[idx], average=avg, zero_division=0)
        vals.append(a)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def tune_thresholds(y_true, y_score, grid=None):
    """Per-label threshold maximising F1 on the data given (use VALIDATION only)."""
    grid = np.linspace(0.05, 0.95, 91) if grid is None else grid
    th = np.zeros(y_true.shape[1])
    for k in range(y_true.shape[1]):
        f = [f1_score(y_true[:, k], (y_score[:, k] >= t).astype(int), zero_division=0)
             for t in grid]
        th[k] = grid[int(np.argmax(f))]
    return th


def bayes_threshold(cost_fp, cost_fn):
    """Cost-optimal threshold for a calibrated probability: predict 1 iff
    p * C_FN > (1 - p) * C_FP  <=>  p > C_FP / (C_FP + C_FN)."""
    return cost_fp / (cost_fp + cost_fn)
