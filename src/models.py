"""Model factories. All are one-vs-rest over the 16 labels (multi-label)."""
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC, SVC
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, Normalizer
from .config import SEED


def logreg(penalty="l2", C=1.0, class_weight=None):
    # scikit-learn >= 1.8 expresses the penalty through l1_ratio (1 = Lasso, 0 = ridge).
    solver = "liblinear" if penalty == "l1" else "lbfgs"
    return OneVsRestClassifier(LogisticRegression(
        l1_ratio=1.0 if penalty == "l1" else 0.0, C=C, solver=solver, max_iter=3000,
        class_weight=class_weight, random_state=SEED))


def linear_svm(C=1.0, class_weight=None):
    return OneVsRestClassifier(LinearSVC(C=C, class_weight=class_weight,
                                         max_iter=20000, random_state=SEED))


def pca_logreg(k=300, C=1.0, class_weight=None):
    # TruncatedSVD = PCA without centring (centring would densify the sparse matrix).
    # Scaler is inside the pipeline, so its mean/std are learned on train folds only.
    # The projection is shared by all 16 labels (fitted once), then one LR per label.
    return make_pipeline(
        TruncatedSVD(n_components=k, random_state=SEED), StandardScaler(),
        OneVsRestClassifier(LogisticRegression(C=C, max_iter=3000, class_weight=class_weight)))


def svd_rbf_svm(C=1.0, gamma="scale", class_weight=None, k=300):
    # RBF on the full ~10^4-dim sparse space is O(n^2) kernel work per label; we run it on
    # a train-fitted 300-d SVD projection (unit-normalised) to keep it tractable.
    return make_pipeline(
        TruncatedSVD(n_components=k, random_state=SEED), Normalizer(),
        OneVsRestClassifier(SVC(C=C, gamma=gamma, kernel="rbf",
                                class_weight=class_weight, cache_size=1000), n_jobs=2))


def scores_of(model, X):
    """Continuous score per label (probability if available, else decision function)."""
    if hasattr(model, "predict_proba"):
        try:
            return model.predict_proba(X)
        except AttributeError:
            pass
    return model.decision_function(X)


class PriorBaseline:
    """Predicts the label set that maximises expected F1 under no information:
    the single most frequent label (Slippery Slope) for every argument."""
    def fit(self, X, Y):
        self.prior_ = Y.mean(axis=0)
        self.top_ = int(np.argmax(self.prior_))
        return self

    def predict(self, X):
        out = np.zeros((X.shape[0], len(self.prior_)), dtype=int)
        out[:, self.top_] = 1
        return out

    def predict_proba(self, X):
        return np.tile(self.prior_, (X.shape[0], 1))


class StratifiedRandomBaseline(PriorBaseline):
    """Predicts each label independently with probability = its train prevalence."""
    def __init__(self, seed=SEED):
        self.seed = seed

    def predict(self, X):
        rng = np.random.default_rng(self.seed)
        return (rng.random((X.shape[0], len(self.prior_))) < self.prior_).astype(int)
