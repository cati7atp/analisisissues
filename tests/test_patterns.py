"""Tests for patterns module."""

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
    """Sample issues for pattern testing."""
    issues = []
    
    # Hardware backend issue
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
    
    # Transpilation issue
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
    
    # Gradient issue
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
    
    # Dependency issue
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
        
        # Check that hardware pattern was found
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
        # Each pattern should have required fields
        for p in patterns:
            assert p.pattern_id
            assert p.name
            assert p.frequency > 0
            assert len(p.supporting_issue_ids) > 0


class TestExtractQuantumPatterns:
    def test_end_to_end(self, config, sample_issues, tmp_path):
        # Write sample issues to JSONL
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
        
        # Create empty topics file
        topics_file = tmp_path / "topics.jsonl"
        topics_file.touch()
        
        output_file = tmp_path / "patterns.jsonl"
        patterns = extract_quantum_patterns(config, topics_file, issues_file, output_file)
        
        assert len(patterns) > 0
        assert output_file.exists()
        
        # Verify CSV was created
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
