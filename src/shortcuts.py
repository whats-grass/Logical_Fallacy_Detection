"""Shortcut-learning diagnostics for linear text classifiers.

Three complementary probes:
  1. coefficient anatomy  - where does the learned weight mass sit (topic / cue / function)?
  2. input masking        - what happens to a trained model if a token group is deleted?
  3. substitution tests   - do predictions flip when label-preserving edits are made?
"""
import re
import numpy as np
import pandas as pd
from .text import token_group, tokenize, RHETORICAL_CUES

GROUPS = ["topic", "cue", "function"]


def linear_coefs(model):
    """(n_labels, n_features) coefficient matrix from a fitted OvR linear model."""
    est = model.estimators_
    W = np.vstack([np.asarray(e.coef_).ravel() for e in est])
    b = np.array([np.asarray(e.intercept_).ravel()[0] for e in est])
    return W, b


def coefficient_anatomy(W, vocab, labels):
    """Per label: share of positive-weight mass and of non-zero coefficients by token group."""
    groups = np.array([token_group(t) for t in vocab])
    rows = []
    for k, lab in enumerate(labels):
        w = W[k]
        pos = np.clip(w, 0, None)
        r = {"label": lab, "nonzero": int((w != 0).sum())}
        for g in GROUPS:
            m = groups == g
            r[f"pos_mass_{g}"] = float(pos[m].sum() / max(pos.sum(), 1e-12))
            r[f"nonzero_{g}"] = int((w[m] != 0).sum())
        rows.append(r)
    base = {g: float((groups == g).mean()) for g in GROUPS}
    return pd.DataFrame(rows), base, groups


def top_tokens(W, vocab, labels, n=12):
    groups = np.array([token_group(t) for t in vocab])
    out = {}
    for k, lab in enumerate(labels):
        idx = np.argsort(-W[k])[:n]
        out[lab] = [(vocab[i], float(W[k, i]), groups[i]) for i in idx if W[k, i] > 0]
    return out


def mask_texts(texts, keep):
    """Rebuild each text from its tokens, keeping only token groups in `keep`."""
    return [" ".join(t for t in tokenize(x) if token_group(t) in keep) for x in texts]


def _replace_tokens(text, mapping):
    toks = tokenize(text)
    return " ".join(mapping.get(t, t) for t in toks)


def neutral_topic_pool(W, vocab, df_counts, min_df=20, n=60):
    """Topic unigrams that are frequent in train yet carry the least weight for every label:
    used as 'neutral' replacements so a substitution does not inject a new signal."""
    cand = [i for i, t in enumerate(vocab)
            if " " not in t and token_group(t) == "topic" and df_counts[i] >= min_df]
    strength = np.abs(W[:, cand]).max(axis=0)
    order = np.argsort(strength)[:n]
    return [vocab[cand[i]] for i in order]


def topic_substitution(texts, true_k, W, vocab_index, pool, k_swap=3, mode="top", seed=0):
    """For each text (whose label of interest is true_k[i]) replace k_swap topic unigrams.
    mode='top'    -> the topic words with the largest positive weight for that label
    mode='random' -> random topic words present (control)"""
    rng = np.random.default_rng(seed)
    out, n_swapped = [], []
    for x, k in zip(texts, true_k):
        toks = sorted(set(t for t in tokenize(x) if token_group(t) == "topic" and t in vocab_index))
        if mode == "top":
            toks = sorted(toks, key=lambda t: -W[k, vocab_index[t]])
            toks = [t for t in toks if W[k, vocab_index[t]] > 0][:k_swap]
        else:
            toks = list(rng.permutation(toks))[:k_swap] if toks else []
        mapping = {t: pool[rng.integers(len(pool))] for t in toks}
        out.append(_replace_tokens(x, mapping)); n_swapped.append(len(mapping))
    return out, np.array(n_swapped)


# Label-preserving synonym swaps for rhetorical cue words. Each replacement keeps the
# argument's fallacy type; the replacements are chosen to be RARE in the training data, so a
# model that learned the concept rather than the exact string should not flip.
CUE_SYNONYMS = {
    "eventually": "ultimately", "soon": "shortly", "inevitably": "unavoidably",
    "everyone": "everybody", "everybody": "everyone", "millions": "multitudes", "popular": "fashionable",
    "expert": "specialist", "experts": "specialists", "scientist": "researcher",
    "famous": "renowned", "doctor": "physician", "dr": "physician", "professor": "lecturer",
    "always": "invariably", "never": "at no time", "clearly": "evidently", "obviously": "plainly",
    "idiot": "imbecile", "stupid": "dim-witted", "liar": "fibber", "hypocrite": "phony",
    "ignorant": "uninformed", "lazy": "idle", "corrupt": "crooked",
    "either": "one of two", "only": "solely", "therefore": "consequently", "proves": "demonstrates",
    "because": "as", "fear": "dread", "dangerous": "hazardous", "trust": "rely on",
}


def cue_synonym_swap(texts):
    out, n = [], []
    for x in texts:
        toks = tokenize(x)
        out.append(" ".join(CUE_SYNONYMS.get(t, t) for t in toks))
        n.append(sum(t in CUE_SYNONYMS for t in toks))
    return out, np.array(n)
