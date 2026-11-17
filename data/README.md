# Data

## File

`data/raw/logical_fallacy_dataset.xlsx` (≈4 MB, tracked in git). Sheets:

| sheet | contents |
|---|---|
| `Dataset` | 17,866 arguments × 21 columns: `id`, `argument`, `fallacies` (semicolon-separated), `num_fallacies`, `split`, and 16 one-hot label columns |
| `README` | provenance and cleaning log written by the dataset builder |
| `Label Guide` | definition and frequency of each of the 16 fallacy labels |
| `Excluded - Review` | 468 rows removed for conflicting / rare / mismatched labels |

## One row

One row = one natural-language argument (median 26 words). The target is a 16-dimensional
binary vector (multi-label: 1–5 fallacies per argument, mean 1.33). There is **no
"no-fallacy" class**: every row contains at least one fallacy.

## Soruce and access

* Built from `logical_fallacy_model_candidates.jsonl` (19,246 raw records of multiple-choice,
  true/false and free-form fallacy items), cleaned and de-duplicated as described in the
  `README` sheet.
* Labels are **silver labels**: they come from an LLM-written explanation of each answer,
  normalised to 16 canonical names. They have not been manually verified.
* Many arguments are synthetic and templated (e.g. 1,744 "calculators in math class"
  arguments; see notebook 02).

**Source** Bin Liu (2026). *A Logical Fallacy Dataset from 2015 to
  2025* (version V2). Science Data Bank. https://doi.org/10.57760/sciencedb.30044
* The published record describes around 20,000 examples in JSON over 13 fallacy types.The    
  file we used  has 19,246 records, and the 16 labels are the dataset builder's normalisation.


## Splits

The `split` column is a deterministic 80/10/10 assignment by a hash of the normalised text
(train 14,341 / val 1,768 / test 1,757). It prevents exact duplicates from crossing splits but
**not** paraphrased templates; notebooks 06 and 08 measure how much that matters.

## Processed data

`data/processed/near_dup_groups_trainval.csv` (written by notebook 08): one row per train or
validation argument (`id`, `split`) with its near-duplicate cluster id at cosine thresholds
0.9 / 0.8 / 0.7 / 0.6 (`group_tau90` … `group_tau60`). Built from TF-IDF of train + val text
only; labels and the test split are never used. The raw spreadsheet is not modified
(team rule 3).

## Reproducing

No download step is needed while the `.xlsx` stays in the repository. All code loads it via
`src/data.py::load_dataset()`, which also asserts the label columns are consistent.

## External data (`data/raw/external/`)

Added after the main evaluation; used only in notebooks 11-13 (`src/external.py`). None of the
texts overlaps the main dataset or each other (checked on normalised text). Sources were named
by the team and checked against the publishers' pages.

| file | rows | source | notes |
|---|---|---|---|
| `edu_fallacies.xlsx` | 2,428 | `edu_all.csv` of LOGIC: Jin, Lalwani, Vaidhya, Shen, Ding, Lyu, Sachan, Mihalcea & Schölkopf (2022), "Logical Fallacy Detection", *Findings of EMNLP 2022*, https://doi.org/10.18653/v1/2022.findings-emnlp.532 (data: github.com/causalNLP/logical-fallacy) | labels mapped onto our 16 by the provider; 334 rows carry only labels outside our 16 (e.g. "Fallacy of Logic", "Intentional") and are excluded from scoring; no Slippery Slope or Composition |
| `sample_fallacies.xlsx` | 237 | a sample of CoCoLoFa: Yeh, Wan & Huang (2024), "CoCoLoFa: A Dataset of News Comments with Common Logical Fallacies Written by LLM-Assisted Crowds", *EMNLP 2024*, https://doi.org/10.18653/v1/2024.emnlp-main.39 | news comments written by crowd workers with an LLM assistant (not Reddit); 8 fallacy types + 97 `No Fallacy`; 55 rows carry only labels outside our 16 |
| `touche_fallacies.xlsx` | 1,171 | Touché 2026 fallacy detection: Heinrich, Mathews & Stein (2026), *Touché26-Fallacy-Detection*, Zenodo, https://doi.org/10.5281/zenodo.19925569, built on Sahai, Balalau & Horincar (2021), "Breaking Down the Invisible Wall of Informal Fallacies in Online Discussions", *ACL-IJCNLP 2021*, https://doi.org/10.18653/v1/2021.acl-long.53 | Reddit comments; 473 `No Fallacy`; **233 rows have no labels and are dropped**; 187 rows carry only labels outside our 16 |
| `contrastive_dataset.csv` | 1,406 | Logical Fallacy Counterfactual Dataset, Kaggle (user navy007), described in Singh (2026), "Debiasing Logical Fallacy Detection for Real-World Robustness via Counterfactually Augmented Data", *ACL 2026 Student Research Workshop*, https://aclanthology.org/2026.acl-srw.30/ | 703 LLM-generated pairs: row 2k = valid argument, row 2k+1 = its fallacious twin; one valid sentence occurs in two pairs (rows 342 and 384), so those pairs are grouped together |

* **Licence:** <LICENCE MAIN> (as stated on the Science Data Bank page).
Licences(These are open sources): LOGIC <LICENCE LOGIC>; CoCoLoFa <LICENCE COCOLOFA>; Touché 2026 CC BY 4.0;
Logical Fallacy Counterfactual Dataset (Kaggle) <LICENCE KAGGLE>.

