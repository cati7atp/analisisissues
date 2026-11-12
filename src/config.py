"""Configuration management for quantum issues analysis."""

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
    # Repos that are kept but reported as needing review (see the preprocess summary).
    review_repos: List[str] = Field(default_factory=lambda: ["gdsfactory/gdsfactory"])


class PreprocessingConfig(BaseModel):
    bot_users: List[str] = Field(default_factory=lambda: [
        "dependabot", "renovate", "github-actions", "codecov", "coveralls", "bors", "mergify",
        "qiskit-bot", "CLAassistant", "pre-commit-ci", "codecov-commenter", "stale"
    ])
    # Case-sensitive regexes matched per line (MULTILINE); each must start at the line start.
    automated_comment_patterns: List[str] = Field(default_factory=lambda: [
        r"^This issue has been automatically marked as stale\b.*$",
        r"^Thank you for your submission, we really appreciate it\. Like many open source projects.*$",
    ])
    min_body_length: int = 10
    min_chars: int = 30  # drop items whose cleaned title+body has fewer characters; 0 disables
    max_comment_length: int = 50000
    strip_code_fences: bool = True
    strip_templates: bool = True
    repeated_line_min_issues: int = 20  # a line in this many distinct issues is boilerplate; 0 disables
    repeated_comment_min_issues: int = 5  # a comment in this many distinct issues is automated or templated; 0 disables
    drop_exact_duplicates: bool = True  # keep the first of identical title+body documents
    normalize_whitespace: bool = True


class BERTopicConfig(BaseModel):
    embedding_model: str = "all-MiniLM-L6-v2"
    nr_topics: Optional[int] = None
    embed_max_chars: int = 2000  # title + first N chars of body are embedded (comments are not)
    embed_batch_size: int = 64
    embed_device: Optional[str] = None
    embed_normalize: bool = True
    umap_n_neighbors: int = 15
    umap_n_components: int = 5
    umap_min_dist: float = 0.0
    umap_metric: str = "cosine"
    hdbscan_min_cluster_size: int = 30  # unvalidated starting value for ~36k issues
    hdbscan_min_samples: int = 10  # unvalidated starting value
    hdbscan_metric: str = "euclidean"
    vectorizer_ngram_range: List[int] = Field(default_factory=lambda: [1, 2])
    vectorizer_stop_words: str = "english"
    vectorizer_min_df: int = 1
    vectorizer_max_df: float = 0.85  # fraction of topics: c-TF-IDF fits one document per topic
    # Placeholder tokens that clean_text leaves in the text (S11)
    domain_stop_words: List[str] = Field(default_factory=lambda: [
        "code", "block", "url", "user", "issue", "code_block", "build_log"
    ])
    # Build, install and CI vocabulary (S20): a topic with >= 3 of its top-10 keywords here is reported as noise
    noise_lexicon: List[str] = Field(default_factory=lambda: [
        "macosx", "aarch64", "ranlib", "travis", "dependabot", "tagbot", "appveyor", "manylinux", "x86_64",
        "ccache", "cmake", "gcc", "wheel", "wheels", "pip", "ubuntu", "circleci", "jenkins", "github actions",
        "workflow", "linux", "darwin", "msvc", "conda", "toolchain", "distutils", "msvccompiler",
    ])
    calculate_probabilities: bool = False  # use hdbscan.probabilities_
    reduce_outliers: bool = False  # True also writes a separate reduced result (S18)
    temporal_nr_bins: int = 20  # time bins for topics_over_time
    reproducible: bool = False  # True seeds UMAP (random_state=42) but disables parallelism
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
    quantum_patterns: Optional[QuantumPatternsConfig] = None  # legacy; superseded by the taxonomy
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)


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
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)


def load_settings() -> Settings:
    """Load settings from environment."""
    return Settings()


# Global config instance
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