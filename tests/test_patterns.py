"""Tests del módulo patterns."""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from src.config import load_config
from src.models import CleanedIssue, CleanedComment
from src.patterns import (
    extract_quantum_patterns, build_keyword_patterns,
    extract_quotes, find_pattern_matches, aggregate_patterns,
)


@pytest.fixture
def sample_issues():
    """Issues de ejemplo para probar patrones."""
    issues = []
    
    # Issue de backend de hardware
    issues.append(CleanedIssue(
        repo="test/qiskit-test",
        issue_number=1,
        title="VQE fails on IBM Quantum hardware",
        body="When running VQE on IBM Quantum hardware, calibration drift causes convergence failure. Simulator works fine.",
        cleaned_body="When running VQE on IBM Quantum hardware, calibration drift causes convergence failure. Simulator works fine.",
        state="open",
        labels=["bug"],
        created_at=datetime(2024, 1, 15),
        closed_at=None,
        author="user1",
        comments=[],
        issue_type="bug",
        full_text="VQE fails on IBM Quantum hardware When running VQE on IBM Quantum hardware, calibration drift causes convergence failure. Simulator works fine.",
    ))
    
    # Issue de transpilación
    issues.append(CleanedIssue(
        repo="test/qiskit-test",
        issue_number=2,
        title="Transpilation error with coupling map",
        body="Transpilation fails due to routing issues with the coupling map. Stochastic swap not working.",
        cleaned_body="Transpilation fails due to routing issues with the coupling map. Stochastic swap not working.",
        state="closed",
        labels=["bug"],
        created_at=datetime(2024, 1, 10),
        closed_at=datetime(2024, 1, 20),
        author="user2",
        comments=[],
        issue_type="bug",
        full_text="Transpilation error with coupling map Transpilation fails due to routing issues with the coupling map. Stochastic swap not working.",
    ))
    
    # Issue de gradientes
    issues.append(CleanedIssue(
        repo="test/pennylane-test",
        issue_number=3,
        title="Gradient computation fails",
        body="Parameter-shift gradient calculation gives wrong results with JAX backend. Adjoint differentiation not supported.",
        cleaned_body="Parameter-shift gradient calculation gives wrong results with JAX backend. Adjoint differentiation not supported.",
        state="open",
        labels=["bug"],
        created_at=datetime(2024, 2, 1),
        closed_at=None,
        author="user3",
        comments=[],
        issue_type="bug",
        full_text="Gradient computation fails Parameter-shift gradient calculation gives wrong results with JAX backend. Adjoint differentiation not supported.",
    ))
    
    # Issue de dependencias
    issues.append(CleanedIssue(
        repo="test/qiskit-test",
        issue_number=4,
        title="Version conflict with numpy",
        body="qiskit-terra 0.45 requires numpy < 1.24 but project needs numpy 1.26. Dependency hell.",
        cleaned_body="qiskit-terra 0.45 requires numpy < 1.24 but project needs numpy 1.26. Dependency hell.",
        state="closed",
        labels=["bug"],
        created_at=datetime(2024, 1, 5),
        closed_at=datetime(2024, 1, 8),
        author="user4",
        comments=[],
        issue_type="bug",
        full_text="Version conflict with numpy qiskit-terra 0.45 requires numpy < 1.24 but project needs numpy 1.26. Dependency hell.",
    ))
    
    return issues


class TestExtractQuotes:
    def test_extracts_matching_quotes(self):
        text = "The VQE algorithm fails on hardware. Simulator works fine. Calibration is needed."
        quotes = extract_quotes(text, ["VQE", "calibration"], max_quotes=2, max_length=200)
        assert len(quotes) >= 1
        assert any("VQE" in q for q in quotes)

    def test_truncates_long_quotes(self):
        long_text = "A" * 300 + " VQE fails. " + "B" * 300
        quotes = extract_quotes(long_text, ["VQE"], max_quotes=1, max_length=50)
        assert len(quotes) == 1
        assert len(quotes[0]) <= 53  # 50 + "..."

    def test_no_matches(self):
        text = "Nothing relevant here"
        quotes = extract_quotes(text, ["VQE", "QAOA"], max_quotes=3, max_length=200)
        assert len(quotes) == 0


class TestBuildKeywordPatterns:
    def test_builds_patterns_from_config(self, config):
        patterns = build_keyword_patterns(config)
        assert {"hardware_backend", "algorithm_convergence", "transpilation_compilation"} <= set(patterns.names)
        assert "hardware_backend" in patterns.names


