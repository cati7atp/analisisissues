"""BERTopic topic modeling for quantum GitHub issues."""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from tqdm import tqdm
import structlog
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.vectorizers import ClassTfidfTransformer
from bertopic.representation import KeyBERTInspired, MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
import umap
import hdbscan
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import get_config
from .embeddings import build_embedding_text, compute_embeddings
from .models import CleanedIssue, TopicInfo, DocTopic

logger = structlog.get_logger()


def load_cleaned_issues(input_path: Path) -> List[CleanedIssue]:
    """Load cleaned issues from JSONL."""
    issues = []
    logger.info("Loading cleaned issues", path=str(input_path))
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            # Convert datetime strings back to datetime objects
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("closed_at"):
                data["closed_at"] = datetime.fromisoformat(data["closed_at"])
            for comment in data.get("comments", []):
                comment["created_at"] = datetime.fromisoformat(comment["created_at"])
            issues.append(CleanedIssue(**data))
    
    logger.info("Loaded cleaned issues", count=len(issues))
    return issues


def prepare_documents(issues: List[CleanedIssue], embed_max_chars: int = 2000):
    """Prepare aligned lists, one entry per issue.

    docs: title + body + comments (c-TF-IDF text); embed_texts: title + start of body (S17).
    """
    docs = []
    embed_texts = []
    issue_ids = []

    for issue in issues:
        text = issue.full_text.strip()
        if text:
            docs.append(text)
            embed_texts.append(build_embedding_text(issue.title, issue.cleaned_body, embed_max_chars))
            issue_ids.append(issue.issue_id)

    logger.info("Prepared documents", count=len(docs))
    return docs, embed_texts, issue_ids


def build_vectorizer(config) -> CountVectorizer:
    """CountVectorizer for c-TF-IDF; English plus domain stop words, bigrams."""
    cfg = config.bertopic
    base = ENGLISH_STOP_WORDS if cfg.vectorizer_stop_words == "english" else frozenset()
    return CountVectorizer(
        ngram_range=tuple(cfg.vectorizer_ngram_range),
        stop_words=sorted(set(base) | {w.lower() for w in cfg.domain_stop_words}),
        min_df=cfg.vectorizer_min_df,
        max_df=cfg.vectorizer_max_df,
    )


def create_bertopic_model(config, embedding_model=None, umap_model=None) -> BERTopic:
    """Create BERTopic model with configured parameters.

    `embedding_model` and `umap_model` can be injected (tests use fakes); embeddings
    themselves are always passed explicitly to `fit_transform`.
    """
    if umap_model is None:
        umap_model = umap.UMAP(
            n_neighbors=config.bertopic.umap_n_neighbors,
            n_components=config.bertopic.umap_n_components,
            min_dist=config.bertopic.umap_min_dist,
            metric=config.bertopic.umap_metric,
            **(
                {"random_state": 42}
                if config.bertopic.reproducible
                else {"n_jobs": -1, "low_memory": True}
            ),
        )

    hdbscan_model = hdbscan.HDBSCAN(
        min_cluster_size=config.bertopic.hdbscan_min_cluster_size,
        min_samples=config.bertopic.hdbscan_min_samples,
        metric=config.bertopic.hdbscan_metric,
        cluster_selection_method="eom",
        prediction_data=True,
    )

    ctfidf_model = ClassTfidfTransformer(reduce_frequent_words=True, bm25_weighting=True)
    # Aspects only: with no "Main" key the main label stays the c-TF-IDF words.
    representation_model = {
        "KeyBERT": KeyBERTInspired(),
        "MMR": MaximalMarginalRelevance(diversity=0.3),
    }
    if embedding_model is None:
        embedding_model = SentenceTransformer(config.bertopic.embedding_model)

    return BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=build_vectorizer(config),
        ctfidf_model=ctfidf_model,
        representation_model=representation_model,
        min_topic_size=config.bertopic.hdbscan_min_cluster_size,
        nr_topics=config.bertopic.nr_topics,
        calculate_probabilities=config.bertopic.calculate_probabilities,
        verbose=config.bertopic.verbose,
    )


