"""Gestión de la configuración del análisis de issues cuánticos."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "config" / "quantum_taxonomy.yaml"


class PathsConfig(BaseModel):
    raw_data: Path = Path("data/raw/issues.jsonl")
    processed_data: Path = Path("data/processed/issues_clean.jsonl")
    topics_output: Path = Path("data/analysis/topics.jsonl")
    doc_topics_output: Path = Path("data/analysis/doc_topics.jsonl")
    patterns_output: Path = Path("data/analysis/quantum_patterns.jsonl")
    metrics_output: Path = Path("data/analysis/maintainability_metrics.json")
    metrics_csv: Path = Path("reports/maintainability_summary.csv")
    model_dir: Path = Path("models/bertopic")
    visualization_html: Path = Path("reports/topic_visualization.html")
    report_md: Path = Path("reports/quantum_maintainability_report.md")
    pattern_summary_csv: Path = Path("reports/pattern_summary.csv")
    cache_dir: Path = Path("data/cache")


class InputConfig(BaseModel):
    db_path: Path = Path("quantum-gh-dataset-2026-10-22/miner.db")
    item_types: List[str] = Field(default_factory=lambda: ["issue"])
    include_comment_kinds: List[str] = Field(default_factory=lambda: ["issue_comment"])
    exclude_repos: List[str] = Field(default_factory=lambda: ["QuTech-Delft/OpenQL"])
    max_reject_ratio: float = 0.005
    # Repos que se conservan pero se marcan como pendientes de revisión (ver el resumen de preprocess).
    review_repos: List[str] = Field(default_factory=lambda: ["gdsfactory/gdsfactory"])


class PreprocessingConfig(BaseModel):
    bot_users: List[str] = Field(default_factory=lambda: [
        "dependabot", "renovate", "github-actions", "codecov", "coveralls", "bors", "mergify",
        "qiskit-bot", "CLAassistant", "pre-commit-ci", "codecov-commenter", "stale"
    ])
    # Regex sensibles a mayúsculas aplicadas por línea (MULTILINE); cada una debe empezar al inicio de la línea.
    automated_comment_patterns: List[str] = Field(default_factory=lambda: [
        r"^This issue has been automatically marked as stale\b.*$",
        r"^Thank you for your submission, we really appreciate it\. Like many open source projects.*$",
    ])
    min_body_length: int = 10
    min_chars: int = 30  # descarta ítems cuyo título+cuerpo limpio tenga menos caracteres; 0 lo desactiva
    max_comment_length: int = 50000
    strip_code_fences: bool = True
    strip_templates: bool = True
    repeated_line_min_issues: int = 20  # una línea presente en tantos issues distintos es texto repetitivo; 0 lo desactiva
    repeated_comment_min_issues: int = 5  # un comentario presente en tantos issues distintos es automático o de plantilla; 0 lo desactiva
    drop_exact_duplicates: bool = True  # conserva el primero de los documentos con título+cuerpo idénticos
    normalize_whitespace: bool = True
    anonymize_authors: bool = True  # autores, comentaristas y asignados pasan a ser seudónimos con sal (u_<12 hex>)
    author_salt: str = "quantum-issues"  # cámbiala para que los seudónimos no se puedan vincular con una publicación anterior


class BERTopicConfig(BaseModel):
    embedding_model: str = "all-MiniLM-L6-v2"
    nr_topics: Optional[int] = None
    embed_max_chars: int = 2000  # se incrustan el título y los primeros N caracteres del cuerpo (los comentarios no)
    embed_batch_size: int = 64
    embed_device: Optional[str] = None
    embed_normalize: bool = True
    umap_n_neighbors: int = 15
    umap_n_components: int = 5
    umap_min_dist: float = 0.0
    umap_metric: str = "cosine"
    hdbscan_min_cluster_size: int = 30  # valor inicial sin validar para ~36k issues
    hdbscan_min_samples: int = 10  # valor inicial sin validar
    hdbscan_metric: str = "euclidean"
    vectorizer_ngram_range: List[int] = Field(default_factory=lambda: [1, 2])
    vectorizer_stop_words: str = "english"
    vectorizer_min_df: int = 1
    vectorizer_max_df: float = 0.85  # fracción de temas: c-TF-IDF ajusta un documento por tema
    # Tokens de marcador que clean_text deja en el texto (S11)
    domain_stop_words: List[str] = Field(default_factory=lambda: [
        "code", "block", "url", "user", "issue", "code_block", "build_log", "email"
    ])
    # Vocabulario de compilación, instalación y CI (S20): un tema con >= 3 de sus 10 palabras clave principales aquí se reporta como ruido
    noise_lexicon: List[str] = Field(default_factory=lambda: [
        "macosx", "aarch64", "ranlib", "travis", "dependabot", "tagbot", "appveyor", "manylinux", "x86_64",
        "ccache", "cmake", "gcc", "wheel", "wheels", "pip", "ubuntu", "circleci", "jenkins", "github actions",
        "workflow", "linux", "darwin", "msvc", "conda", "toolchain", "distutils", "msvccompiler",
    ])
    calculate_probabilities: bool = False  # usa hdbscan.probabilities_
    reduce_outliers: bool = False  # True también escribe un resultado reducido por separado (S18)
    repo_specific_share: float = 0.8  # un tema con una cuota del repo principal superior a esta se marca como repo_specific
    temporal_nr_bins: int = 10  # intervalos de tiempo para topics_over_time
    temporal_views: bool = True  # topics_over_time es lento en corpus grandes; False lo omite junto con topics_per_class
    seed: int = 42  # random_state de UMAP
    reproducible: bool = True  # True: UMAP con semilla y un solo hilo (temas idénticos entre ejecuciones); False: paralelo y sin semilla
    verbose: bool = True


class QuantumPatternsConfig(BaseModel):
    hardware_backend: List[str]
    algorithm_convergence: List[str]
    dependency_version: List[str]
    sim_vs_hardware: List[str]
    transpilation_compilation: List[str]
    gradients_autodiff: List[str]
    reproducibility: List[str]
    performance_scaling: List[str]


class MetricsConfig(BaseModel):
    compute_gini: bool = True
    resolution_time_quantiles: List[float] = Field(default_factory=lambda: [0.25, 0.5, 0.75])
    anonymize_repos_in_report: bool = True
    comparison_repo_cap: int = 1000  # tope de documentos por repo para la ejecución de sensibilidad


class CrossProjectConfig(BaseModel):
    min_repos: int = 3  # repos que deben tener cada uno min_issues_per_repo issues del tema
    min_issues_per_repo: int = 3
    max_top_repo_share: float = 0.9  # ningún repo puede tener más de esta proporción del tema


class ReportConfig(BaseModel):
    include_visualizations: bool = True
    max_example_quotes: int = 3
    quote_max_length: int = 200
    anonymize: bool = True


class Config(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    bertopic: BERTopicConfig = Field(default_factory=BERTopicConfig)
    quantum_taxonomy: Path = DEFAULT_TAXONOMY_PATH
    quantum_patterns: Optional[QuantumPatternsConfig] = None  # heredado; reemplazado por la taxonomía
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    cross_project: CrossProjectConfig = Field(default_factory=CrossProjectConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    github_token: Optional[str] = None
    log_level: str = "INFO"


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Carga la configuración desde un archivo YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)


def load_settings() -> Settings:
    """Carga los ajustes desde el entorno."""
    return Settings()


# Instancia global de configuración
_config: Optional[Config] = None
_settings: Optional[Settings] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings