"""Vectorisers. Every vectoriser is fitted on the training split only."""
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from .text import tokenize


def word_bow():
    # Reproduces the notebook-03 baseline representation.
    return CountVectorizer(lowercase=True, ngram_range=(1, 1), min_df=2, max_df=0.95)


def word_tfidf(ngram_range=(1, 1), min_df=2, sublinear_tf=True):
    return TfidfVectorizer(
        tokenizer=tokenize, token_pattern=None, lowercase=False,
        ngram_range=ngram_range, min_df=min_df, max_df=0.95,
        sublinear_tf=sublinear_tf, norm="l2",
    )