def run_topic_modeling(
    config, input_path: Path, output_dir: Path, embedding_model=None, umap_model=None, encoder=None
) -> BERTopic:
    """Run the full topic modeling pipeline (injectable models are for tests)."""
    # Load issues
    issues = load_cleaned_issues(input_path)
    
    # Prepare documents
    docs, embed_texts, issue_ids = prepare_documents(issues, config.bertopic.embed_max_chars)
    
    if len(docs) < config.bertopic.hdbscan_min_cluster_size * 2:
        logger.warning("Too few documents for topic modeling", count=len(docs))
        # Create minimal outputs
        output_dir.mkdir(parents=True, exist_ok=True)
        _save_empty_outputs(config, output_dir, issue_ids)
        return None
    
    # Create and fit model
    logger.info("Creating BERTopic model")
    topic_model = create_bertopic_model(config, embedding_model=embedding_model, umap_model=umap_model)

    embeddings = compute_embeddings(
        embed_texts,
        config.bertopic.embedding_model,
        config.paths.cache_dir,
        encoder=encoder,
        batch_size=config.bertopic.embed_batch_size,
        device=config.bertopic.embed_device,
        normalize=config.bertopic.embed_normalize,
    )

    logger.info("Fitting BERTopic model", n_docs=len(docs))
    topics, probabilities = topic_model.fit_transform(docs, embeddings=embeddings)
    
    # Save model
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "bertopic_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(topic_model, f)
    logger.info("Saved model", path=str(model_path))
    
    # Extract topic info
    topic_info = topic_model.get_topic_info()
    _write_run_summary(output_dir, topics)
    
    # Save topics.jsonl
    _save_topics(config, topic_model, topic_info, output_dir)
    
    # Save doc_topics.jsonl
    _save_doc_topics(config, issue_ids, topics, probabilities, output_dir)
    
    # Generate visualization
    _generate_visualization(config, topic_model, docs, output_dir)

    if config.bertopic.reduce_outliers:
        _save_reduced_result(config, topic_model, docs, issue_ids, topics, probabilities, embeddings, output_dir)

    return topic_model


def _save_reduced_result(config, topic_model, docs, issue_ids, topics, probabilities, embeddings, output_dir):
    """Second, separate result with outliers reassigned; call only after the primary outputs are saved."""
    reduced = topic_model.reduce_outliers(docs, topics, strategy="embeddings", embeddings=embeddings)
    topic_model.update_topics(
        docs,
        topics=reduced,
        vectorizer_model=topic_model.vectorizer_model,
        ctfidf_model=topic_model.ctfidf_model,
        representation_model=topic_model.representation_model,
    )
    _save_topics(config, topic_model, topic_model.get_topic_info(), output_dir, output_dir / "topics_reduced.jsonl")
    _save_doc_topics(config, issue_ids, reduced, probabilities, output_dir, output_dir / "doc_topics_reduced.jsonl")
    _write_run_summary(output_dir, topics, reduced_topics=reduced)


def _topic_counts(topics: List[int]) -> Dict[str, Any]:
    n_docs = len(topics)
    n_outliers = sum(1 for t in topics if t == -1)
    return {
        "n_topics": len({t for t in topics if t != -1}),
        "n_outliers": n_outliers,
        "outlier_share": n_outliers / n_docs if n_docs else 0.0,
    }