class TestFindPatternMatches:
    def test_finds_matches(self, config, sample_issues):
        keyword_patterns = build_keyword_patterns(config)
        matches = find_pattern_matches(sample_issues, keyword_patterns, config)
        assert len(matches) > 0
        
        # Comprueba que se encontró el patrón de hardware
        categories = {m.category for m in matches}
        assert "hardware_backend" in categories or "algorithm_convergence" in categories

    def test_no_matches_for_unrelated(self, config):
        issue = CleanedIssue(
            repo="test/test",
            issue_number=99,
            title="UI button color",
            body="The button should be blue not red.",
            cleaned_body="The button should be blue not red.",
            state="open",
            labels=["ui"],
            created_at=datetime(2024, 1, 1),
            closed_at=None,
            author="user",
            comments=[],
            issue_type="feature",
            full_text="UI button color The button should be blue not red.",
        )
        keyword_patterns = build_keyword_patterns(config)
        matches = find_pattern_matches([issue], keyword_patterns, config)
        assert len(matches) == 0


class TestAggregatePatterns:
    def test_aggregates_by_category(self, config, sample_issues):
        keyword_patterns = build_keyword_patterns(config)
        matches = find_pattern_matches(sample_issues, keyword_patterns, config)
        patterns = aggregate_patterns(matches)
        
        assert len(patterns) > 0
        # Cada patrón debe tener los campos requeridos
        for p in patterns:
            assert p.pattern_id
            assert p.name
            assert p.frequency > 0
            assert len(p.supporting_issue_ids) > 0


class TestExtractQuantumPatterns:
    def test_end_to_end(self, config, sample_issues, tmp_path):
        # Escribe los issues de ejemplo en JSONL
        issues_file = tmp_path / "issues.jsonl"
        with open(issues_file, "w") as f:
            for issue in sample_issues:
                data = issue.model_dump()
                data["created_at"] = issue.created_at.isoformat()
                if issue.closed_at:
                    data["closed_at"] = issue.closed_at.isoformat()
                for c in data["comments"]:
                    c["created_at"] = c["created_at"].isoformat()
                f.write(json.dumps(data) + "\n")
        
        # Crea un archivo de temas vacío
        topics_file = tmp_path / "topics.jsonl"
        topics_file.touch()
        
        output_file = tmp_path / "patterns.jsonl"
        patterns = extract_quantum_patterns(config, topics_file, issues_file, output_file)
        
        assert len(patterns) > 0
        assert output_file.exists()
        
        # Verifica que se creó el CSV
        csv_path = config.paths.pattern_summary_csv
        assert csv_path.exists() or Path("reports/pattern_summary.csv").exists()

def _taxonomy(tmp_path, body):
    path = tmp_path / "taxonomy.yaml"
    path.write_text(body, encoding="utf-8")
    return path


class TestTaxonomyMatcher:
    def test_terms_are_anchored_and_accept_plurals(self, tmp_path):
        from src.taxonomy import TaxonomyMatcher, load_taxonomy

        matcher = TaxonomyMatcher(load_taxonomy(_taxonomy(tmp_path, (
            "version: 1\ncategories:\n  gates:\n    name: Gates\n    terms: [gate]\n"))))
        assert matcher.match("We should investigate this") == {}
        assert matcher.match("Two gates fail") == {"gates": ["gate"]}
        assert matcher.match("The GATE is wrong") == {"gates": ["gate"]}

    def test_negative_terms_veto_a_category(self, tmp_path):
        from src.taxonomy import TaxonomyMatcher, load_taxonomy

        matcher = TaxonomyMatcher(load_taxonomy(_taxonomy(tmp_path, (
            "version: 1\ncategories:\n  noise:\n    name: Noise\n    terms: [noise model]\n"
            "    negative_terms: [log noise]\n"))))
        assert matcher.match("the noise model is wrong") == {"noise": ["noise model"]}
        assert matcher.match("the noise model has log noise") == {}

    def test_default_taxonomy_loads_with_generic_words_not_standalone(self, config):
        from src.taxonomy import TaxonomyMatcher, load_taxonomy

        taxonomy = load_taxonomy(config.quantum_taxonomy)
        assert taxonomy.version >= 1 and len(taxonomy.categories) >= 10
        matcher = TaxonomyMatcher(taxonomy)
        for text in ["the circuit", "a gate", "the backend", "memory", "performance"]:
            assert matcher.match(text) == {}, text
        assert "transpilation_compilation" in matcher.match("transpile fails with a coupling map")


