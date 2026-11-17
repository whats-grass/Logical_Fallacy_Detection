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

## Provenance and access

* Built from `logical_fallacy_model_candidates.jsonl` (19,246 raw records of multiple-choice,
  true/false and free-form fallacy items), cleaned and de-duplicated as described in the
  `README` sheet.
* Labels are **silver labels**: they come from an LLM-written explanation of each answer,
  normalised to 16 canonical names. They have not been manually verified.
* Many arguments are synthetic and templated (e.g. 1,744 "calculators in math class"
  arguments; see notebook 02).


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
