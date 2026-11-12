"""Tests for the BERTopic configuration, using fake embeddings and a synthetic corpus."""

import numpy as np
import pytest
from bertopic.backend import BaseEmbedder
from bertopic.dimensionality import BaseDimensionalityReduction

from src.models import clean_text
from src.topic_model import build_vectorizer, create_bertopic_model

THEMES = {
    "transpile": "transpiler optimization pass layout routing depth",
    "noise": "noise mitigation readout twirling mitigated error rates",
    "backend": "backend queue hardware access quota job runtime",
    "pulse": "pulse schedule calibration waveform amplitude drive",
}
UNIQUE_WORD = "zzuniqueword"
NOISY_TAIL = "```python\nx = 1\n``` see https://example.com/a thanks @someone fixed in #123 `inline`"


class FakeEmbedder(BaseEmbedder):
    """Deterministic embedder so no real model is ever loaded."""

    def embed(self, documents, verbose=False):
        out = []
        for doc in documents:
            seed = sum(ord(c) for c in doc) % (2**32)
            out.append(np.random.default_rng(seed).normal(size=16))
        return np.asarray(out, dtype="float32")


def make_corpus(sizes=(30, 30, 30, 30), seed=0):
    rng = np.random.default_rng(seed)
    centers = rng.normal(scale=10, size=(len(THEMES), 16))
    docs, embeddings = [], []
    for i, (words, size) in enumerate(zip(THEMES.values(), sizes)):
        vocab = words.split()
        for j in range(size):
            picked = " ".join(rng.choice(vocab, size=6))
            extra = f" {UNIQUE_WORD}" if (i == 0 and j == 0) else ""
            docs.append(clean_text(f"{picked}{extra} {NOISY_TAIL}"))
            embeddings.append(centers[i] + rng.normal(scale=0.3, size=16))
    return docs, np.asarray(embeddings, dtype="float32")


@pytest.fixture
def small_config(config):
    config.bertopic.hdbscan_min_cluster_size = 5
    config.bertopic.hdbscan_min_samples = 2
    config.bertopic.verbose = False
    return config


def fit(config, docs, embeddings):
    model = create_bertopic_model(
        config, embedding_model=FakeEmbedder(), umap_model=BaseDimensionalityReduction()
    )
    topics, _ = model.fit_transform(docs, embeddings=embeddings)
    return model, topics


def test_vectorizer_settings(config):
    vec = build_vectorizer(config)
    assert vec.min_df == 1
    assert vec.max_df == 0.85
    assert vec.ngram_range == (1, 2)
    for word in ["code", "block", "url", "user", "issue", "code_block", "the"]:
        assert word in vec.stop_words


def test_vocabulary_has_no_placeholders_and_keeps_topic_specific_words(small_config):
    docs, embeddings = make_corpus()
    model, topics = fit(small_config, docs, embeddings)
    assert len(set(topics) - {-1}) >= 3
    vocab = set(model.vectorizer_model.get_feature_names_out())
    for token in ["code", "block", "url", "user", "issue", "code_block"]:
        assert token not in vocab
    assert UNIQUE_WORD in vocab


def test_hdbscan_min_cluster_size_changes_topic_count(small_config):
    docs, embeddings = make_corpus(sizes=(8, 30, 30, 30))
    small_config.bertopic.hdbscan_min_cluster_size = 5
    _, low = fit(small_config, docs, embeddings)
    small_config.bertopic.hdbscan_min_cluster_size = 15
    _, high = fit(small_config, docs, embeddings)
    assert len(set(low) - {-1}) == 4
    assert len(set(high) - {-1}) == 3


def test_cli_min_topic_size_maps_to_hdbscan(tmp_path, monkeypatch):
    from pathlib import Path

    from typer.testing import CliRunner

    import src.topic_model as tm
    from src.cli import app

    captured = {}
    monkeypatch.setattr(tm, "run_topic_modeling", lambda cfg, inp, out: captured.setdefault("cfg", cfg))
    inp = tmp_path / "issues.jsonl"
    inp.write_text("", encoding="utf-8")
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    result = CliRunner().invoke(
        app, ["topic-model", "--input", str(inp), "--output-dir", str(tmp_path / "o"),
              "--min-topic-size", "7", "--config", str(config_path)],
    )
    assert result.exit_code == 0, result.output
    assert captured["cfg"].bertopic.hdbscan_min_cluster_size == 7


def _umap_of(config):
    return create_bertopic_model(config, embedding_model=FakeEmbedder()).umap_model


def test_umap_not_seeded_by_default(config):
    assert config.bertopic.reproducible is False
    umap_model = _umap_of(config)
    assert umap_model.random_state is None
    assert umap_model.n_jobs == -1
    assert umap_model.low_memory is True


def test_umap_seeded_when_reproducible(config):
    config.bertopic.reproducible = True
    umap_model = _umap_of(config)
    assert umap_model.random_state == 42


def test_starting_hdbscan_values_and_probabilities_off(config):
    assert config.bertopic.hdbscan_min_cluster_size == 30
    assert config.bertopic.hdbscan_min_samples == 10
    assert config.bertopic.calculate_probabilities is False


def test_doc_topic_probabilities_come_from_hdbscan(small_config, tmp_path):
    from src.topic_model import _save_doc_topics

    docs, embeddings = make_corpus()
    model, topics = fit(small_config, docs, embeddings)
    assert model.probabilities_.shape == (len(docs),)
    _save_doc_topics(small_config, [str(i) for i in range(len(docs))], topics, model.probabilities_, tmp_path)
    import json

    rows = [json.loads(line) for line in small_config.paths.doc_topics_output.read_text(encoding="utf-8").splitlines()]
    assert all(0.0 <= r["probability"] <= 1.0 for r in rows)
    assert any(r["probability"] > 0 for r in rows)


class ThemeEncoder:
    """Sentence-encoder stand-in: one cluster centre per theme plus per-text noise."""

    def __init__(self):
        self.calls = 0
        self.texts = []
        centres = np.random.default_rng(0).normal(scale=10, size=(len(THEMES), 16))
        self.centres = dict(zip(THEMES, centres))

    def encode(self, texts, **kwargs):
        self.calls += 1
        self.texts.extend(texts)
        rows = []
        for text in texts:
            rng = np.random.default_rng(sum(map(ord, text)))
            theme = next((k for k, words in THEMES.items() if words.split()[0] in text), None)
            if theme is None:  # isolated point: becomes an outlier
                rows.append(rng.normal(scale=15, size=16))
            else:
                rows.append(self.centres[theme] + rng.normal(scale=0.3, size=16))
        return np.asarray(rows, dtype="float32")


def write_issues(per_theme=30, n_misc=0):
    from src.models import RawIssue

    issues = [
        RawIssue(repo="a/b", issue_number=90000 + m, title=f"misc{m} unrelated", body=f"zork{m} blarg{m} flub{m}",
                 state="open", created_at="2024-01-01T00:00:00Z", author="human")
        for m in range(n_misc)
    ]
    for i, (theme, words) in enumerate(THEMES.items()):
        vocab = words.split()
        for j in range(per_theme):
            body = " ".join(vocab[(j + k) % len(vocab)] for k in range(8))
            issues.append(RawIssue(
                repo="a/b", issue_number=i * 1000 + j, title=f"{vocab[0]} problem {j}", body=body, state="open",
                created_at="2024-01-01T00:00:00Z", author="human",
                comments=[{"author": "h", "created_at": "2024-01-02T00:00:00Z",
                           "body": f"COMMENTMARKER{theme} {body}"}],
            ))
    return issues


@pytest.fixture
def issues_file(small_config, tmp_path):
    from src.preprocess import IssuePreprocessor

    path = tmp_path / "issues_clean.jsonl"
    IssuePreprocessor(small_config).process_items(write_issues(), path)
    return path


