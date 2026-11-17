"""Small data file for the "Explore the Lab" page (website/lab.html).

    python -m src.export_lab

Writes website/data/lab_data.json:
* label_guide: the 16 fallacy definitions, copied from the dataset's own "Label Guide" sheet;
* quiz: six single-label arguments from the main TEST split for "Spot the fallacy", each with
  four options (the dataset's label plus three other labels, in a fixed random order);
* pairs: eight contrastive pairs from the TEST split of notebook 12 (a valid argument and its
  fallacious twin), for "Same reasoning, different words";
* bpe: seven test arguments split by the BPE subword tokenizer of notebook 03 (vocabulary 5,000,
  minimum frequency 2, lower-cased, whitespace pre-tokenizer, trained on the main train split);
* models: predictions of the four model families (BoW baseline, Lasso, ridge, linear SVM; the
  configurations of results/selection.json, refitted on the main train split as in notebook 10)
  on five test arguments drawn at random from those on which the models disagree.
Everything is chosen with a fixed seed. Only the "models" part fits models (a few minutes, mostly
the Lasso); the rest of the page scores texts live with the in-browser model of the inspector.
"""
import json
import numpy as np
import pandas as pd

from .config import DATA_PATH, WEB_DATA, SEED
from .data import load_dataset


def main():
    rng = np.random.default_rng(SEED)
    df, LABELS = load_dataset()

    g = pd.read_excel(DATA_PATH, sheet_name="Label Guide", header=2)
    g = g.rename(columns={g.columns[0]: "label", g.columns[1]: "count", g.columns[2]: "share", g.columns[3]: "description"})
    g = g[g.label.isin(LABELS)]
    assert len(g) == 16, "Label Guide should define all 16 labels"
    guide = [{"label": r.label, "description": r.description, "count": int(r["count"]), "share": round(float(r.share), 4)}
             for _, r in g.iterrows()]

    te = df[(df.split == "test") & (df.num_fallacies == 1)].copy()
    te["words"] = te.argument.str.split().str.len()
    te = te[(te.words >= 12) & (te.words <= 40)]
    wanted = ["Slippery Slope", "Ad Hominem", "False Dilemma", "Bandwagon / Popularity", "Appeal to Authority", "Hasty Generalization"]
    quiz = []
    for lab in wanted:
        pool = te[te.fallacies == lab]
        r = pool.iloc[int(rng.integers(0, len(pool)))]
        others = rng.choice([l for l in wanted if l != lab], 3, replace=False).tolist()
        options = others + [lab]; rng.shuffle(options)
        quiz.append({"text": r.argument, "label": lab, "options": options})
    order = rng.permutation(len(quiz)); quiz = [quiz[i] for i in order]

    from .external import binary_dataset
    B = binary_dataset()
    C = B[(B.source == "contrastive") & (B.split == "test")].dropna(subset=["pair"])
    pairs_ok = [p for p, grp in C.groupby("pair") if sorted(grp.is_fallacy) == [0, 1]]
    pick = sorted(rng.choice(pairs_ok, 8, replace=False).tolist())
    pairs = []
    for p in pick:
        grp = C[C.pair == p]
        pairs.append({"valid": grp[grp.is_fallacy == 0].argument.iloc[0], "fallacy": grp[grp.is_fallacy == 1].argument.iloc[0]})

    # ---- BPE subwords for three test arguments (notebook 03 settings) ----
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.trainers import BpeTrainer
    from tokenizers.pre_tokenizers import Whitespace
    from tokenizers.normalizers import Lowercase
    tr = df[df.split == "train"]
    tok = Tokenizer(BPE(unk_token="[UNK]")); tok.normalizer = Lowercase(); tok.pre_tokenizer = Whitespace()
    tok.train_from_iterator(tr.argument.tolist(), trainer=BpeTrainer(vocab_size=5000, min_frequency=2, special_tokens=["[UNK]"]))
    extra = te[~te.argument.isin([q["text"] for q in quiz])]
    bpe_texts = [q["text"] for q in quiz] + [extra.argument.iloc[int(rng.integers(0, len(extra)))]]
    bpe = [{"text": t, "tokens": tok.encode(t).tokens} for t in bpe_texts]

    # ---- four model families on five test arguments where they disagree ----
    import json as _json
    from .config import RESULTS
    from .data import get_splits
    from .features import word_tfidf, word_bow
    from .models import logreg, linear_svm
    sel = _json.loads((RESULTS / "selection.json").read_text())
    cw = lambda v: None if v in (None, "None") else "balanced"
    S = get_splits(df, LABELS); X_tr, Y_tr, _ = S["train"]; X_te, Y_te, te_df = S["test"]
    vec = word_tfidf(ngram_range=(1, 2)); A = vec.fit_transform(X_tr); T = vec.transform(X_te)
    bow = word_bow(); Ab = bow.fit_transform(X_tr); Tb = bow.transform(X_te)
    fits = {"BoW baseline": (logreg("l2", 1.0).fit(Ab, Y_tr), Tb),
            "Lasso": (logreg("l1", sel["LR-L1"]["C"], cw(sel["LR-L1"]["class_weight"])).fit(A, Y_tr), T),
            "Ridge": (logreg("l2", sel["LR-L2"]["C"], cw(sel["LR-L2"]["class_weight"])).fit(A, Y_tr), T),
            "Linear SVM": (linear_svm(sel["LinearSVM"]["C"], cw(sel["LinearSVM"]["class_weight"])).fit(A, Y_tr), T)}
    P = {k: m.predict(X) for k, (m, X) in fits.items()}
    sets = {k: [frozenset(np.where(r == 1)[0]) for r in v] for k, v in P.items()}
    disagree = [i for i in range(len(X_te)) if len({sets[k][i] for k in sets}) > 1 and len(X_te.iloc[i].split()) <= 45]
    pick = sorted(rng.choice(disagree, 5, replace=False).tolist())
    models = [{"text": X_te.iloc[i], "label": te_df.fallacies.iloc[i].split("; "),
               "pred": {k: [LABELS[j] for j in sorted(sets[k][i])] for k in sets}} for i in pick]
    nonzero = {"Lasso": float((np.abs(np.vstack([e.coef_.ravel() for e in fits["Lasso"][0].estimators_])) > 0).mean()),
               "Ridge": float((np.abs(np.vstack([e.coef_.ravel() for e in fits["Ridge"][0].estimators_])) > 0).mean())}

    out = {"label_guide": guide, "quiz": quiz, "pairs": pairs, "bpe": bpe,
           "models": models, "n_disagree": len(disagree), "n_test": int(len(X_te)), "nonzero_share": nonzero}
    (WEB_DATA / "lab_data.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", WEB_DATA / "lab_data.json", f"({len(guide)} labels, {len(quiz)} quiz items, {len(pairs)} pairs, {len(bpe)} BPE examples, {len(models)} model examples)")


if __name__ == "__main__":
    main()