class TestMetricsParity:
    def test_metrics_and_patterns_report_the_same_prevalence(self, config, sample_issues):
        from src.metrics import compute_quantum_keyword_ratios

        matcher = build_keyword_patterns(config)
        patterns = aggregate_patterns(find_pattern_matches(sample_issues, matcher, config), matcher.names)
        ratios = compute_quantum_keyword_ratios(sample_issues, config)
        assert set(ratios) == set(matcher.names)
        from_patterns = {p.category: p.frequency / len(sample_issues) for p in patterns}
        assert from_patterns and all(ratios[c] == pytest.approx(r) for c, r in from_patterns.items())
        assert all(ratios[c] == 0.0 for c in set(ratios) - set(from_patterns))

    def test_metrics_ignore_generic_substrings(self, config):
        from src.metrics import compute_quantum_keyword_ratios

        issue = CleanedIssue(
            repo="a/b", issue_number=1, title="investigate", cleaned_body="", state="open",
            created_at=datetime(2024, 1, 1), author="u", full_text="we should investigate the nonexistent seedling",
        )
        assert sum(compute_quantum_keyword_ratios([issue], config).values()) == 0.0


def _issue(n, text):
    return CleanedIssue(repo="a/b", issue_number=n, title=text, cleaned_body="", state="open",
                        created_at=datetime(2024, 1, 1), author="u", full_text=text)


class TestTopicIntegration:
    def _write(self, tmp_path, issues, assignments, topics):
        issues_file = tmp_path / "issues.jsonl"
        with open(issues_file, "w", encoding="utf-8") as f:
            for issue in issues:
                data = issue.model_dump()
                data["created_at"] = issue.created_at.isoformat()
                f.write(json.dumps(data) + "\n")
        doc_topics = tmp_path / "doc_topics.jsonl"
        doc_topics.write_text("\n".join(
            json.dumps({"issue_id": i.issue_id, "topic_id": t, "probability": 1.0})
            for i, t in zip(issues, assignments)) + "\n", encoding="utf-8")
        topics_file = tmp_path / "topics.jsonl"
        topics_file.write_text("\n".join(
            json.dumps({"topic_id": tid, "name": f"{tid}_x", "keywords": kw, "count": c,
                        "repo_specific": bool(rest and rest[0])})
            for tid, kw, c, *rest in topics) + "\n", encoding="utf-8")
        return issues_file, topics_file, doc_topics

    def test_patterns_report_topic_share_and_uncovered_topics_are_candidates(self, config, tmp_path):
        issues = [_issue(1, "transpile fails"), _issue(2, "transpiler crash"), _issue(3, "transpile slow"),
                  _issue(4, "pulse schedule broken"), _issue(5, "tea recipe"), _issue(6, "coffee recipe"),
                  _issue(7, "lunch menu")]
        files = self._write(tmp_path, issues, [0, 0, 0, -1, 1, 1, 1],
                            [(0, ["transpile"], 3), (1, ["recipe", "menu"], 3)])
        out = tmp_path / "patterns.jsonl"
        patterns = extract_quantum_patterns(config, files[1], files[0], out, doc_topics_path=files[2])
        by_cat = {p.category: p for p in patterns}
        assert by_cat["transpilation_compilation"].topic_share == 1.0
        assert by_cat["pulse_control"].topic_share == 0.0  # su único documento es un outlier
        candidates = [json.loads(l) for l in (tmp_path / "candidate_categories.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [c["topic_id"] for c in candidates] == [1]
        assert candidates[0]["keywords"] == ["recipe", "menu"] and candidates[0]["matched_share"] == 0.0

    def test_repo_specific_topics_are_not_cross_project_evidence(self, config, tmp_path):
        issues = [_issue(1, "transpile fails"), _issue(2, "transpiler crash"), _issue(3, "transpile slow"),
                  _issue(4, "pyrpl lockbox"), _issue(5, "pyrpl scope"), _issue(6, "pyrpl asg")]
        files = self._write(tmp_path, issues, [0, 0, 1, 2, 2, 2],
                            [(0, ["transpile"], 2, True), (1, ["transpile", "slow"], 1), (2, ["pyrpl"], 3, True)])
        patterns = extract_quantum_patterns(config, files[1], files[0], tmp_path / "p.jsonl", doc_topics_path=files[2])
        pattern = {p.category: p for p in patterns}["transpilation_compilation"]
        assert pattern.topic_share == pytest.approx(1 / 3)  # solo el tema 1 es entre proyectos
        assert "0_x" not in pattern.description and "1_x" in pattern.description
        candidates = [json.loads(l) for l in (tmp_path / "candidate_categories.jsonl").read_text(encoding="utf-8").splitlines()]
        assert 2 not in [c["topic_id"] for c in candidates]  # un tema de un solo proyecto no es una categoría nueva

    def test_without_doc_topics_patterns_still_run(self, config, tmp_path):
        files = self._write(tmp_path, [_issue(1, "transpile fails")], [0], [(0, ["transpile"], 1)])
        files[2].unlink()
        patterns = extract_quantum_patterns(config, files[1], files[0], tmp_path / "p.jsonl", doc_topics_path=files[2])
        assert patterns and patterns[0].topic_share is None
        assert not (tmp_path / "candidate_categories.jsonl").exists()
