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
        assert "hardware_backend" in patterns
        assert "algorithm_convergence" in patterns
        assert "transpilation_compilation" in patterns
        # Each category should have (keyword, pattern) tuples
        assert len(patterns["hardware_backend"]) > 0
        assert all(isinstance(p, tuple) for p in patterns["hardware_backend"])


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