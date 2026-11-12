# Handoff: BERTopic results on quantum-software GitHub issues

Short guide for the team that will analyze the results. Paths are relative to the repository root
(`C:\Users\catuk\Documents\cuantica\analisisissues`).

## 1. What this project does

It takes the GitHub **issues** of ~100 repositories with quantum components (Qiskit, PennyLane, Cirq,
Braket, tket, ...), cleans them, groups them into **topics** with BERTopic, and looks for **patterns that
repeat across different projects**.

```
miner.db  ->  preprocess  ->  BERTopic  ->  patterns / cross-project topics  ->  metrics  ->  report
```

| Step | Command | Writes |
|------|---------|--------|
| 1 Clean | `python -m src.cli preprocess` | `data/processed/issues_clean.jsonl` |
| 2 Topics | `python -m src.cli topic-model --output-dir data/analysis` | `topics.jsonl`, `doc_topics.jsonl`, ... |
| 3 Patterns | `python -m src.cli extract-patterns --output-dir data/analysis` | `quantum_patterns.jsonl`, `cross_project_patterns.*` |
| 4 Metrics | `python -m src.cli compute-metrics --output-dir data/analysis` | `maintainability_metrics.json`, `comparisons.json` |
| 5 Report | `python -m src.cli generate-report` | `reports/quantum_maintainability_report.md` |

Everything in one go: `python -m src.cli run-pipeline` (about 30 minutes on a GTX 1660 Ti; most of it is
the temporal views and the outlier reassignment).

## 2. Where things are

| What | Path |
|------|------|
| Source dataset (read-only SQLite) | `quantum-gh-dataset-2026-10-22/miner.db` (see `README_DATASET.txt` there) |
| Settings (thresholds, model, seed) | `config.yaml` |
| Pattern categories and keywords | `config/quantum_taxonomy.yaml` |
| Code | `src/` (`topic_model.py`, `cross_project.py`, `patterns.py`, `metrics.py`, `report.py`) |
| Tests (182) | `tests/` (`python -m pytest -q`) |
| Cleaned issues (pseudonymized) | `data/processed/issues_clean.jsonl` |
| **Results** | `data/analysis/` |
| Final report | `reports/quantum_maintainability_report.md` |
| Saved BERTopic model | `data/analysis/model/` |

`data/` and `reports/` are in `.gitignore`: **they are not in git**, share them separately.

## 3. The results, file by file (`data/analysis/`)

Start with the first three.

| File | What it is | Key columns |
|------|------------|-------------|
| `cross_project_patterns.csv` | **Main file.** One row per topic, flagged when it recurs across repos | `topic_id, name, cross_project, n_repos, n_supporting_repos, n_issues, top_repo, top_repo_share, evenness, keywords, supporting_repos` |
| `topics.jsonl` | The 151 topics | `topic_id, name, keywords, count, representative_docs, top_repo, top_repo_share, n_repos, repo_specific` |
| `doc_topics.jsonl` | Issue -> topic (`-1` = outlier) | `issue_id` (`owner/repo#number`), `topic_id`, `probability` |
| `cross_project_patterns.jsonl` | Same as the CSV plus `per_repo` (issues and prevalence per repo) and `example_issue_ids` | |
| `quantum_patterns.jsonl`, `pattern_summary.csv` | Keyword-taxonomy categories (12) with their issues | `pattern_id, frequency, topic_share, supporting_issue_ids, example_quotes` |
| `candidate_categories.jsonl` | Topics the taxonomy does not explain (new category candidates) | `topic_id, matched_share` |
| `topics_reduced.jsonl`, `doc_topics_reduced.jsonl` | Same result with outliers reassigned by similarity (more coverage, lower quality) | |
| `topics_over_time.jsonl`, `topics_per_class.jsonl` | Topic frequency per time bin / per repo | |
| `maintainability_metrics.json`, `maintainability_summary.csv` | Per-repo metrics (resolution time, Gini, topic entropy, ...) | |
| `comparisons.json` | Per-repo, per-SDK-family and capped (max 1000 issues/repo) views | |
| `run_summary.json` | 35 340 issues, 151 topics, 49.9 % outliers, 3 noise topics | |
| `topic_visualization.html` | Interactive BERTopic charts (open in a browser) | |

### What "cross-project pattern" means here

A topic is flagged `cross_project = True` when at least **3 repos each hold 3 or more** of its issues and
no single repo holds more than **90 %** of it (`cross_project:` in `config.yaml`). Outliers never count.
This is lenient: 104 of 151 topics qualify. Stricter cuts (computed from `per_repo`):

| Rule | Topics |
|------|--------|
| 3 repos x 3 issues, top repo <= 90 % (default) | 104 |
| 5 repos x 5 issues, top repo <= 70 % | 38 |
| 8 repos x 5 issues, top repo <= 60 % | 11 |

Changing the thresholds needs no retraining: edit `config.yaml` and run
`python -m src.cli extract-patterns --output-dir data/analysis`.

## 4. Quick start for the analysis

```python
import pandas as pd
cp = pd.read_csv("data/analysis/cross_project_patterns.csv")
strong = cp[(cp.cross_project) & (cp.n_supporting_repos >= 8) & (cp.top_repo_share <= 0.6)]
print(strong[["topic_id", "keywords", "n_supporting_repos", "n_issues"]])
```

Read an example issue: take an id from `example_issue_ids`, look it up in
`data/processed/issues_clean.jsonl` (`repo` + `issue_number`) or in `miner.db`.

To rebuild the environment: `py -3.12 -m venv .venv`, install a CUDA build of `torch`, then
`pip install -r requirements.txt` (the pins `click<8.2` and `hdbscan==0.8.40` matter).

## 5. Read this before trusting the results

1. **Topics are semantic similarity, not the same bug.** A topic shared by 38 repos means similar wording.
   Validate by hand: read ~30 issues from topics 4, 2, 10 and 20 before claiming a pattern.
2. **About half of the issues (49.9 %) are outliers** and belong to no topic, so patterns describe half the
   corpus. Embedding model: general-purpose `all-MiniLM-L6-v2`, weak on quantum vocabulary.
3. **Not everything is quantum.** CI/coverage, sphinx, wheels and docstrings topics are general maintenance.
   Separate them from pulse, noise, Clifford, gradients, transpilation and QASM topics.
4. **The keyword taxonomy is coarse.** `documentation_examples` matches 6 121 issues (17 %).
5. **`gdsfactory/gdsfactory` (1 038 issues) is photonic chip design**, probably not quantum, and it is still
   included (it dominates topic 0). Decide whether to exclude it (`input.exclude_repos` in `config.yaml`).
6. **Qiskit has by far the most issues**, so topics skew to it; that is why the criteria cap the top-repo share.
7. **Not verified:** two runs giving identical topics (the seed is fixed, but I did not run it twice), and the
   GitHub CI on Ubuntu/Python 3.11. The original spec (S19-S29) is not stored in the repo.

## 6. Privacy

Authors, commenters and assignees are replaced by salted pseudonyms (`u_<12 hex>`) and `@mentions` are
masked, in `issues_clean.jsonl` and every output. Repository names are public projects; the report
anonymizes them (`report.anonymize`), the CSV and JSONL files do not. Change `preprocessing.author_salt`
in `config.yaml` to make pseudonyms unlinkable to this release.
