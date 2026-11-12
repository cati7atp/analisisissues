"""Coherencia del contenido del informe: los números salen de los datos, no del texto."""

from src.models import (
    AggregatedMetrics,
    MaintainabilityMetrics,
    QuantumPattern,
    RepoMetrics,
)
from src.report import (
    format_outcomes,
    generate_comparative_discussion,
    generate_conclusions,
    generate_executive_summary,
    generate_metrics_section,
)


def _metrics(outcomes=None, per_repo=None):
    return MaintainabilityMetrics(
        per_repo=per_repo or [],
        aggregated=AggregatedMetrics(
            total_repos=1,
            total_issues=10,
            resolution_outcomes=outcomes or {},
        ),
    )


def _repo(outcomes):
    return RepoMetrics(
        repo="a/b",
        total_issues=10,
        open_issues=3,
        closed_issues=7,
        issue_types={"bug": 10},
        resolution_outcomes=outcomes,
    )


def _pattern(index):
    return QuantumPattern(
        pattern_id=f"p{index}",
        name=f"Pattern {index}",
        description="descripción",
        category="categoría",
        supporting_issue_ids=[],
        frequency=1,
    )


def test_executive_summary_counts_the_patterns_it_receives():
    text = generate_executive_summary(_metrics(), [_pattern(i) for i in range(3)])

    assert "3 distinct categories" in text
    assert "eight" not in text


def test_executive_summary_renders_outcomes_without_python_dict_syntax():
    text = generate_executive_summary(
        _metrics({"completed": 7, "duplicate": 1, "not_planned": 2}), []
    )

    assert "Resolution Outcomes (closed issues)**: completed: 7, not planned: 2, duplicate: 1" in text
    assert "{'" not in text


def test_metrics_section_renders_outcomes_without_python_dict_syntax():
    text = generate_metrics_section(_metrics({"completed": 7}), anonymize=False)

    assert "| Resolution Outcomes (closed) | completed: 7 |" in text
    assert "{'" not in text


def test_per_repository_table_renders_outcomes_without_python_dict_syntax():
    metrics = _metrics(per_repo=[_repo({"completed": 5, "duplicate": 2})])

    text = generate_metrics_section(metrics, anonymize=False)

    assert "completed: 5, duplicate: 2" in text
    assert "{'" not in text


def test_comparative_discussion_reports_the_topic_count_it_is_given():
    text = generate_comparative_discussion(_metrics(), [], n_topics=162)

    assert "discovered 162 topics" in text
    assert "dominant thematic clusters" not in text


def test_conclusions_count_the_patterns_they_receive():
    text = generate_conclusions(_metrics(), [_pattern(i) for i in range(4)])

    assert "4 categories of quantum-specific issues" in text
    assert "Eight" not in text


def test_format_outcomes_orders_by_count_and_handles_no_closures():
    assert format_outcomes({"duplicate": 1, "completed": 7, "not_planned": 2}) == (
        "completed: 7, not planned: 2, duplicate: 1"
    )
    assert format_outcomes({}) == "N/A"
