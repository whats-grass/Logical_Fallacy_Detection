"""Near-duplicate / template-overlap measurement between evaluation rows and train.

The TF-IDF space used here is fitted on TRAIN ONLY, and labels are never used,
so this is a leakage-free description of how 'familiar' each eval argument is.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def max_sim_to_train(train_texts, eval_texts, batch=1000):
    vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=1)
    A = vec.fit_transform(train_texts)
    B = vec.transform(eval_texts)
    out, arg = np.zeros(B.shape[0]), np.zeros(B.shape[0], dtype=int)
    for s in range(0, B.shape[0], batch):
        S = cosine_similarity(B[s:s + batch], A)
        out[s:s + batch] = S.max(axis=1)
        arg[s:s + batch] = S.argmax(axis=1)
    return out, arg


def bucket(sim, low, high):
    return np.where(sim >= high, "template-seen", np.where(sim < low, "novel", "intermediate"))
