"""Explicit embedding computation with an on-disk .npy cache (S17)."""

import hashlib
import os
from pathlib import Path
from typing import Any, List, Optional, Sequence

import numpy as np
import structlog

logger = structlog.get_logger()


def build_embedding_text(title: str, body: Optional[str], max_chars: int = 2000) -> str:
    """Embedding text: title plus the first `max_chars` characters of the body."""
    title = (title or "").strip()
    body = (body or "").strip()[:max_chars]
    return f"{title} {body}".strip()


def corpus_key(texts: Sequence[str], model_name: str, normalize: bool) -> str:
    """Stable key over the exact encoded strings, the model name and the normalize flag."""
    digest = hashlib.sha256()
    digest.update(f"{model_name}\x00{int(normalize)}\x00".encode("utf-8"))
    for text in texts:
        digest.update(text.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()[:24]


def compute_embeddings(
    texts: List[str],
    model_name: str,
    cache_dir: Path,
    encoder: Optional[Any] = None,
    batch_size: int = 64,
    device: Optional[str] = None,
    normalize: bool = True,
) -> np.ndarray:
    """Encode `texts` once and cache the matrix as .npy keyed by model and corpus."""
    cache_dir = Path(cache_dir)
    cache_path = cache_dir / f"embeddings_{corpus_key(texts, model_name, normalize)}.npy"
    if cache_path.exists():
        logger.info("Embeddings cache hit", path=str(cache_path))
        return np.load(cache_path)

    if encoder is None:
        from sentence_transformers import SentenceTransformer

        encoder = SentenceTransformer(model_name, device=device)
    logger.info("Computing embeddings", n_docs=len(texts), model=model_name)
    embeddings = np.asarray(
        encoder.encode(
            texts,
            batch_size=batch_size,
            device=device,
            normalize_embeddings=normalize,
            show_progress_bar=True,
        )
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    _save_atomic(cache_path, embeddings)
    return embeddings


def _save_atomic(path: Path, array: np.ndarray) -> None:
    """Write to a temporary file, then rename, so an interrupted run never leaves a corrupt cache."""
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "wb") as handle:  # a file handle stops np.save appending ".npy"
            np.save(handle, array)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