def run(config, input_path, out, encoder):
    from src.topic_model import run_topic_modeling

    return run_topic_modeling(
        config, input_path, out, embedding_model=FakeEmbedder(),
        umap_model=BaseDimensionalityReduction(), encoder=encoder,
    )


def test_run_uses_cached_embeddings_and_decoupled_texts(small_config, issues_file, tmp_path):
    enc = ThemeEncoder()
    model = run(small_config, issues_file, tmp_path / "out", enc)
    assert model is not None
    assert len(list(small_config.paths.cache_dir.glob("*.npy"))) == 1
    # embedding text excludes comments; c-TF-IDF text includes them
    assert not any("COMMENTMARKER" in t for t in enc.texts)
    assert any("commentmarker" in w for w in model.vectorizer_model.get_feature_names_out())
    calls = enc.calls
    run(small_config, issues_file, tmp_path / "out2", enc)
    assert enc.calls == calls


def test_run_summary_reports_unreduced_outlier_share(small_config, issues_file, tmp_path):
    import json

    out = tmp_path / "out"
    run(small_config, issues_file, out, ThemeEncoder())
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in small_config.paths.doc_topics_output.read_text(encoding="utf-8").splitlines()]
    outliers = sum(1 for r in rows if r["topic_id"] == -1)
    assert summary["n_documents"] == len(rows) == 120
    assert summary["n_outliers"] == outliers
    assert summary["outlier_share"] == pytest.approx(outliers / len(rows))
    assert summary["n_topics"] == 4


def test_keybert_and_mmr_are_aspects_main_label_stays_ctfidf(small_config):
    docs, embeddings = make_corpus()
    model, topics = fit(small_config, docs, embeddings)
    assert {"KeyBERT", "MMR"} <= set(model.topic_aspects_)
    vocab = set(model.vectorizer_model.get_feature_names_out())
    main_words = [w for w, _ in model.get_topic(0)]
    assert main_words and all(w in vocab for w in main_words)
    keybert = model.topic_aspects_["KeyBERT"][0]
    assert keybert and all(isinstance(w, tuple) for w in keybert)


def test_outliers_not_reduced_by_default(small_config, tmp_path):
    import json
    from src.preprocess import IssuePreprocessor

    path = tmp_path / "with_misc.jsonl"
    IssuePreprocessor(small_config).process_items(write_issues(n_misc=6), path)
    out = tmp_path / "out"
    run(small_config, path, out, ThemeEncoder())
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["n_outliers"] > 0
    assert "reduced" not in summary
    assert not (out / "doc_topics_reduced.jsonl").exists()


