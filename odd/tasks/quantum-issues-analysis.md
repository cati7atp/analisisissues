# Quantum GitHub Issues Analysis — Feature Specification

## Header
- **Objective**: Analyze GitHub issues/comments from repositories using quantum components to identify patterns informing maintainability of hybrid quantum-classical software products
- **Branch**: `feature/quantum-issues-analysis`
- **Delivery Strategy**: `ask-on-risk`
- **Test Runner**: `pytest -q`

## Specs

### S3: Data Preprocessing & Cleaning
**Requirement**: Normalize and clean raw issue data for analysis
**Acceptance Criteria**:
- CLI command `preprocess` reads `data/raw/issues.jsonl` (or directory) and writes `data/processed/issues_clean.jsonl`
- Input format (JSONL per line): `{"repo": "owner/repo", "issue_number": 123, "title": "...", "body": "...", "state": "open|closed", "labels": ["bug", "quantum"], "created_at": "ISO8601", "closed_at": "ISO8601|null", "author": "login", "comments": [{"author": "login", "created_at": "ISO8601", "body": "..."}]}`
- Removes: bot comments (dependabot, renovate, github-actions, etc.), system messages, duplicate comments
- Normalizes: timestamps to UTC ISO8601, user logins to lowercase, strips markdown code fences
- Extracts: issue type (bug, feature, question, discussion), labels, state transitions
- Preserves: issue number, title, body, comments (author, created_at, body), repo context
- Output JSONL: one line per issue with all cleaned fields + `issue_type`, `cleaned_body`, `cleaned_comments`

### S4: Topic Modeling with BERTopic
**Requirement**: Apply BERTopic to discover thematic patterns in quantum-related issues
**Acceptance Criteria**:
- CLI command `topic-model` accepts `--input` (processed JSONL), `--output-dir`, `--min-topic-size` (default: 10), `--n-topics` (optional), `--embedding-model` (default: `all-MiniLM-L6-v2`)
- Uses `sentence-transformers` for embeddings + BERTopic (HDBSCAN + UMAP)
- Combines title + body + comments as document text per issue
- Outputs: `models/bertopic/` (saved model), `data/analysis/topics.jsonl` (topic_id, name, keywords, count, representative_docs), `data/analysis/doc_topics.jsonl` (issue_id, topic_id, probability)
- Generates visualization HTML: `reports/topic_visualization.html` (interactive topic map, hierarchy, barcharts)
- Logs: number of topics, outlier percentage, top topics by frequency

### S5: Quantum-Specific Pattern Extraction
**Requirement**: Extract patterns specific to quantum software maintainability
**Acceptance Criteria**:
- CLI command `extract-patterns` reads topics and processed issues, writes `data/analysis/quantum_patterns.jsonl`
- Pattern taxonomy (keyword-based + topic inspection):
  - `hardware_backend`: noise, calibration, queue times, device availability, backend, ibm_quantum, ionq, rigetti
  - `algorithm_convergence`: VQE, QAOA, ansatz, barren plateaus, convergence, optimizer, cost function
  - `dependency_version`: qiskit-terra, qiskit-aer, pennylane, numpy, python version, version conflict, dependency hell
  - `sim_vs_hardware`: simulator, hardware, noise model, shot count, discrepancy, different results
  - `transpilation_compilation`: transpile, transpilation, circuit, gate, basis gates, coupling map, routing, layout
  - `gradients_autodiff`: gradient, autodiff, backprop, parameter-shift, adjoint, jax, tensorflow, pytorch, pennylane
  - `reproducibility`: seed, deterministic, reproducible, random, non-deterministic, different runs
  - `performance_scaling`: scaling, qubit count, depth, execution time, memory, large circuit
- Each pattern: pattern_id, name, description, supporting_issue_ids, frequency, example_quotes (max 3, truncated to 200 chars)
- Also outputs `reports/pattern_summary.csv` for quick inspection

### S6: Maintainability Metrics Computation
**Requirement**: Compute quantitative maintainability indicators from issue data
**Acceptance Criteria**:
- CLI command `compute-metrics` outputs `data/analysis/maintainability_metrics.json` and `reports/maintainability_summary.csv`
- Metrics per repo and aggregated:
  - Issue density: issues/star (if stars available), issues per repo
  - Resolution time: median time to close (by type: bug vs feature vs question)
  - Reopen rate: % issues reopened after close (track via state transitions or events)
  - Label churn: label additions/removals per issue (if event data available)
  - Contributor concentration: Gini coefficient of issue authorship
  - Quantum-specific ratios: % issues mentioning hardware, simulators, gradients, transpilation, convergence
  - Topic diversity: entropy of topic distribution per repo
- Outputs both JSON (full) and CSV (summary table)

### S7: Comparative Analysis Report
**Requirement**: Generate scientific report comparing quantum vs classical maintainability patterns
**Acceptance Criteria**:
- CLI command `generate-report` produces `reports/quantum_maintainability_report.md`
- Sections: Executive Summary, Methodology, Quantum Pattern Taxonomy, Maintainability Metrics, Comparative Discussion, Threats to Validity, Conclusions
- Includes: topic model visualizations (embedded as base64 or linked), metric tables, representative quotes (anonymized: repo names hashed or generic)
- References: links to source issues preserved in data (issue_number + repo)
- Configurable: `--anonymize` flag to hash repo names in report

### S8: Reproducibility & Configuration
**Requirement**: Full pipeline configurable and reproducible
**Acceptance Criteria**:
- `config.yaml` with all parameters (model names, thresholds, paths, quantum keywords)
- `run_pipeline.sh` / `run_pipeline.ps1` executes full workflow end-to-end
- `requirements.txt` / `pyproject.toml` with pinned versions
- GitHub Actions workflow: `.github/workflows/analysis.yml` (manual dispatch with data artifact)
- README with: quickstart, expected input format, configuration, extending pattern keywords, interpreting outputs

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S3 | inline | pending | - |
| T2 | S4 | delegated | pending | - |
| T3 | S5 | inline | pending | - |
| T4 | S6 | inline | pending | - |
| T5 | S7 | inline | pending | - |
| T6 | S8 | inline | pending | - |

## Log
**L1** (2026-10-22): User request — analyze GitHub issues from quantum-component repositories to find patterns informing maintainability of hybrid quantum-classical products. Pre-existing PDF on BERTopic applied to GitHub issues suggests prior exploration.
**L2** (2026-10-22): User clarification — data acquisition already done by colleague; focus on analysis pipeline (S3-S8). Input data format defined as JSONL with issue+comments structure.