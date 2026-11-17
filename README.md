# Logical Fallacy Detection with Classical Machine Learning

ES 335 (Machine Learning, IIT Gandhinagar) course project.

**Live site:** `https://whats-grass.github.io/Logical_Fallacy_Detection/` (built from `website/` by `.github/workflows/pages.yml`)

## Question

When linear and margin-based classifiers label 16 informal logical fallacies in short
arguments, how much of their accuracy comes from surface lexical shortcuts (topic words and
templates) rather than words that express the reasoning pattern, and do L1 sparsity or SVM
margins reduce that reliance?

* **Row:** one argument (17,866 total). **Target:** 16 binary labels (multi-label, 1–5 per row).
* **Prediction time:** only the argument text is available.
* **Primary metric:** macro-F1 (rare fallacies count equally).

## Main results (held-out test split, evaluated once)

| model | macro-F1 [95% CI] | Δ vs baseline [95% CI] | micro-F1 |
|---|---|---|---|
| Most-frequent label | 0.027 | – | 0.237 |
| Unigram BoW + LR (baseline) | 0.751 [0.699, 0.786] | – | 0.794 |
| TF-IDF Lasso LR | 0.773 [0.729, 0.805] | [−0.007, +0.057] | 0.798 |
| TF-IDF ridge LR | 0.789 [0.746, 0.820] | [+0.005, +0.077] | 0.824 |
| **TF-IDF linear SVM** | **0.805 [0.764, 0.834]** | **[+0.021, +0.092]** | **0.832** |
| SVD-1000 + LR (PCA) | 0.761 [0.712, 0.793] | [−0.019, +0.048] | 0.793 |
| SVD-300 + RBF SVM | 0.764 [0.713, 0.798] | [−0.028, +0.052] | 0.815 |
| Calibrated SVM + val-tuned thresholds | 0.781 [0.735, 0.813] | [−0.006, +0.069] | 0.825 |

Shortcut audit (linear SVM):

* micro-F1 is **0.941** on test arguments that are near-copies of a training argument
  (cosine ≥ 0.8) and **0.796** on novel ones (cosine < 0.5);
* trained on **topic words only**, the model reaches 0.744 validation macro-F1, versus 0.747 with
  cue + function words only;
* replacing the 3 highest-weighted topic words flips **22%** of correct detections (random
  topic words: 6%); swapping cue words for rare synonyms flips 9%;
* group-based 5-fold CV (near-duplicate clusters kept inside one fold) lowers macro-F1 from
  0.813 to 0.708–0.752; the rare, templated fallacies lose most (Denying the Antecedent
  0.90 → 0.38).

Final test numbers, including the TF-IDF + structural model and the three focus-fallacy
detectors, are in `results/test_results.csv` and notebook 10.

## Repository layout

```
data/raw/logical_fallacy_dataset.xlsx   dataset (see data/README.md)
data/processed/                         near-duplicate cluster ids for train+val (notebook 08)
notebooks/
  01_dataset_audit.ipynb                missing values, duplicates, label consistency, splits
  02_explainatory_data_analysis.ipynb   lengths, vocabulary, templates, near-duplicates
  03_baseline_models.ipynb              word vs BPE bag-of-words + one-vs-rest LR
  04_tfidf_regularised_models.ipynb     TF-IDF, Lasso / ridge LR, linear SVM, grid on val
  05_pca_and_svm.ipynb                  truncated SVD (PCA) + LR, RBF SVM
  06_shortcut_analysis.ipynb            template overlap, coefficient anatomy, masking, stress tests
  07_thresholds_calibration.ipynb       calibration, PR curves, cost-optimal thresholds
  08_representations_imbalance_groups.ipynb  team questions Q2, Q4, Q6 (BoW vs TF-IDF, imbalance, group CV)
  09_proposal_items.ipynb               proposal items: stratification, collinearity, CV tuning,
                                        structural features, support vectors, NLTK, focus detectors
  10_final_test_evaluation.ipynb        single test evaluation, bootstrap CIs, error analysis
src/                                    shared code used by notebooks 04-10
results/                                selection.json, validation/CV grids, test results, figures
website/                                static GitHub Pages site (HTML/CSS/JS + data/*.json + figures)
.github/workflows/pages.yml             deploys website/ to GitHub Pages on every push to main
```

## Evaluation protocol

1. Official split from the dataset (train 14,341 / val 1,768 / test 1,757), fixed before modelling.
2. Vectorisers, SVD, scalers and calibration are fitted on train only.
3. Hyperparameters are chosen by 5-fold multilabel-stratified CV on train (notebook 09), after a
   first grid on the validation split (04–05); thresholds on validation (07). Notebooks 04–09
   never load the test split; choices are stored in `results/selection.json`.
4. Notebook 10 evaluates those fixed choices on test. It was run twice; see the website's §12.

## Reproduce

Follows the team setup guide (Python 3.11, 3.12 or 3.13, virtual environment, VS Code + Jupyter).

```bash
python -m venv venv
source venv/bin/activate            # Windows PowerShell: .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('punkt_tab')"
```

Then run notebooks 01 → 02 → 03 in VS Code (venv kernel), and the rest with:

