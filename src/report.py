"""Generación del informe científico del análisis de mantenibilidad cuántica."""

import json
import base64
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

import pandas as pd
import structlog

from .config import get_config
from .models import MaintainabilityMetrics, QuantumPattern, TopicInfo
from .taxonomy import load_taxonomy

logger = structlog.get_logger()


def load_metrics(metrics_path: Path) -> MaintainabilityMetrics:
    """Carga las métricas desde JSON."""
    with open(metrics_path, "r", encoding="utf-8") as f:
        return MaintainabilityMetrics.model_validate_json(f.read())


def load_topics(topics_path: Path) -> List[TopicInfo]:
    """Carga los temas desde JSONL."""
    topics = []
    if not topics_path.exists():
        return topics
    with open(topics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            topics.append(TopicInfo.model_validate_json(line))
    return topics


def load_patterns(patterns_path: Path) -> List[QuantumPattern]:
    """Carga los patrones desde JSONL."""
    patterns = []
    if not patterns_path.exists():
        return patterns
    with open(patterns_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            patterns.append(QuantumPattern.model_validate_json(line))
    return patterns


def anonymize_repo_name(repo: str, salt: str = "quantum-issues-2024") -> str:
    """Anonimiza el nombre del repositorio con un hash consistente."""
    hash_obj = hashlib.sha256(f"{salt}{repo}".encode())
    return f"Repo_{hash_obj.hexdigest()[:8]}"


def format_number(n: Optional[float], decimals: int = 1) -> str:
    """Da formato a un número para el informe."""
    if n is None:
        return "N/A"
    return f"{n:.{decimals}f}"


def format_outcomes(outcomes: Dict[str, int]) -> str:
    """Da formato al desglose por estado de cierre; nunca imprime el dict crudo."""
    if not outcomes:
        return "N/A"
    ordered = sorted(outcomes.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name.replace('_', ' ')}: {count}" for name, count in ordered)


def generate_executive_summary(metrics: MaintainabilityMetrics, patterns: List[QuantumPattern]) -> str:
    """Genera la sección de resumen ejecutivo."""
    agg = metrics.aggregated
    total_patterns = sum(p.frequency for p in patterns)
    
    return f"""# Executive Summary

This report presents a systematic analysis of GitHub issues from repositories utilizing quantum computing components (Qiskit, Cirq, PennyLane, Amazon Braket, Q#, and related frameworks). The objective is to identify maintainability patterns specific to hybrid quantum-classical software products, which represent a novel paradigm in the software industry.

## Key Findings

- **Repositories Analyzed**: {agg.total_repos}
- **Total Issues**: {agg.total_issues}
- **Median Resolution Time**: {format_number(agg.overall_median_resolution_days)} days
- **Resolution Outcomes (closed issues)**: {format_outcomes(agg.resolution_outcomes)}
- **Contributor Concentration (Gini)**: {agg.overall_gini_contributors:.2f}
- **Quantum-Specific Patterns Identified**: {len(patterns)} categories, {total_patterns} total occurrences

## Quantum Pattern Taxonomy

The analysis revealed {len(patterns)} distinct categories of quantum-specific maintainability challenges:

| Category | Frequency | Description |
|----------|-----------|-------------|
{chr(10).join(f"| {p.name} | {p.frequency} | {p.description[:80]}... |" for p in patterns[:8])}

## Maintainability Implications

Hybrid quantum-classical systems exhibit unique maintainability characteristics not captured by traditional software metrics. Hardware dependencies, algorithmic convergence uncertainties, and the simulator-hardware gap introduce failure modes that require specialized monitoring and mitigation strategies.
"""


def _taxonomy(config):
    return load_taxonomy(config.quantum_taxonomy)


def _taxonomy_terms(config) -> List[str]:
    return [t for c in _taxonomy(config).categories.values() for t in c.terms]


def generate_methodology(config) -> str:
    """Genera la sección de metodología."""
    return f"""# Methodology

## Data Collection

Issues and comments were extracted from GitHub repositories identified as using quantum computing frameworks. The dataset includes issues from repositories matching the quantum taxonomy terms (for example: {", ".join(_taxonomy_terms(config)[:5])}).

## Preprocessing

Raw GitHub issues underwent the following cleaning steps:
1. **Bot filtering**: Removal of automated comments from dependabot, renovate, github-actions, and similar bots
2. **Normalization**: Timestamps converted to UTC ISO8601, usernames lowercased
3. **Markdown stripping**: Code fences, inline code, URLs, and mentions replaced with placeholders
4. **Deduplication**: Near-duplicate comments removed
5. **Classification**: Issues typed as bug, feature, question, or discussion based on labels and content heuristics

## Topic Modeling

We employed BERTopic (Grootendorst, 2022) for unsupervised topic discovery:
- **Embedding Model**: {config.bertopic.embedding_model} (sentence-transformers)
- **Dimensionality Reduction**: UMAP (n_neighbors={config.bertopic.umap_n_neighbors}, n_components={config.bertopic.umap_n_components})
- **Clustering**: HDBSCAN (min_cluster_size={config.bertopic.hdbscan_min_cluster_size})
- **Topic Representation**: c-TF-IDF with KeyBERT-inspired representation
- **Minimum Topic Size**: {config.bertopic.hdbscan_min_cluster_size}

## Pattern Extraction

Quantum-specific patterns were identified through keyword matching against a curated taxonomy of {sum(len(c.terms) for c in _taxonomy(config).categories.values())} terms across {len(_taxonomy(config).categories)} categories, validated against discovered topics.

## Metrics Computation

Maintainability metrics were computed per repository and aggregated:
- **Resolution Time**: Median days from creation to closure (by issue type)
- **Reopen Rate**: Proxy via comments after closure date
- **Contributor Concentration**: Gini coefficient of issue authorship
- **Quantum Keyword Ratios**: Proportion of issues mentioning each pattern category
- **Topic Entropy**: Shannon entropy of topic distribution per repository
"""


def generate_pattern_taxonomy(patterns: List[QuantumPattern], config) -> str:
    """Genera la sección de taxonomía de patrones cuánticos."""
    lines = ["# Quantum Pattern Taxonomy\n"]
    
    for pattern in patterns:
        lines.append(f"## {pattern.name} (`{pattern.pattern_id}`)")
        lines.append(f"**Frequency**: {pattern.frequency} issues")
        lines.append(f"**Description**: {pattern.description}")
        lines.append(f"**Keywords**: {', '.join(pattern.keywords_matched[:10])}")
        
        if pattern.example_quotes:
            lines.append("**Representative Quotes**:")
            for i, quote in enumerate(pattern.example_quotes, 1):
                lines.append(f"{i}. \"{quote}\"")
        
        lines.append("")
    
    return "\n".join(lines)


def generate_metrics_section(metrics: MaintainabilityMetrics, anonymize: bool) -> str:
    """Genera la sección de métricas de mantenibilidad."""
    agg = metrics.aggregated
    lines = [
        "# Maintainability Metrics\n",
        "## Aggregated Metrics\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Repositories | {agg.total_repos} |",
        f"| Total Issues | {agg.total_issues} |",
        f"| Median Resolution Time (days) | {format_number(agg.overall_median_resolution_days)} |",
        f"| Resolution Outcomes (closed) | {format_outcomes(agg.resolution_outcomes)} |",
        f"| Contributor Gini Coefficient | {agg.overall_gini_contributors:.3f} |",
        f"| Avg Issues per Repository | {agg.avg_issues_per_repo:.1f} |",
        "",
        "## Per-Repository Metrics\n",
    ]
    
    # Crea la tabla resumen
    df_data = []
    for m in metrics.per_repo:
        repo_name = anonymize_repo_name(m.repo) if anonymize else m.repo
        df_data.append({
            "Repository": repo_name,
            "Total Issues": m.total_issues,
            "Open": m.open_issues,
            "Closed": m.closed_issues,
            "Median Resolution (days)": format_number(m.median_resolution_days),
            "Outcomes": format_outcomes(m.resolution_outcomes),
            "Gini": f"{m.gini_contributors:.3f}",
            "Contributors": m.unique_contributors,
            "Topic Entropy": f"{m.topic_entropy:.2f}",
        })
    
    df = pd.DataFrame(df_data)
    lines.append(df.to_markdown(index=False))
    lines.append("")
    
    # Distribución por tipo de issue
    lines.append("## Issue Type Distribution\n")
    cat_lines = ["| Type | Count | Percentage |", "|------|-------|------------|"]
    total = sum(agg.category_distribution.values())
    for cat, count in sorted(agg.category_distribution.items(), key=lambda x: -x[1]):
        cat_lines.append(f"| {cat} | {count} | {count/total:.1%} |")
    lines.extend(cat_lines)
    lines.append("")
    
    # Prevalencia de patrones cuánticos
    lines.append("## Quantum Pattern Prevalence\n")
    pattern_lines = ["| Pattern | Prevalence |", "|---------|------------|"]
    for pattern_id, prev in sorted(agg.quantum_pattern_prevalence.items(), key=lambda x: -x[1]):
        pattern_lines.append(f"| {pattern_id} | {prev:.1%} |")
    lines.extend(pattern_lines)
    lines.append("")
    
    return "\n".join(lines)


def load_cross_project(path: Path) -> List[dict]:
    """Filas escritas por extract-patterns; [] si el archivo no existe."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_cross_project_section(rows: List[dict], anonymize: bool, config, top_n: int = 25) -> str:
    """Temas que se repiten en repos distintos, con los umbrales que los definen."""
    cp = config.cross_project
    selected = [r for r in rows if r["cross_project"]]
    lines = ["# Cross-Project Patterns\n",
             f"A topic is a cross-project pattern when at least {cp.min_repos} repositories each hold "
             f"{cp.min_issues_per_repo} or more of its issues and no single repository holds more than "
             f"{cp.max_top_repo_share:.0%} of it. Outlier issues are never counted.\n",
             f"**{len(selected)} of {len(rows)} topics qualify.**\n"]
    if not selected:
        return "\n".join(lines)
    lines.append("| Topic | Keywords | Repos | Issues | Top repo share | Evenness |")
    lines.append("|-------|----------|-------|--------|----------------|----------|")
    for r in selected[:top_n]:
        top = anonymize_repo_name(r["top_repo"]) if anonymize else r["top_repo"]
        lines.append(f"| {r['topic_id']} | {', '.join(r['keywords'][:6])} | {len(r['supporting_repos'])} "
                     f"| {r['n_issues']} | {r['top_repo_share']:.0%} ({top}) | {r['evenness']:.2f} |")
    return "\n".join(lines) + "\n"


def generate_comparative_discussion(metrics: MaintainabilityMetrics, patterns: List[QuantumPattern], n_topics: int) -> str:
    """Genera la sección de discusión comparativa."""
    agg = metrics.aggregated
    
    return f"""# Comparative Discussion

## Quantum vs Classical Maintainability

Traditional software maintainability metrics (resolution time, resolution outcomes, contributor concentration) provide a baseline, but quantum software introduces additional dimensions:

### 1. Hardware Dependency Risk
Unlike classical software, quantum programs depend on physical quantum hardware with:
- Calibration drift requiring frequent recalibration
- Queue times affecting development velocity
- Device availability impacting reproducibility
- **Evidence**: {agg.quantum_pattern_prevalence.get('hardware_backend', 0):.1%} of issues mention hardware/backend concerns

### 2. Algorithmic Uncertainty
Variational quantum algorithms (VQE, QAOA) exhibit:
- Barren plateaus preventing gradient-based optimization
- Convergence to local minima
- Sensitivity to ansatz choice and initialization
- **Evidence**: {agg.quantum_pattern_prevalence.get('algorithm_convergence', 0):.1%} of issues discuss convergence

### 3. Simulator-Hardware Gap
Results on noiseless simulators often diverge from hardware execution due to:
- Noise model fidelity limitations
- Shot noise and readout errors
- Crosstalk and correlated errors not captured in simulation
- **Evidence**: {agg.quantum_pattern_prevalence.get('sim_vs_hardware', 0):.1%} of issues report discrepancies

### 4. Compilation Fragility
Quantum circuit transpilation introduces:
- Non-deterministic routing/layout decisions
- Optimization-level-dependent behavior
- Basis gate decomposition variations
- **Evidence**: {agg.quantum_pattern_prevalence.get('transpilation_compilation', 0):.1%} of issues involve transpilation

### 5. Gradient Computation Challenges
Hybrid quantum-classical gradients require:
- Parameter-shift rules (circuit evaluations scale with parameters)
- Adjoint differentiation (simulator-only)
- Framework-specific autodiff integration (PennyLane, TFQ, JAX)
- **Evidence**: {agg.quantum_pattern_prevalence.get('gradients_autodiff', 0):.1%} of issues involve gradients

## Topic Model Insights

The BERTopic model discovered {n_topics} topics across {agg.total_repos} repositories ({agg.total_issues} issues in total), revealing that quantum issues naturally organize around:
- Hardware access and backend management
- Algorithm implementation and debugging
- Framework version compatibility
- Result validation and reproducibility

## Implications for Practitioners

1. **Monitoring**: Traditional CI/CD insufficient; need quantum-specific health checks (calibration status, queue times)
2. **Testing**: Require hardware-in-the-loop testing, not just simulator validation
3. **Dependencies**: Pin quantum framework versions rigorously; breaking changes are frequent
4. **Documentation**: Hardware-specific behavior must be documented alongside algorithmic logic
5. **Skills**: Teams need quantum physics literacy alongside software engineering
"""


def generate_threats_to_validity(config) -> str:
    """Genera la sección de amenazas a la validez."""
    return """# Threats to Validity

## Internal Validity

1. **Keyword-Based Pattern Detection**: Patterns identified via keyword matching may produce false positives (keyword mentioned in unrelated context) or false negatives (concept discussed without exact keyword). Manual validation of a sample is recommended.

2. **Issue Classification Heuristics**: Issue typing (bug/feature/question) relies on labels and text heuristics, which may misclassify issues, especially in repositories with inconsistent labeling practices.

3. **No Event History**: The dataset has no event timeline, so reopen rate and label churn are not reported; closed issues are broken down by `state_reason` instead.

4. **Label Churn**: True label churn requires event data; current implementation returns 0 as placeholder.

## External Validity

1. **Repository Selection Bias**: Analysis limited to repositories matching quantum keywords and minimum star thresholds; may miss early-stage or private quantum projects.

2. **Language Bias**: GitHub issues predominantly in English; non-English discussions not captured.

3. **Temporal Scope**: Snapshot analysis; maintainability patterns may evolve as quantum frameworks mature.

4. **Framework Coverage**: Keyword list may not capture all quantum frameworks (e.g., newer ones like CUDA-Q, Qadence).

## Construct Validity

1. **Maintainability Operationalization**: Metrics chosen (resolution time, resolution outcomes, Gini) are proxies; true maintainability includes cognitive load, onboarding time, and change failure rate not measured here.

2. **Topic Model Stability**: BERTopic results vary with random seeds and hyperparameters; results should be validated across multiple runs.
"""


def generate_conclusions(metrics: MaintainabilityMetrics, patterns: List[QuantumPattern]) -> str:
    """Genera la sección de conclusiones."""
    agg = metrics.aggregated
    
    return f"""# Conclusions

This analysis of {agg.total_issues} GitHub issues across {agg.total_repos} quantum software repositories reveals that hybrid quantum-classical systems exhibit distinct maintainability challenges requiring specialized engineering practices.

## Key Contributions

1. **Quantum Pattern Taxonomy**: {len(patterns)} categories of quantum-specific issues identified, providing a vocabulary for practitioners and researchers.

2. **Quantitative Baselines**: First systematic measurement of resolution times, resolution outcomes, and contributor concentration in quantum repositories.

3. **Methodological Framework**: Reproducible pipeline combining BERTopic topic modeling with domain-specific pattern extraction.

## Recommendations

### For Quantum Software Engineers
- Implement hardware health monitoring in CI pipelines
- Design algorithms with simulator-hardware gap in mind
- Pin quantum framework dependencies; test upgrades in isolation
- Invest in reproducibility infrastructure (seed management, environment capture)

### For Framework Maintainers
- Improve error messages for transpilation and gradient failures
- Provide migration guides for breaking changes
- Stabilize core APIs; quantum ecosystem suffers from rapid churn

### For Researchers
- Validate pattern taxonomy with practitioner surveys
- Extend analysis to pull requests and commit data
- Investigate correlation between quantum patterns and production incidents
- Develop quantum-specific maintainability metrics (e.g., calibration-aware MTTR)

## Future Work

- Longitudinal analysis tracking pattern evolution across framework versions
- Integration with GitHub Actions workflow data for CI/CD failure patterns
- Practitioner interviews to validate and enrich pattern descriptions
- Extension to quantum-specific package ecosystems (PyPI, conda-forge)
"""


def embed_visualization(visualization_path: Path, report_dir: Optional[Path] = None) -> str:
    """Devuelve un enlace a la visualización, relativo a la carpeta del reporte."""
    if not visualization_path.exists():
        return "*Visualization not available*"

    # El enlace se calcula desde la carpeta del reporte para que funcione al abrirlo.
    target = visualization_path
    if report_dir is not None:
        target = Path(os.path.relpath(visualization_path, report_dir))
    return f"[Interactive Topic Visualization]({target.as_posix()})"


def generate_report(
    config,
    metrics_path: Path,
    topics_path: Path,
    patterns_path: Path,
    output_path: Path,
    anonymize: bool = True,
) -> str:
    """Genera el informe científico completo."""
    logger.info("Generating report", output=str(output_path))
    
    # Carga los datos
    metrics = load_metrics(metrics_path)
    topics = load_topics(topics_path)
    patterns = load_patterns(patterns_path)
    cross_project = load_cross_project(patterns_path.with_name("cross_project_patterns.jsonl"))
    
    # Arma las secciones del informe
    sections = []
    
    sections.append("# Quantum Software Maintainability Analysis Report\n")
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sections.append(f"*Generated: {generated_at}*")
    sections.append(f"*Anonymized: {anonymize}*\n")
    
    sections.append(generate_executive_summary(metrics, patterns))
    sections.append(generate_methodology(config))
    sections.append(generate_pattern_taxonomy(patterns, config))
    sections.append(generate_metrics_section(metrics, anonymize))
    sections.append(generate_comparative_discussion(metrics, patterns, len(topics)))
    if cross_project:
        sections.append(generate_cross_project_section(cross_project, anonymize, config))
    
    # Referencia a la visualización
    sections.append("# Topic Model Visualization\n")
    sections.append(embed_visualization(config.paths.visualization_html, output_path.parent))
    sections.append("")
    
    sections.append(generate_threats_to_validity(config))
    sections.append(generate_conclusions(metrics, patterns))
    
    # Referencias
    sections.append("""# References

1. Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv preprint arXiv:2203.05794*.
2. McKinney, W. (2010). Data Structures for Statistical Computing in Python. *Proceedings of the 9th Python in Science Conference*.
3. Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*.
""")
    
    # Escribe el informe
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_content = "\n".join(sections)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info("Report generated", path=str(output_path), length=len(report_content))
    return report_content


if __name__ == "__main__":
    import typer
    from .config import load_config
    
    cfg = load_config(Path("config.yaml"))
    generate_report(cfg, cfg.paths.metrics_output, cfg.paths.topics_output, cfg.paths.patterns_output, cfg.paths.report_md)