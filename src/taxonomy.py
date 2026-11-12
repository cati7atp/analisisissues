"""Taxonomía versionada de patrones cuánticos y el único matcher compartido por patrones y métricas (S21, S22)."""

import re
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field


class CategorySpec(BaseModel):
    name: str
    terms: List[str]
    negative_terms: List[str] = Field(default_factory=list)


class Taxonomy(BaseModel):
    version: int
    categories: Dict[str, CategorySpec]


def load_taxonomy(path: Path) -> Taxonomy:
    with open(path, "r", encoding="utf-8") as f:
        return Taxonomy(**yaml.safe_load(f))


def _alternation(terms: List[str]) -> "re.Pattern":
    """Una alternancia sin distinguir mayúsculas; cada término va en su propio grupo para saber cuál coincidió."""
    body = "|".join(f"({re.escape(t.lower())})" for t in terms)
    return re.compile(rf"\b(?:{body})(?:s|es)?\b", re.IGNORECASE)


class TaxonomyMatcher:
    """Matcher compilado con límites de palabra, una alternancia por categoría."""

    def __init__(self, taxonomy: Taxonomy) -> None:
        self.taxonomy = taxonomy
        self.names = {cid: spec.name for cid, spec in taxonomy.categories.items()}
        self._terms = {cid: [t.lower() for t in spec.terms] for cid, spec in taxonomy.categories.items()}
        self._positive = {cid: _alternation(spec.terms) for cid, spec in taxonomy.categories.items()}
        self._negative = {
            cid: _alternation(spec.negative_terms)
            for cid, spec in taxonomy.categories.items() if spec.negative_terms
        }

    def match(self, text: str) -> Dict[str, List[str]]:
        """Devuelve {categoría: términos encontrados} para las categorías que coinciden con ``text``."""
        found: Dict[str, List[str]] = {}
        if not text:
            return found
        for cid, pattern in self._positive.items():
            hits = {self._terms[cid][m.lastindex - 1] for m in pattern.finditer(text)}
            if not hits:
                continue
            negative = self._negative.get(cid)
            if negative is not None and negative.search(text):
                continue
            found[cid] = sorted(hits)
        return found
