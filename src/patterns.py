"""Extracción de patrones específicos de computación cuántica desde temas e issues."""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

import pandas as pd
from tqdm import tqdm
import structlog

from .config import get_config
from .models import CleanedIssue, QuantumPattern, TopicInfo, DocTopic
from .taxonomy import TaxonomyMatcher, load_taxonomy

logger = structlog.get_logger()


@dataclass
class PatternMatch:
    pattern_id: str
    category: str
    issue_id: str
    matched_keywords: List[str]
    quote: str


def load_topics(topics_path: Path) -> List[TopicInfo]:
    """Carga los temas desde JSONL."""
    topics = []
    with open(topics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            topics.append(TopicInfo.model_validate_json(line))
    return topics


def load_doc_topics(doc_topics_path: Path) -> List[DocTopic]:
    """Carga las asignaciones documento-tema desde JSONL."""
    doc_topics = []
    with open(doc_topics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc_topics.append(DocTopic.model_validate_json(line))
    return doc_topics


def load_issues(issues_path: Path) -> List[CleanedIssue]:
    """Carga los issues limpios desde JSONL."""
    issues = []
    with open(issues_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            from datetime import datetime
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("closed_at"):
                data["closed_at"] = datetime.fromisoformat(data["closed_at"])
            for comment in data.get("comments", []):
                comment["created_at"] = datetime.fromisoformat(comment["created_at"])
            issues.append(CleanedIssue(**data))
    return issues


def build_keyword_patterns(config) -> TaxonomyMatcher:
    """Construye el matcher de taxonomía compartido (el mismo que usan las métricas)."""
    return TaxonomyMatcher(load_taxonomy(config.quantum_taxonomy))


def extract_quotes(text: str, keywords: List[str], max_quotes: int = 3, max_length: int = 200) -> List[str]:
    """Extrae citas relevantes de textos que contienen palabras clave."""
    quotes = []
    sentences = re.split(r"[.!?]+", text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Revisa si la oración contiene alguna palabra clave
        sentence_lower = sentence.lower()
        if any(kw.lower() in sentence_lower for kw in keywords):
            # Recorta si es muy larga
            if len(sentence) > max_length:
                sentence = sentence[:max_length] + "..."
            quotes.append(sentence)
            if len(quotes) >= max_quotes:
                break
    
    return quotes


def find_pattern_matches(
    issues: List[CleanedIssue],
    matcher: TaxonomyMatcher,
    config,
) -> List[PatternMatch]:
    """Encuentra todas las coincidencias de patrones en los issues."""
    matches = []
    
    for issue in tqdm(issues, desc="Scanning for patterns"):
        full_text = issue.full_text
        if not full_text:
            continue
        
        for category, matched_keywords in matcher.match(full_text).items():
            quotes = extract_quotes(
                full_text,
                matched_keywords,
                max_quotes=config.report.max_example_quotes,
                max_length=config.report.quote_max_length,
            )
            matches.append(PatternMatch(
                pattern_id=f"{category}_{len(matches)}",
                category=category,
                issue_id=issue.issue_id,
                matched_keywords=matched_keywords,
                quote=quotes[0] if quotes else "",
            ))

    return matches


def aggregate_patterns(matches: List[PatternMatch], names: Optional[Dict[str, str]] = None) -> List[QuantumPattern]:
    """Agrupa las coincidencias individuales en resúmenes de patrones."""
    # Agrupa por categoría
    by_category: Dict[str, List[PatternMatch]] = defaultdict(list)
    for match in matches:
        by_category[match.category].append(match)
    
    patterns = []
    for category, cat_matches in by_category.items():
        # Cuenta issues únicos por palabra clave
        keyword_issue_counts: Dict[str, Set[str]] = defaultdict(set)
        all_quotes = []
        all_keywords = []
        
        for match in cat_matches:
            for kw in match.matched_keywords:
                keyword_issue_counts[kw].add(match.issue_id)
            all_keywords.extend(match.matched_keywords)
            if match.quote:
                all_quotes.append(match.quote)
        
        # Se crea un patrón por categoría con sus palabras clave principales
        # (en vez de subpatrones por palabra clave que aparezca en varios issues)
        
        # Obtiene las palabras clave principales por frecuencia
        keyword_freq = {kw: len(issues) for kw, issues in keyword_issue_counts.items()}
        top_keywords = sorted(keyword_freq.keys(), key=lambda k: keyword_freq[k], reverse=True)[:10]
        
        # Todos los IDs de issues únicos de esta categoría
        all_issue_ids = set()
        for match in cat_matches:
            all_issue_ids.add(match.issue_id)
        
        pattern = QuantumPattern(
            pattern_id=category,
            name=(names or {}).get(category, category.replace("_", " ").title()),
            description=f"Issues related to {category.replace('_', ' ')} in quantum software development",
            category=category,
            supporting_issue_ids=sorted(all_issue_ids),
            frequency=len(all_issue_ids),
            example_quotes=all_quotes[:3],
            keywords_matched=top_keywords,
        )
        patterns.append(pattern)
    
    # Ordena por frecuencia, de mayor a menor
    patterns.sort(key=lambda p: p.frequency, reverse=True)
    return patterns


def extract_quantum_patterns(
    config,
    topics_path: Path,
    issues_path: Path,
    output_path: Path,
    doc_topics_path: Optional[Path] = None,
) -> List[QuantumPattern]:
    """Extrae patrones específicos de computación cuántica desde temas e issues.

    Con un archivo doc-topics, los patrones también informan la proporción de sus issues que cae en
    temas descubiertos, y los temas que ninguna categoría cubre se escriben en candidate_categories.jsonl.
    """
    logger.info("Loading data for pattern extraction")
    
    # Carga los datos
    topics = load_topics(topics_path)
    issues = load_issues(issues_path)
    
    # Construye los patrones de palabras clave desde la configuración
    matcher = build_keyword_patterns(config)
    
    # Busca coincidencias
    logger.info("Finding pattern matches")
    matches = find_pattern_matches(issues, matcher, config)
    logger.info("Found matches", count=len(matches))
    
    # Agrupa en patrones
    logger.info("Aggregating patterns")
    patterns = aggregate_patterns(matches, matcher.names)
    logger.info("Extracted patterns", count=len(patterns))

    doc_topics_path = doc_topics_path or config.paths.doc_topics_output
    if doc_topics_path.exists():
        doc_topics = load_doc_topics(doc_topics_path)
        patterns = enhance_with_topic_analysis(patterns, topics, doc_topics, issues)
        candidates = find_candidate_categories({m.issue_id for m in matches}, topics, doc_topics)
        candidates_path = output_path.with_name("candidate_categories.jsonl")
        candidates_path.parent.mkdir(parents=True, exist_ok=True)
        with open(candidates_path, "w", encoding="utf-8") as f:
            for candidate in candidates:
                f.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        logger.info("Candidate new categories", count=len(candidates))
    else:
        logger.info("No doc-topics file; skipping topic analysis", path=str(doc_topics_path))
    
    # Guarda los patrones en JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pattern in patterns:
            f.write(pattern.model_dump_json() + "\n")
    
    # Guarda el resumen de patrones en CSV
    csv_path = config.paths.pattern_summary_csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{
        "pattern_id": p.pattern_id,
        "name": p.name,
        "category": p.category,
        "frequency": p.frequency,
        "keywords": ", ".join(p.keywords_matched[:5]),
        "example_quote": p.example_quotes[0] if p.example_quotes else "",
    } for p in patterns])
    df.to_csv(csv_path, index=False)
    logger.info("Saved pattern summary CSV", path=str(csv_path))
    
    return patterns


def enhance_with_topic_analysis(
    patterns: List[QuantumPattern],
    topics: List[TopicInfo],
    doc_topics: List[DocTopic],
    issues: List[CleanedIssue],
) -> List[QuantumPattern]:
    """Enriquece los patrones con información del modelo de temas."""
    # Mapea issue_id -> topic_id
    issue_to_topic = {dt.issue_id: dt.topic_id for dt in doc_topics}
    
    # Mapea topic_id -> información del tema
    topic_map = {t.topic_id: t for t in topics}
    # Los temas de un solo proyecto no son evidencia de un patrón entre proyectos (S24).
    repo_specific = {t.topic_id for t in topics if t.repo_specific}

    # Para cada patrón, busca los temas asociados
    for pattern in patterns:
        topic_counts = Counter()
        for issue_id in pattern.supporting_issue_ids:
            topic_id = issue_to_topic.get(issue_id, -1)
            if topic_id != -1 and topic_id not in repo_specific:
                topic_counts[topic_id] += 1
        pattern.topic_share = (
            sum(topic_counts.values()) / len(pattern.supporting_issue_ids)
            if pattern.supporting_issue_ids else 0.0
        )
        
        # Agrega los temas principales a la descripción del patrón
        if topic_counts:
            top_topics = topic_counts.most_common(3)
            topic_names = [topic_map[tid].name for tid, _ in top_topics if tid in topic_map]
            if topic_names:
                pattern.description += f" Associated topics: {', '.join(topic_names)}."
    
    return patterns


def find_candidate_categories(
    matched_issue_ids: Set[str],
    topics: List[TopicInfo],
    doc_topics: List[DocTopic],
    min_share: float = 0.5,
) -> List[Dict[str, Any]]:
    """Temas donde menos de ``min_share`` de los documentos coincide con alguna categoría de la taxonomía."""
    members: Dict[int, List[str]] = defaultdict(list)
    for dt in doc_topics:
        if dt.topic_id != -1:
            members[dt.topic_id].append(dt.issue_id)
    candidates = []
    for topic in topics:
        if topic.repo_specific:
            continue  # a single-project topic is not a cross-project category candidate (S24)
        ids = members.get(topic.topic_id, [])
        share = sum(1 for i in ids if i in matched_issue_ids) / len(ids) if ids else 0.0
        if share < min_share:
            candidates.append({
                "topic_id": topic.topic_id, "name": topic.name, "keywords": topic.keywords,
                "count": topic.count, "matched_share": share,
            })
    return candidates


if __name__ == "__main__":
    import typer
    from .config import load_config
    
    cfg = load_config(Path("config.yaml"))
    patterns = extract_quantum_patterns(cfg, cfg.paths.topics_output, cfg.paths.processed_data, cfg.paths.patterns_output)
    print(f"Extracted {len(patterns)} patterns")