def _write_run_summary(
    output_dir: Path, topics: List[int], reduced_topics: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Log and persist document, topic and (unreduced) outlier counts."""
    summary = {"n_documents": len(topics), **_topic_counts(topics)}
    if reduced_topics is not None:
        summary["reduced"] = _topic_counts(reduced_topics)
    logger.info("Topic modeling complete", **summary)
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _save_topics(
    config, topic_model: BERTopic, topic_info: pd.DataFrame, output_dir: Path, output_path: Optional[Path] = None
):
    """Save topic information to JSONL."""
    output_path = output_path or config.paths.topics_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in topic_info.iterrows():
            topic_id = int(row["Topic"])
            if topic_id == -1:
                continue  # Skip outlier topic
            
            # Get representative documents
            rep_docs = topic_model.get_representative_docs(topic_id)
            rep_docs_short = [doc[:500] for doc in (rep_docs or [])]
            
            # Get keywords
            topic_words = topic_model.get_topic(topic_id)
            keywords = [word for word, _ in (topic_words or [])[:10]]
            
            topic = TopicInfo(
                topic_id=topic_id,
                name=row.get("Name", f"Topic_{topic_id}"),
                keywords=keywords,
                count=int(row["Count"]),
                representative_docs=rep_docs_short,
            )
            f.write(topic.model_dump_json() + "\n")
    
    logger.info("Saved topics", path=str(output_path), n_topics=len(topic_info) - 1)


def _save_doc_topics(
    config, issue_ids: List[str], topics: List[int], probabilities: np.ndarray, output_dir: Path,
    output_path: Optional[Path] = None,
):
    """Save document-topic assignments to JSONL."""
    output_path = output_path or config.paths.doc_topics_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for issue_id, topic_id, prob in zip(issue_ids, topics, probabilities):
            if topic_id == -1:
                prob_val = 0.0
            else:
                prob_val = float(prob) if isinstance(prob, (float, np.floating)) else float(prob[topic_id]) if hasattr(prob, '__getitem__') else 0.0
            
            doc_topic = DocTopic(
                issue_id=issue_id,
                topic_id=int(topic_id),
                probability=prob_val,
            )
            f.write(doc_topic.model_dump_json() + "\n")
    
    logger.info("Saved doc topics", path=str(output_path))


def _generate_visualization(config, topic_model: BERTopic, docs: List[str], output_dir: Path):
    """Generate interactive HTML visualization."""
    output_path = config.paths.visualization_html
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create visualizations
        fig_topics = topic_model.visualize_topics()
        fig_hierarchy = topic_model.visualize_hierarchy()
        fig_barchart = topic_model.visualize_barchart(top_n_topics=20)
        fig_heatmap = topic_model.visualize_heatmap()
        
        # Combine into single HTML with tabs
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Quantum Issues - Topic Model Visualization</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .tab {{ overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; }}
        .tab button {{ background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; }}
        .tab button:hover {{ background-color: #ddd; }}
        .tab button.active {{ background-color: #ccc; }}
        .tabcontent {{ display: none; padding: 6px 12px; border: 1px solid #ccc; border-top: none; }}
    </style>
</head>
<body>
    <h1>Quantum GitHub Issues - Topic Model Analysis</h1>
    <p>Generated: {datetime.utcnow().isoformat()}Z</p>
    <p>Documents: {len(docs)} | Topics: {len(topic_model.get_topic_info()) - 1}</p>
    
    <div class="tab">
        <button class="tablinks active" onclick="openTab(event, 'topics')">Topics Map</button>
        <button class="tablinks" onclick="openTab(event, 'hierarchy')">Hierarchy</button>
        <button class="tablinks" onclick="openTab(event, 'barchart')">Top Topics</button>
        <button class="tablinks" onclick="openTab(event, 'heatmap')">Topic Similarity</button>
    </div>
    
    <div id="topics" class="tabcontent" style="display:block;">{fig_topics.to_html(full_html=False, include_plotlyjs=False)}</div>
    <div id="hierarchy" class="tabcontent">{fig_hierarchy.to_html(full_html=False, include_plotlyjs=False)}</div>
    <div id="barchart" class="tabcontent">{fig_barchart.to_html(full_html=False, include_plotlyjs=False)}</div>
    <div id="heatmap" class="tabcontent">{fig_heatmap.to_html(full_html=False, include_plotlyjs=False)}</div>
    
    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{ tabcontent[i].style.display = "none"; }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{ tablinks[i].className = tablinks[i].className.replace(" active", ""); }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }}
    </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info("Saved visualization", path=str(output_path))
    except Exception as e:
        logger.warning("Failed to generate visualization", error=str(e))


def _save_empty_outputs(config, output_dir: Path, issue_ids: List[str]):
    """Save empty output files when too few documents."""
    # Empty topics
    with open(config.paths.topics_output, "w") as f:
        pass
    # Empty doc_topics (all outliers)
    with open(config.paths.doc_topics_output, "w", encoding="utf-8") as f:
        for issue_id in issue_ids:
            doc_topic = DocTopic(issue_id=issue_id, topic_id=-1, probability=0.0)
            f.write(doc_topic.model_dump_json() + "\n")
    # Empty visualization
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(config.paths.visualization_html, "w") as f:
        f.write("<html><body><h1>Insufficient data for topic modeling</h1></body></html>")


def load_topic_model(model_dir: Path) -> Optional[BERTopic]:
    """Load a saved BERTopic model."""
    model_path = model_dir / "bertopic_model.pkl"
    if not model_path.exists():
        return None
    with open(model_path, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    import typer
    from .config import load_config
    
    cfg = load_config(Path("config.yaml"))
    run_topic_modeling(cfg, cfg.paths.processed_data, cfg.paths.model_dir)