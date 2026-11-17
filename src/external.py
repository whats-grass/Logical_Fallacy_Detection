"""Loaders for the four external datasets (data/raw/external/) and their mapping onto the
project's 16-label schema.

Sources (see data/README.md for provenance notes):
  edu_fallacies.xlsx      LOGIC (Jin et al., 2022) educational examples, all fallacious
  sample_fallacies.xlsx   CoCoLoFa (Yeh et al., 2024): news comments written by crowd workers,
                          8 fallacy types + "No Fallacy" (a 237-row sample)
  touche_fallacies.xlsx   Touché 2026 fallacy detection (Reddit comments, from Sahai et al., 2021),
                          same label set; 233 rows have no labels and are dropped
  contrastive_dataset.csv 703 valid/fallacy pairs (row 2k = valid, row 2k+1 = its fallacious twin)

Nothing here is fitted; the split helpers are deterministic hashes, so they cannot leak.
"""
import hashlib
import re
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import EXTERNAL, EXT_SPLIT


def _labels16():
    from .data import load_dataset
    return load_dataset()[1]


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", "", str(t).lower()).strip()


def load_schema_file(name, labels):
    """edu / sample / touche share the main dataset's 22-column layout (+ 'No Fallacy')."""
    d = pd.read_excel(EXTERNAL / name, sheet_name="Dataset")
    d = d.dropna(subset=["fallacies"]).copy()                       # unlabelled rows
    d[labels + ["No Fallacy"]] = d[labels + ["No Fallacy"]].astype(int)
    d["in_schema"] = d[labels].sum(axis=1) > 0                     # has >=1 of our 16 labels
    d["is_fallacy"] = (d["No Fallacy"] == 0).astype(int)
    d["other_labels"] = d["fallacies"].map(
        lambda s: "; ".join(x for x in str(s).split("; ") if x not in labels and x != "No Fallacy"))
    return d.reset_index(drop=True)


def load_edu(labels=None):
    labels = labels or _labels16()
    d = load_schema_file("edu_fallacies.xlsx", labels)
    d["source"] = "edu"
    return d


def load_comments(labels=None):
    """Online comments: CoCoLoFa (crowd-written news comments) + Touché 2026 (Reddit)."""
    labels = labels or _labels16()
    parts = []
    for name, src in [("sample_fallacies.xlsx", "cocolofa"), ("touche_fallacies.xlsx", "touche")]:
        d = load_schema_file(name, labels); d["source"] = src; parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    d["uid"] = d["source"] + ":" + d["id"].astype(str)
    return d


def load_contrastive():
    d = pd.read_csv(EXTERNAL / "contrastive_dataset.csv")
    assert (d.label.values[0::2] == "valid").all() and (d.label.values[1::2] == "fallacy").all()
    d["pair"] = np.arange(len(d)) // 2
    d["is_fallacy"] = (d.label == "fallacy").astype(int)
    # a sentence that occurs in two pairs ties those pairs into one group (one duplicate exists)
    key = d.text.map(_norm)
    n = d.pair.max() + 1
    rows, cols = [], []
    for _, g in d.groupby(key):
        p = g.pair.unique()
        rows += [p[0]] * len(p); cols += list(p)
    G = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    comp = connected_components(G, directed=False)[1]
    d["group"] = "pair" + pd.Series(comp[d.pair]).astype(str).values
    d["source"] = "contrastive"
    d["uid"] = "contrastive:" + d.index.astype(str)
    return d.rename(columns={"text": "argument"})


def near_dup_groups(texts, tau=0.8):
    """Connected components of the cosine >= tau graph (labels unused)."""
    V = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(texts)
    S = (V @ V.T).tocoo(); keep = S.data >= tau
    G = sp.coo_matrix((np.ones(keep.sum()), (S.row[keep], S.col[keep])), shape=(V.shape[0],) * 2)
    return connected_components(G, directed=False)[1]


def hash_split(group_ids, shares=EXT_SPLIT):
    """Deterministic train/val/test assignment by md5 of the group id."""
    u = np.array([int(hashlib.md5(str(g).encode()).hexdigest()[:8], 16) / 16 ** 8 for g in group_ids])
    return np.where(u < shares[0], "train", np.where(u < shares[0] + shares[1], "val", "test"))


def binary_dataset():
    """Fallacy-vs-valid data: only sources that contain BOTH classes (contrastive, comments), so the
    writing style of a source cannot predict the label."""
    c = load_contrastive()
    r = load_comments()
    # the prefix "reddit" is part of the hashed group id: it is kept as it was when the split
    # was declared, because changing it would reshuffle the train/val/test assignment
    r["group"] = "reddit" + pd.Series(near_dup_groups(r.argument.tolist())).astype(str).values
    cols = ["uid", "source", "argument", "is_fallacy", "group"]
    d = pd.concat([c[cols + ["pair"]], r[cols]], ignore_index=True)
    d["split"] = hash_split(d.group)
    return d


def combined_dataset(labels=None):
    """All five sources in one table for notebook 13 (training on everything).

    Columns: uid, source, argument, the 16 label columns, is_fallacy, split, trainable.
    * main dataset: official split, all rows trainable.
    * edu (LOGIC): rows with >= 1 of our labels; split by a hash of the near-duplicate cluster.
    * comments (CoCoLoFa + Touché): "No Fallacy" rows become all-zero rows (valid arguments);
      fallacious rows need >= 1 of our labels. Split = the split of notebook 12, unchanged.
    * contrastive pairs: the file gives no fallacy TYPE, so the fallacious twins cannot be
      16-label targets; keeping only the valid twins would teach "contrastive style = valid".
      Both twins are therefore evaluation-only (trainable = False), split as in notebook 12.
    Fallacious rows whose only labels are outside our 16 are dropped: as all-zero rows they
    would wrongly teach the model that they are valid.
    """
    from .data import load_dataset
    df, L = load_dataset()
    labels = labels or L
    main = df[["id", "argument", "split"] + labels].copy()
    main["uid"] = "main:" + main["id"].astype(str); main["source"] = "main"
    main["is_fallacy"] = 1; main["trainable"] = True

    e = load_edu(labels); e = e[e.in_schema].reset_index(drop=True)
    e["uid"] = "edu:" + e["id"].astype(str)
    # cluster on normalised text so that variants differing only in punctuation share a split
    e["split"] = hash_split("edu" + pd.Series(near_dup_groups(e.argument.map(_norm).tolist())).astype(str).values)
    e["trainable"] = True

    B = binary_dataset().set_index("uid")
    c = load_comments(labels)
    c = c[(c.is_fallacy == 0) | c.in_schema].reset_index(drop=True)
    c.loc[c.is_fallacy == 0, labels] = 0     # valid argument: no fallacy label
    c["split"] = B.loc[c.uid, "split"].values; c["trainable"] = True

    k = load_contrastive()
    k["split"] = B.loc[k.uid, "split"].values; k["trainable"] = False
    for l in labels:
        k[l] = 0          # unknown for the fallacious twins; never used as a training target

    cols = ["uid", "source", "argument"] + labels + ["is_fallacy", "split", "trainable"]
    return pd.concat([main[cols], e[cols], c[cols], k[cols + ["pair"]]], ignore_index=True)
