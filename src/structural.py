"""Hand-written structural / rhetorical features (proposal: "tabular syntactic, rhetorical
and n-gram representations").

Each feature counts one argument pattern with a regular expression. They were written from the
Label Guide definitions, before looking at any model. They are stateless; the only learned step
is the StandardScaler, which callers must fit on training data only.
"""
import re
import numpy as np
import scipy.sparse as sp
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler

PATTERNS = {
    "if_then":       r"\bif\b[^.!?]*\b(?:then|will|would|'ll)\b",          # conditional consequence
    "chain":         r"\b(?:then|eventually|ultimately|leading to|which will|before you know it)\b",
    "either_or":     r"\beither\b[^.!?]*\bor\b|\bonly (?:two|one) (?:options?|choices?)\b|\bor else\b",
    "universal":     r"\b(?:all|every|everyone|everybody|always|never|nobody|no one)\b",
    "authority":     r"\b(?:expert|experts|dr|doctor|scientist|professor|study|studies|famous|celebrity)\b",
    "popularity":    r"\b(?:everyone|millions|most people|popular|majority|trend\w*)\b",
    "second_person": r"\b(?:you|your|you're)\b",
    "insult":        r"\b(?:idiot|stupid|liar|hypocrite|ignorant|fool|corrupt|lazy|crazy|incompetent)\b",
    "causal":        r"\b(?:because|caused?|causes|since|therefore|thus|after)\b",
    "negation":      r"\b(?:not|no|never|don't|can't|won't|isn't|doesn't)\b",
    "question":      r"\?",
    "exclaim":       r"!",
}
FEATURE_NAMES = list(PATTERNS) + ["log_length"]
_COMPILED = [re.compile(p) for p in PATTERNS.values()]


def structural_features(texts):
    rows = []
    for t in texts:
        tl = t.lower()
        rows.append([len(rx.findall(tl)) for rx in _COMPILED] + [np.log1p(max(len(tl.split()), 1))])
    return np.asarray(rows, dtype=float)


class TfidfPlusStructural(BaseEstimator, TransformerMixin):
    """[TF-IDF | weight * standardised structural features], as one sparse matrix.

    `weight` balances 13 dense columns against ~38k sparse ones; it is a hyperparameter chosen
    by cross-validation on train (notebook 09). Both the vectoriser and the scaler are fitted
    in `fit`, so inside a CV pipeline they only ever see the training fold.
    """

    def __init__(self, vectorizer=None, weight=0.3):
        self.vectorizer = vectorizer
        self.weight = weight

    def fit(self, X, y=None):
        from .features import word_tfidf
        from sklearn.base import clone
        self.vec_ = clone(self.vectorizer) if self.vectorizer is not None else word_tfidf(ngram_range=(1, 2))
        self.vec_.fit(X)
        self.scaler_ = StandardScaler().fit(structural_features(X))
        return self

    def transform(self, X):
        S = self.scaler_.transform(structural_features(X)) * self.weight
        return sp.hstack([self.vec_.transform(X), sp.csr_matrix(S)]).tocsr()