def test_reduce_outliers_writes_a_separate_second_result(small_config, tmp_path):
    import json
    from src.preprocess import IssuePreprocessor

    small_config.bertopic.reduce_outliers = True
    path = tmp_path / "with_misc.jsonl"
    IssuePreprocessor(small_config).process_items(write_issues(n_misc=6), path)
    out = tmp_path / "out"
    run(small_config, path, out, ThemeEncoder())
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    primary = [json.loads(l) for l in small_config.paths.doc_topics_output.read_text(encoding="utf-8").splitlines()]
    reduced = [json.loads(l) for l in (out / "doc_topics_reduced.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(r["topic_id"] == -1 for r in primary) == summary["n_outliers"] > 0
    n_reduced = sum(r["topic_id"] == -1 for r in reduced)
    assert n_reduced < summary["n_outliers"]  # similarity threshold 0 may leave a few unassigned
    assert summary["reduced"]["n_outliers"] == n_reduced
    assert (out / "topics_reduced.jsonl").exists()


def test_model_saved_as_safetensors_directory_and_loads_back(small_config, issues_file, tmp_path, monkeypatch):
    import sentence_transformers

    from src.topic_model import load_topic_model

    def no_real_model(*args, **kwargs):  # BERTopic.load would otherwise instantiate the saved model name
        raise RuntimeError("real embedding model must not load in tests")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", no_real_model)

    out = tmp_path / "out"
    model = run(small_config, issues_file, out, ThemeEncoder())
    assert not list(out.rglob("*.pkl"))
    assert list((out / "model").glob("*.safetensors"))
    loaded = load_topic_model(out, embedding_model=FakeEmbedder())
    assert loaded.get_topic_info()["Topic"].tolist() == model.get_topic_info()["Topic"].tolist()
    assert [w for w, _ in loaded.get_topic(0)] == [w for w, _ in model.get_topic(0)]


def test_load_topic_model_missing_dir_returns_none(tmp_path):
    from src.topic_model import load_topic_model

    assert load_topic_model(tmp_path / "nothing") is None


def test_too_few_documents_writes_empty_outputs_creating_parent_dirs(small_config, tmp_path):
    from src.preprocess import IssuePreprocessor

    path = tmp_path / "tiny.jsonl"
    IssuePreprocessor(small_config).process_items(write_issues(per_theme=2), path)
    assert not small_config.paths.topics_output.parent.exists()
    assert run(small_config, path, tmp_path / "out", ThemeEncoder()) is None
    assert small_config.paths.topics_output.exists()
    assert small_config.paths.doc_topics_output.exists()
    assert small_config.paths.visualization_html.exists()


def test_cli_output_dir_redirects_every_output(tmp_path, monkeypatch):
    from pathlib import Path

    from typer.testing import CliRunner

    import src.topic_model as tm
    from src.cli import app

    captured = {}

    def fake_run(cfg, inp, out):
        captured.update(cfg=cfg, out=out)

    monkeypatch.setattr(tm, "run_topic_modeling", fake_run)
    inp = tmp_path / "issues.jsonl"
    inp.write_text("", encoding="utf-8")
    out = tmp_path / "custom"
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    result = CliRunner().invoke(
        app, ["topic-model", "--input", str(inp), "--output-dir", str(out), "--config", str(config_path)]
    )
    assert result.exit_code == 0, result.output
    paths = captured["cfg"].paths
    assert captured["out"] == out
    for p in (paths.topics_output, paths.doc_topics_output, paths.visualization_html):
        assert p.parent == out


class StubClusterer:
    """HDBSCAN stand-in that forces a fixed number of clusters (0 or 1)."""

    clusters = 0

    def __init__(self, *args, **kwargs):
        pass

    def fit(self, X, y=None):
        self.labels_ = np.full(len(X), 0 if self.clusters else -1)
        self.probabilities_ = np.ones(len(X))
        return self


@pytest.mark.parametrize("clusters", [0, 1])
def test_too_few_clusters_finish_with_an_explicit_empty_outcome(small_config, issues_file, tmp_path, monkeypatch, clusters):
    import json
    import src.topic_model as tm

    StubClusterer.clusters = clusters
    monkeypatch.setattr(tm.hdbscan, "HDBSCAN", StubClusterer)
    out = tmp_path / "out"
    assert run(small_config, issues_file, out, ThemeEncoder()) is None
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "no_topics"
    assert summary["clusters_found"] == clusters
    assert summary["n_documents"] == 120 and summary["n_topics"] == 0 and summary["outlier_share"] == 1.0
    assert small_config.paths.topics_output.read_text(encoding="utf-8") == ""
    rows = [json.loads(l) for l in small_config.paths.doc_topics_output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 120 and {r["topic_id"] for r in rows} == {-1}


def test_other_fit_errors_are_not_swallowed(small_config, issues_file, tmp_path, monkeypatch):
    from bertopic import BERTopic

    def boom(self, *args, **kwargs):
        raise ValueError("unrelated failure")

    monkeypatch.setattr(BERTopic, "fit_transform", boom)
    with pytest.raises(ValueError, match="unrelated failure"):
        run(small_config, issues_file, tmp_path / "out", ThemeEncoder())


def test_normal_run_summary_outcome_is_ok(small_config, issues_file, tmp_path):
    import json

    out = tmp_path / "out"
    run(small_config, issues_file, out, ThemeEncoder())
    assert json.loads((out / "run_summary.json").read_text(encoding="utf-8"))["outcome"] == "ok"
