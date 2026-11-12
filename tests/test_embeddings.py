"""Tests for explicit embedding computation and the .npy cache (S17)."""

import numpy as np

from src.embeddings import build_embedding_text, compute_embeddings


class FakeEncoder:
    def __init__(self):
        self.calls = 0
        self.kwargs = None

    def encode(self, texts, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        rng = np.random.default_rng(len(texts))
        return rng.normal(size=(len(texts), 8)).astype("float32")


def test_embedding_text_is_title_plus_truncated_body():
    text = build_embedding_text("Title", "x" * 50, max_chars=10)
    assert text == "Title " + "x" * 10


def test_embedding_text_without_body_is_title():
    assert build_embedding_text("Title", "", max_chars=10) == "Title"


def test_second_call_hits_cache(tmp_path):
    enc = FakeEncoder()
    texts = ["a", "b", "c"]
    first = compute_embeddings(texts, "m", tmp_path, encoder=enc, batch_size=2, device="cpu")
    second = compute_embeddings(texts, "m", tmp_path, encoder=enc, batch_size=2, device="cpu")
    assert enc.calls == 1
    assert np.array_equal(first, second)
    assert len(list(tmp_path.glob("*.npy"))) == 1


def test_cache_key_depends_on_texts_and_model(tmp_path):
    enc = FakeEncoder()
    compute_embeddings(["a", "b"], "m", tmp_path, encoder=enc)
    compute_embeddings(["a", "c"], "m", tmp_path, encoder=enc)
    compute_embeddings(["a", "b"], "other", tmp_path, encoder=enc)
    assert enc.calls == 3
    assert len(list(tmp_path.glob("*.npy"))) == 3


def test_encode_receives_explicit_options(tmp_path):
    enc = FakeEncoder()
    compute_embeddings(["a"], "m", tmp_path, encoder=enc, batch_size=7, device="cpu", normalize=True)
    assert enc.kwargs["batch_size"] == 7
    assert enc.kwargs["device"] == "cpu"
    assert enc.kwargs["normalize_embeddings"] is True