```bash
python -m src.run_all               # notebooks 04-13 + website data (about 50-65 min; nb09 is ~30)
python -m http.server -d website    # view the site at http://localhost:8000
```

Seed 42 throughout; scikit-learn 1.9.1. The full pipeline (notebooks 01-10) was run on Python 3.12.3
and 3.13: all metrics agree, with the largest difference 7e-8 (in Platt-calibrated probabilities).

## Limitations

Silver (LLM-derived) labels; no "no fallacy" class; synthetic templated text; a coarse
hand-made cue lexicon; 5–15 test examples for the four rarest labels. See the website's
Limitations section.

## AI use

We used Claude and ChatGPT to help draft the experiment code in `src/` and the notebooks. Every number reported in this repository comes from running our notebooks; we re-ran them, checked the outputs, and take responsibility for all the results.

## External data (notebooks 11-12)

Four further datasets in `data/raw/external/` (sources and licences in `data/README.md`) are used
without touching the main dataset or its test split:

* **Out-of-distribution test (notebook 11).** The frozen models of `results/selection.json` are
  applied to 2,094 short educational examples from LOGIC (edu) and 363 fallacious online comments
  (CoCoLoFa news comments and Touché 2026 Reddit comments). The linear SVM falls from 0.805
  macro-F1 on the main test split to 0.327 on edu and 0.326 on the comments (scored on the labels
  each source annotates), and finds no fallacy at all in 38-49% of these arguments.
* **Fallacy vs valid (notebook 12).** On LLM-generated contrastive pairs and the online comments
  (both classes present; grouped 70/15/15 split so the twins of a pair never cross splits), the
  main-dataset model flags 44% of valid arguments. A dedicated TF-IDF linear SVM reaches 0.695
  test accuracy against 0.511 for the majority baseline (BoW baseline: 0.695), 0.80 on the pairs
  but only about 0.59 on the comments, and nothing transfers between the two sources.

* **One model trained on all datasets (notebook 13).** Main + LOGIC + comments (valid comments
  as rows with no label), contrastive pairs for testing only. Main test macro-F1 is unchanged
  (0.803 vs 0.805, paired 95% interval [-0.007, +0.005]); LOGIC test improves from 0.323 to 0.445;
  the comments show no measurable gain, and fallacy-vs-valid accuracy on them (0.538) stays below
  the majority baseline (0.564).

Re-run only these with `python -m src.run_all --from 11` (about 6 minutes).

## Data access

* **Main dataset:** `data/raw/logical_fallacy_dataset.xlsx` is in the repository (no download
  needed). Sheet `Dataset` holds one argument per row: `argument` (the text, the only model input),
  16 binary label columns, `fallacies` (the same labels as a string), `num_fallacies`, `split`
  (the fixed train / val / test assignment) and `id`. Sheets `README`, `Label Guide` and
  `Excluded - Review` (468 set-aside rows) document how it was built. See `data/README.md`.
* **External data:** four files in `data/raw/external/`, used only by notebooks 11-13.
* **Derived data:** `data/processed/near_dup_groups_trainval.csv` (near-duplicate clusters for
  group-based CV); every result table is in `results/`, figures in `results/figures/`.


## Data sources and citations

1. Bin Liu (2026). *A Logical Fallacy Dataset from 2015 to 2025* (V2). Science Data Bank.
   https://doi.org/10.57760/sciencedb.30044 (main dataset, as identified by the team)
2. Z. Jin, A. Lalwani, T. Vaidhya, X. Shen, Y. Ding, Z. Lyu, M. Sachan, R. Mihalcea,
   B. Schölkopf (2022). Logical Fallacy Detection. *Findings of EMNLP 2022*.
   https://doi.org/10.18653/v1/2022.findings-emnlp.532 (LOGIC, `edu_fallacies.xlsx`)
3. M.-H. Yeh, R. Wan, T.-H. K. Huang (2024). CoCoLoFa: A Dataset of News Comments with Common
   Logical Fallacies Written by LLM-Assisted Crowds. *EMNLP 2024*.
   https://doi.org/10.18653/v1/2024.emnlp-main.39 (`sample_fallacies.xlsx`)
4. M. Heinrich, C. Mathews, B. Stein (2026). *Touché26-Fallacy-Detection*. Zenodo, CC BY 4.0.
   https://doi.org/10.5281/zenodo.19925569 (`touche_fallacies.xlsx`), built on
   S. Sahai, O. Balalau, R. Horincar (2021). Breaking Down the Invisible Wall of Informal
   Fallacies in Online Discussions. *ACL-IJCNLP 2021*. https://doi.org/10.18653/v1/2021.acl-long.53
5. N. Singh (2026). Debiasing Logical Fallacy Detection for Real-World Robustness via
   Counterfactually Augmented Data. *ACL 2026 Student Research Workshop*.
   https://aclanthology.org/2026.acl-srw.30/ ; data: Logical Fallacy Counterfactual Dataset,
   Kaggle (navy007) (`contrastive_dataset.csv`)

Software: scikit-learn, NumPy, pandas, SciPy, NLTK, Hugging Face `tokenizers`,
`iterative-stratification`, matplotlib (versions in `requirements.txt`).
file: `data/README.md`.
