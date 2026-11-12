from src.report import anonymize_repo_name, generate_cross_project_section, load_cross_project


def _row(tid, cross, top="big/repo"):
    return {"topic_id": tid, "cross_project": cross, "keywords": ["pulse", "schedule"], "supporting_repos": ["a", "b", "c"],
            "n_issues": 40, "top_repo": top, "top_repo_share": 0.5, "evenness": 0.9}


def test_section_lists_only_qualifying_topics_and_states_the_thresholds(config):
    text = generate_cross_project_section([_row(1, True), _row(2, False)], anonymize=False, config=config)
    assert "**1 of 2 topics qualify.**" in text
    assert "at least 3 repositories each hold 3 or more" in text and "90%" in text
    assert "| 1 | pulse, schedule |" in text and "| 2 |" not in text


def test_section_anonymizes_repo_names(config):
    text = generate_cross_project_section([_row(1, True)], anonymize=True, config=config)
    assert "big/repo" not in text and anonymize_repo_name("big/repo") in text


def test_missing_file_gives_no_rows(tmp_path):
    assert load_cross_project(tmp_path / "nope.jsonl") == []
