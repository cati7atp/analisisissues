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


def make_corpus(per_theme=30, seed=0):
    rng = np.random.default_rng(seed)
    centers = rng.normal(scale=10, size=(len(THEMES), 16))
    docs, embeddings = [], []
    for i, words in enumerate(THEMES.values()):
        vocab = words.split()
        for j in range(per_theme):
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
