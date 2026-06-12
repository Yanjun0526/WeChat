from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

import stage4_pipeline as s4  # noqa: E402
from stage4_pipeline import (  # noqa: E402
    CANONICAL_TOPIC_SCORE_COLUMNS,
    CANONICAL_TOPICS,
    build_level1_content_master,
    build_level2_agent_network_master,
    build_level3_agent_topic_match_master,
    build_master_from_frames,
    check_source_readiness,
    cleanup_legacy_outputs,
    derive_analysis_variables,
    duplicate_key_report,
    make_descriptive_tables,
    make_join_quality_tables,
    create_level_figures,
    run_level1_content_analysis,
    run_level2_agent_network_analysis,
    run_level3_agent_topic_matching_analysis,
    run_group_tests,
    run_regressions,
    validate_master,
    write_findings_summary,
    write_variable_role_map,
    write_notebook,
)


def test_build_master_normalizes_keys_and_preserves_agent_article_rows():
    final = pd.DataFrame(
        {
            "agent_name": [" Alice ", "Bob"],
            "article_title": ["装修A", "推广B"],
            "Title": ["装修A", "推广B"],
            "first_layer_width": [2, 1],
            "second_layer_width": [1, 0],
            "depth": [2, 1],
            "reshare_pct": [0.25, 0.0],
            "duration_mean_s": [10, 20],
            "structural_virality": [1.5, 1.0],
            "MatchScore": [0.7, 0.2],
            "ProfessionContentMatch": [1, 0],
        }
    )
    corrected = pd.DataFrame(
        {
            "agent_name": ["Alice", "Alice", "Alice", "Bob"],
            "article_title": ["装修A", "装修A", "装修A", "推广B"],
            "reader_wechat_nn": ["r1", "r2", "r3", "r4"],
            "reader_read": [1, 2, 1, 5],
            "correct_layer": [0, 1, 2, 1],
            "TopContentCluster": ["Home", "Home", "Home", "Promo"],
        }
    )
    content = pd.DataFrame(
        {
            "Title": ["装修A", "推广B"],
            "TopContentCluster": ["Home", "Promo"],
            "CosineSim": [0.8, 0.4],
            "EuclideanDist": [10, 40],
            "ManhattanDist": [20, 80],
        }
    )
    article_meta = pd.DataFrame(
        {
            "Title": ["装修A", "推广B"],
            "WordCount": [120, 60],
            "HasImage": ["Yes", "No"],
            "NumImages": [3, 0],
        }
    )
    agent_gender = pd.DataFrame(
        {"agent_name": ["Alice", "Bob"], "agent_gender": [1, 0]}
    )
    agent_dep_job = pd.DataFrame(
        {"agent": ["Alice", "Bob"], "agent_dep": ["Sales", "Design"]}
    )

    master = build_master_from_frames(
        final=final,
        corrected=corrected,
        content=content,
        article_meta=article_meta,
        agent_gender=agent_gender,
        agent_dep_job=agent_dep_job,
    )

    assert len(master) == 2
    assert master.loc[0, "cascade_size"] == 3
    assert master.loc[0, "total_reads"] == 4
    assert master.loc[0, "TopContentCluster"] == "Home"
    assert master.loc[0, "HasImage"] == 1
    assert master.loc[1, "agent_dep"] == "Design"


def test_build_master_prefers_exact_corrected_layer_keys_before_normalized_fallback():
    final = pd.DataFrame(
        {
            "agent_name": ["Agent", "Agent", " Agent "],
            "article_title": ["Same title", "Same title ", "Needs fallback"],
            "Title": ["Same title", "Same title ", "Needs fallback"],
            "first_layer_width": [1, 2, 1],
            "second_layer_width": [0, 0, 0],
            "depth": [1, 1, 1],
            "reshare_pct": [0.0, 0.0, 0.0],
            "duration_mean_s": [10, 20, 30],
            "structural_virality": [1.0, 1.0, 1.0],
            "MatchScore": [0.2, 0.3, 0.4],
            "ProfessionContentMatch": [0, 0, 1],
        }
    )
    corrected = pd.DataFrame(
        {
            "agent_name": ["Agent", "Agent", "Agent", "Agent"],
            "article_title": ["Same title", "Same title ", "Same title ", "Needs fallback"],
            "reader_wechat_nn": ["r1", "r2", "r3", "r4"],
            "reader_read": [1, 2, 3, 4],
            "correct_layer": [1, 1, 2, 1],
            "TopContentCluster": ["A", "B", "B", "C"],
        }
    )
    content = pd.DataFrame(
        {
            "Title": ["Same title", "Same title ", "Needs fallback"],
            "TopContentCluster": ["A", "B", "C"],
            "CosineSim": [0.8, 0.7, 0.6],
            "EuclideanDist": [10, 20, 30],
            "ManhattanDist": [20, 30, 40],
        }
    )

    master = build_master_from_frames(final=final, corrected=corrected, content=content)

    assert master["cascade_size"].tolist() == [1, 2, 1]
    assert master["total_reads"].tolist() == [1, 5, 4]
    assert master["corrected_depth"].tolist() == [1, 2, 1]


def test_derive_variables_and_validate_master_rules():
    master = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "article_title": ["装修A", "推广B"],
            "cascade_size": [3, 1],
            "total_reads": [4, 5],
            "depth": [2, 1],
            "second_layer_width": [1, 0],
            "reshare_pct": [0.25, 0.0],
            "duration_mean_s": [10.0, 10_000.0],
            "structural_virality": [1.5, 20.0],
            "wiener_index": [5.0, 100.0],
            "MatchScore": [0.7, 0.2],
            "ProfessionContentMatch": [1, 0],
        }
    )

    derived = derive_analysis_variables(master)

    assert derived["log_reach"].round(6).tolist() == pytest.approx(
        [1.386294, 0.693147]
    )
    assert derived["any_reshare"].tolist() == [1, 0]
    assert "duration_mean_s_winsorized" in derived
    assert "log_duration" in derived

    validation = validate_master(derived, expected_rows=2)
    assert validation["valid"]
    assert validation["checks"]["row_count"]["actual"] == 2

    bad = derived.copy()
    bad.loc[0, "MatchScore"] = 1.5
    with pytest.raises(ValueError, match="MatchScore"):
        validate_master(bad, expected_rows=2, raise_on_error=True)


def test_descriptive_decile_tables_are_sorted_numerically():
    master = pd.DataFrame(
        {
            "agent_name": [f"a{i}" for i in range(20)],
            "article_title": [f"t{i}" for i in range(20)],
            "cascade_size": range(1, 21),
            "depth": [1] * 20,
            "second_layer_width": [0] * 20,
            "reshare_pct": [0.0] * 20,
            "duration_mean_s": range(20),
            "duration_mean_s_winsorized": range(20),
            "structural_virality": [1.0] * 20,
            "structural_virality_winsorized": [1.0] * 20,
            "MatchScore": [i / 19 for i in range(20)],
            "CosineSim": [i / 19 for i in range(20)],
        }
    )
    master = derive_analysis_variables(master)

    tables = make_descriptive_tables(master)

    assert tables["cosine_deciles"]["CosineSimDecile"].tolist() == [
        f"D{i}" for i in range(1, 11)
    ]
    assert tables["matchscore_deciles"]["MatchScoreDecile"].tolist() == [
        f"D{i}" for i in range(1, 11)
    ]


def test_opportunity_matrix_reports_counts_and_suppresses_sparse_cells():
    master = pd.DataFrame(
        {
            "JobCategory": ["A"] * 5 + ["B"],
            "TopContentCluster": ["Topic1"] * 5 + ["Topic2"],
            "log_reach": [1, 2, 3, 4, 5, 10],
            "depth": [1, 1, 2, 2, 3, 4],
            "reshare_pct": [0.0, 0.1, 0.2, 0.1, 0.0, 1.0],
            "MatchScore": [0.1, 0.2, 0.3, 0.4, 0.5, 1.0],
        }
    )

    tables = make_descriptive_tables(master, min_opportunity_cell_n=3)

    long = tables["job_topic_opportunity_long"]
    sparse = long[(long["JobCategory"] == "B") & (long["TopContentCluster"] == "Topic2")].iloc[0]
    dense = long[(long["JobCategory"] == "A") & (long["TopContentCluster"] == "Topic1")].iloc[0]
    assert dense["cell_n"] == 5
    assert dense["is_sparse"] == 0
    assert sparse["cell_n"] == 1
    assert sparse["is_sparse"] == 1
    assert pd.isna(sparse["log_reach_mean_reportable"])
    assert "job_topic_opportunity_counts" in tables
    assert "job_topic_opportunity_depth" in tables
    assert "job_topic_opportunity_reshare" in tables
    assert "job_topic_opportunity_match" in tables


def test_group_tests_include_welch_games_howell_and_dunn_outputs():
    master = pd.DataFrame(
        {
            "TopContentCluster": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
            "JobCategory": ["J1"] * 15 + ["J2"] * 15,
            "ProfessionContentMatch": [0, 1] * 15,
            "log_reach": list(range(10)) + list(range(10, 20)) + list(range(20, 30)),
            "depth": [1] * 10 + [2] * 10 + [3] * 10,
            "reshare_pct": [0.0, 0.1, 0.2] * 10,
            "log_duration": list(range(30)),
            "structural_virality_winsorized": [1.0, 1.2, 1.4] * 10,
        }
    )

    tables = run_group_tests(master)

    assert {"welch_anova_summary", "games_howell_pairs", "dunn_pairs"}.issubset(tables)
    assert not tables["welch_anova_summary"].empty
    assert not tables["games_howell_pairs"].empty
    assert not tables["dunn_pairs"].empty
    assert "epsilon_squared" in tables["kruskal_summary"].columns


def test_regressions_include_negative_binomial_and_overdispersion_diagnostics():
    n = 80
    master = pd.DataFrame(
        {
            "_agent_key": [f"a{i % 10}" for i in range(n)],
            "agent_name": [f"a{i % 10}" for i in range(n)],
            "article_title": [f"t{i}" for i in range(n)],
            "cascade_size": [1 + (i % 5) * (i + 1) for i in range(n)],
            "second_layer_width": [i % 7 for i in range(n)],
            "any_reshare": [i % 2 for i in range(n)],
            "log_reach": [float(i % 9 + 1) for i in range(n)],
            "log_duration": [float(i % 11 + 1) for i in range(n)],
            "structural_virality_winsorized": [float(i % 6 + 1) for i in range(n)],
            "JobCategory": [str(i % 3) for i in range(n)],
            "TopContentCluster": [f"Topic{i % 3}" for i in range(n)],
            "CosineSim": [i / n for i in range(n)],
            "EuclideanDist": [float(i % 13) for i in range(n)],
            "ManhattanDist": [float(i % 17) for i in range(n)],
            "WordCount": [100 + i for i in range(n)],
            "HasImage": [i % 2 for i in range(n)],
            "NumImages": [i % 6 for i in range(n)],
            "MatchScore": [(i % 10) / 10 for i in range(n)],
            "ProfessionContentMatch": [i % 2 for i in range(n)],
            "agent_deg_centrality": [float(i % 8) for i in range(n)],
            "Home Design & Decoration(Title+Content)": [float(i % 100) for i in range(n)],
            "Events & Promotions(Title+Content)": [float((100 - i) % 100) for i in range(n)],
        }
    )

    tables = run_regressions(master)

    assert "overdispersion_diagnostics" in tables
    assert "negative_binomial_coefficients" in tables
    assert "distance_robustness_coefficients" in tables
    assert "interaction_diagnostics" in tables
    assert "topic_job_cell_counts" in tables
    assert not tables["overdispersion_diagnostics"].empty
    assert not tables["interaction_diagnostics"].empty
    assert not tables["topic_job_cell_counts"].empty
    assert (tables["model_summary"]["family"] == "negative_binomial").any()


def test_legacy_run_regressions_keeps_matching_specs_separate():
    n = 90
    master = pd.DataFrame(
        {
            "_agent_key": [f"a{i % 15}" for i in range(n)],
            "agent_name": [f"a{i % 15}" for i in range(n)],
            "article_title": [f"t{i}" for i in range(n)],
            "cascade_size": [1 + (i % 6) for i in range(n)],
            "second_layer_width": [i % 5 for i in range(n)],
            "any_reshare": [i % 2 for i in range(n)],
            "log_reach": [1.0 + (i % 12) * 0.1 for i in range(n)],
            "log_duration": [1.0 + (i % 9) * 0.1 for i in range(n)],
            "structural_virality_winsorized": [1.0 + (i % 8) * 0.1 for i in range(n)],
            "JobCategory": [str(i % 3) for i in range(n)],
            "TopContentCluster": [f"Topic{i % 3}" for i in range(n)],
            "CosineSim": [i / n for i in range(n)],
            "WordCount": [100 + i for i in range(n)],
            "HasImage": [i % 2 for i in range(n)],
            "NumImages": [i % 6 for i in range(n)],
            "MatchScore": [(i % 10) / 10 for i in range(n)],
            "ProfessionContentMatch": [i % 2 for i in range(n)],
            "agent_deg_centrality": [float(i % 8) for i in range(n)],
        }
    )

    tables = run_regressions(master)
    formulas = " ".join(tables["model_summary"].get("formula", pd.Series(dtype=str)).dropna().astype(str))
    coeff = tables["coefficients"]
    terms_by_model = coeff.groupby(["model", "outcome"])["term"].apply(set).reset_index()
    mixed_models = terms_by_model[
        terms_by_model["term"].map(
            lambda terms: ("MatchScore" in terms)
            and any(str(term).startswith("ProfessionContentMatch") for term in terms)
        )
    ]

    assert "MatchScore + ProfessionContentMatch" not in formulas
    assert mixed_models.empty


def test_topic_job_interaction_diagnostics_fit_non_sparse_full_rank_cells():
    n = 160
    master = pd.DataFrame(
        {
            "_agent_key": [f"a{i % 20}" for i in range(n)],
            "cascade_size": [1 + (i % 7) for i in range(n)],
            "second_layer_width": [i % 5 for i in range(n)],
            "any_reshare": [i % 2 for i in range(n)],
            "log_reach": [1.0 + (i % 13) * 0.1 for i in range(n)],
            "log_duration": [1.0 + (i % 17) * 0.1 for i in range(n)],
            "structural_virality_winsorized": [1.0 + (i % 11) * 0.1 for i in range(n)],
            "TopContentCluster": [f"Topic{(i // 40) % 2}" for i in range(n)],
            "JobCategory": [f"Job{(i // 20) % 2}" for i in range(n)],
            "CosineSim": [((i * 7) % 101) / 100 for i in range(n)],
            "EuclideanDist": [float((i * 5) % 29) for i in range(n)],
            "ManhattanDist": [float((i * 3) % 31) for i in range(n)],
            "WordCount": [100 + ((i * 11) % 97) for i in range(n)],
            "HasImage": [1 if i % 3 == 0 else 0 for i in range(n)],
            "NumImages": [i % 6 for i in range(n)],
            "MatchScore": [((i * 13) % 100) / 100 for i in range(n)],
            "ProfessionContentMatch": [i % 2 for i in range(n)],
        }
    )

    diagnostics = run_regressions(master)["interaction_diagnostics"]

    assert diagnostics.loc[0, "status"] != "error"
    assert diagnostics.loc[0, "status"] in {"fit", "skipped_rank_deficient"}


def test_duplicate_key_report_flags_conflicting_normalized_auxiliary_keys():
    df = pd.DataFrame(
        {
            "Title": ["Same", " Same "],
            "CosineSim": [0.1, 0.9],
            "WordCount": [10, 10],
        }
    )

    report = duplicate_key_report(df, key_col="Title", value_cols=["CosineSim", "WordCount"])

    assert len(report) == 1
    assert report.loc[0, "conflicting_columns"] == "CosineSim"


def test_join_quality_tables_report_conflicts_and_missing_reader_ids():
    inputs = {
        "content": pd.DataFrame(
            {
                "Title": ["Same", " Same "],
                "CosineSim": [0.1, 0.9],
                "TopContentCluster": ["A", "B"],
            }
        ),
        "article_meta": pd.DataFrame({"Title": ["Same"], "WordCount": [10]}),
        "agent_dep_job": pd.DataFrame({"agent": ["Alice"], "agent_dep": ["Sales"]}),
        "corrected": pd.DataFrame(
            {
                "agent_name": ["Alice", "Alice"],
                "article_title": ["Story", "Story"],
                "reader_wechat_nn": ["r1", None],
                "correct_layer": [1, 2],
            }
        ),
    }

    tables = make_join_quality_tables(inputs)

    assert "content_title_conflicts" in tables
    assert len(tables["content_title_conflicts"]) == 1
    assert tables["corrected_reader_id_missing"].loc[0, "missing_reader_wechat_nn_rows"] == 1
    assert "topic_label_standardization" in tables


def _minimal_readiness_inputs():
    final = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "article_title": ["Story A", "Story B"],
            "Title": ["Story A", "Story B"],
            "first_layer_width": [1, 2],
            "second_layer_width": [0, 1],
            "depth": [1, 2],
            "reshare_pct": [0.0, 0.5],
            "duration_mean_s": [10, 20],
            "structural_virality": [1.0, 1.5],
            "MatchScore": [0.8, 0.4],
            "ProfessionContentMatch": [1, 0],
            "JobCategory": ["Sales", "Design"],
        }
    )
    return {
        "final": final,
        "agent_level": pd.DataFrame(
            {
                "agent_name": ["Alice", "Bob"],
                "cascade_size_mean": [1.0, 3.0],
                "depth_mean": [1.0, 2.0],
                "reshare_mean": [0.0, 0.5],
            }
        ),
        "agent_topic": pd.DataFrame(
            {
                "agent_name": ["Alice", "Bob"],
                "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
                "cascade_size_mean": [1.0, 3.0],
            }
        ),
        "corrected": pd.DataFrame(
            {
                "agent_name": ["Alice", "Bob"],
                "article_title": ["Story A", "Story B"],
                "reader_wechat_nn": ["r1", "r2"],
                "reader_read": [1, 2],
                "correct_layer": [1, 2],
                "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
            }
        ),
        "content": pd.DataFrame(
            {
                "Title": ["Story A", "Story B"],
                "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
                "CosineSim": [0.8, 0.5],
                "EuclideanDist": [10, 20],
                "ManhattanDist": [20, 40],
            }
        ),
        "article_meta": pd.DataFrame(
            {
                "Title": ["Story A", "Story B"],
                "WordCount": [100, 200],
                "HasImage": ["Yes", "No"],
                "NumImages": [2, 0],
            }
        ),
        "agent_gender": pd.DataFrame({"agent_name": ["Alice", "Bob"], "agent_gender": [0, 1]}),
        "agent_dep_job": pd.DataFrame({"agent": ["Alice", "Bob"], "agent_dep": ["Sales", "Design"], "agent_job": ["Advisor", "Designer"]}),
    }


def test_source_readiness_gate_reports_required_checks_and_raises_on_errors():
    inputs = _minimal_readiness_inputs()
    tables = check_source_readiness(
        inputs,
        expected_rows={"final": 2, "agent_level": 2, "agent_topic": 2},
        raise_on_error=True,
    )

    assert "readiness_gate" in tables
    gate = tables["readiness_gate"]
    assert gate["ready_to_build"].all()
    assert {
        "source_required_columns",
        "row_count",
        "final_to_content_exact_title",
        "final_to_article_meta_exact_title",
        "agent_topic_primary_key_unique",
        "topic_label_standardization",
    }.issubset(set(gate["check"]))

    broken = _minimal_readiness_inputs()
    broken["content"] = broken["content"].iloc[[0]].copy()
    with pytest.raises(ValueError, match="final_to_content_exact_title"):
        check_source_readiness(
            broken,
            expected_rows={"final": 2, "agent_level": 2, "agent_topic": 2},
            raise_on_error=True,
        )

    unmapped = _minimal_readiness_inputs()
    unmapped["agent_topic"].loc[0, "TopContentCluster"] = "Unknown Topic"
    with pytest.raises(ValueError, match="topic_label_standardization"):
        check_source_readiness(
            unmapped,
            expected_rows={"final": 2, "agent_level": 2, "agent_topic": 2},
            raise_on_error=True,
        )


def test_write_notebook_uses_stage4_directory_fallback(tmp_path):
    notebook_path = tmp_path / "factor_analysis_stage4.ipynb"

    write_notebook(notebook_path)

    text = notebook_path.read_text(encoding="utf-8")
    assert "analysis(S4)" in text
    assert "sys.path.insert" in text
    assert "stage4_pipeline" in text
    assert "regenerate_notebook=False" in text


def test_three_level_master_builders_enforce_scope_and_english_topics():
    final = pd.DataFrame(
        {
            "agent_name": ["Alice", "Alice", "Bob"],
            "article_title": ["Story A", "Story B", "Story A"],
            "Title": ["Story A", "Story B", "Story A"],
            "first_layer_width": [2, 3, 1],
            "second_layer_width": [1, 0, 2],
            "depth": [2, 1, 3],
            "reshare_pct": [0.2, 0.0, 0.4],
            "duration_mean_s": [10, 20, 30],
            "structural_virality": [1.2, 1.0, 2.0],
            "wiener_index": [1.0, 1.1, 1.2],
            "centrality": [0.1, 0.2, 0.3],
            "agent_deg_centrality": [0.2, 0.2, 0.4],
            "avg_out_degree_centrality": [0.3, 0.3, 0.5],
            "gender_assortativity": [0.1, 0.1, 0.2],
            "gender_pct_aud_0": [0.4, 0.4, 0.8],
            "gender_pct_aud_1": [0.6, 0.6, 0.2],
            "JobCategory": [3, 3, 4],
            "agent_job": ["Advisor", "Advisor", "Designer"],
            "MatchScore": [0.8, 0.4, 0.6],
            "ProfessionContentMatch": [1, 0, 1],
        }
    )
    corrected = pd.DataFrame(
        {
            "agent_name": ["Alice", "Alice", "Alice", "Bob"],
            "article_title": ["Story A", "Story A", "Story B", "Story A"],
            "reader_wechat_nn": ["r1", "r2", "r3", "r4"],
            "reader_read": [1, 1, 2, 1],
            "correct_layer": [1, 2, 1, 1],
            "TopContentCluster": ["家居设计与装修", "家居设计与装修", "活动与促销", "家居设计与装修"],
        }
    )
    content = pd.DataFrame(
        {
            "Title": ["Story A", "Story B"],
            "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
            "Home Design & Decoration(Title+Content)": [80, 10],
            "Events & Promotions(Title+Content)": [20, 90],
            "CosineSim": [0.8, 0.5],
            "EuclideanDist": [10, 20],
            "ManhattanDist": [30, 40],
        }
    )
    article_meta = pd.DataFrame(
        {
            "Title": ["Story A", "Story B"],
            "WordCount": [100, 200],
            "HasImage": ["Yes", "No"],
            "NumImages": [2, 0],
        }
    )
    agent_level = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "cascade_size_mean": [2.5, 1.0],
            "depth_mean": [1.5, 3.0],
            "reshare_mean": [0.1, 0.4],
            "structural_virality_mean": [1.1, 2.0],
            "duration_mean_of_means": [15, 30],
            "agent_deg_centrality_mean": [0.2, 0.5],
            "avg_out_degree_centrality_mean": [0.3, 0.6],
            "gender_assortativity_mean": [0.1, 0.2],
            "repeat_exposure_1st_nodes_pct": [0.0, 0.1],
            "repeat_exposure_2nd_nodes_pct": [0.0, 0.2],
            "matchscore_mean": [0.6, 0.6],
            "profession_content_match_mean": [0.5, 1.0],
        }
    )
    agent_topic = pd.DataFrame(
        {
            "agent_name": ["Alice", "Alice", "Bob"],
            "TopContentCluster": ["家居设计与装修", "活动与促销", "家居设计与装修"],
            "cascade_size_mean": [2.0, 1.0, 3.0],
            "depth_mean": [2.0, 1.0, 3.0],
            "reshare_mean": [0.2, 0.0, 0.4],
            "structural_virality_mean": [1.2, 1.0, 2.0],
            "duration_mean_of_means": [10, 20, 30],
            "agent_deg_centrality_mean": [0.2, 0.2, 0.5],
            "avg_out_degree_centrality_mean": [0.3, 0.3, 0.6],
            "centrality_mean": [0.2, 0.2, 0.5],
        }
    )
    agent_gender = pd.DataFrame({"agent_name": ["Alice", "Bob"], "agent_gender": [0, 1]})
    agent_dep_job = pd.DataFrame(
        {
            "agent": ["Alice", "Bob"],
            "agent_dep": ["Sales Dept", "Design Dept"],
            "agent_job": ["Advisor", "Designer"],
        }
    )

    level1 = build_level1_content_master(
        final=final,
        corrected=corrected,
        content=content,
        article_meta=article_meta,
    )
    level2 = build_level2_agent_network_master(
        agent_level=agent_level,
        final=final,
        agent_gender=agent_gender,
        agent_dep_job=agent_dep_job,
    )
    level3 = build_level3_agent_topic_match_master(
        agent_topic=agent_topic,
        final=final,
        content=content,
        article_meta=article_meta,
        agent_gender=agent_gender,
        agent_dep_job=agent_dep_job,
    )

    assert len(level1) == 3
    assert set(level1["TopContentCluster"]).issubset(CANONICAL_TOPICS)
    assert "MatchScore" not in level1.columns
    assert "ProfessionContentMatch" not in level1.columns
    assert "JobCategory" not in level1.columns
    assert "centrality" not in level1.columns
    assert "agent_deg_centrality" not in level1.columns
    assert "avg_out_degree_centrality" not in level1.columns
    assert "gender_assortativity" not in level1.columns
    assert "gender_pct_aud_0" not in level1.columns
    assert not any(str(column).endswith("_content") for column in level1.columns)
    assert not any("(Content)" in str(column) or "(Title+Content)" in str(column) for column in level1.columns)

    assert level2["agent_name"].nunique() == 2
    assert "article_count_per_agent" in level2.columns
    assert "log_article_count_per_agent" in level2.columns
    assert "log_agent_cascade_size_mean" in level2.columns
    assert "matchscore_mean" not in level2.columns
    assert "profession_content_match_mean" not in level2.columns

    assert set(level3["TopContentCluster"]).issubset(CANONICAL_TOPICS)
    assert level3[["agent_name", "TopContentCluster"]].duplicated().sum() == 0
    for column in [
        "MatchScore_mean",
        "ProfessionContentMatch_mean",
        "log_agent_topic_article_n",
        "WordCount_mean",
        "HasImage_share",
        "NumImages_mean",
        "CosineSim_mean",
        "log_agent_topic_cascade_size_mean",
    ]:
        assert column in level3.columns


def test_level3_matching_models_are_separate():
    n = 72
    df = pd.DataFrame(
        {
            "agent_name": [f"a{i % 12}" for i in range(n)],
            "TopContentCluster": [list(CANONICAL_TOPICS)[i % 3] for i in range(n)],
            "JobCategory": [f"J{i % 3}" for i in range(n)],
            "agent_gender": [i % 2 for i in range(n)],
            "log_agent_topic_cascade_size_mean": [1.0 + (i % 10) * 0.1 for i in range(n)],
            "depth_mean": [1 + i % 5 for i in range(n)],
            "reshare_mean": [(i % 10) / 10 for i in range(n)],
            "second_layer_width_avg": [i % 7 for i in range(n)],
            "structural_virality_mean": [1.0 + (i % 8) * 0.1 for i in range(n)],
            "duration_mean_of_means": [10 + i for i in range(n)],
            "wiener_index_mean": [3 + (i % 9) * 0.3 for i in range(n)],
            "centrality_mean": [(i % 12) / 100 for i in range(n)],
            "agent_deg_centrality_mean": [(i % 15) / 100 for i in range(n)],
            "avg_out_degree_centrality_mean": [(i % 18) / 100 for i in range(n)],
            "MatchScore_mean": [((i * 7) % 100) / 100 for i in range(n)],
            "ProfessionContentMatch_mean": [1.0 if i % 3 == 0 else 0.0 for i in range(n)],
            "log_agent_topic_article_n": [1.0 + (i % 5) * 0.1 for i in range(n)],
            "WordCount_mean": [100 + i for i in range(n)],
            "HasImage_share": [0.5 if i % 2 else 1.0 for i in range(n)],
            "NumImages_mean": [i % 6 for i in range(n)],
            "CosineSim_mean": [0.3 + (i % 10) * 0.05 for i in range(n)],
            "agent_topic_article_n": [10 + i % 6 for i in range(n)],
            "is_sparse_cell_10": [0] * n,
            "is_sparse_cell_30": [0] * n,
        }
    )

    tables = run_level3_agent_topic_matching_analysis(df)
    formulas = " ".join(tables["model_summary"]["formula"].astype(str))
    modeled_outcomes = set(tables["model_summary"]["outcome"])

    assert "level3_model_a_matchscore" in set(tables["model_summary"]["model"])
    assert "level3_model_b_profession_match" in set(tables["model_summary"]["model"])
    assert "MatchScore_mean + ProfessionContentMatch_mean" not in formulas
    assert {
        "depth_mean",
        "reshare_mean",
        "structural_virality_mean",
        "wiener_index_mean",
        "centrality_mean",
        "agent_deg_centrality_mean",
    }.issubset(modeled_outcomes)
    assert "level3_matchscore_centrality_moderation" not in set(tables["model_summary"]["model"])
    rhs_text = " ".join(
        formula.split("~", 1)[1]
        for formula in tables["model_summary"]["formula"].dropna().astype(str)
        if "~" in formula
    )
    for forbidden_rhs in [
        "agent_deg_centrality_mean",
        "avg_out_degree_centrality_mean",
        "centrality_mean",
        "wiener_index_mean",
        "structural_virality_mean",
        "depth_mean",
    ]:
        assert forbidden_rhs not in rhs_text
    for model_name in [
        "level3_model_a_matchscore_weighted",
        "level3_model_b_profession_match_weighted",
        "level3_model_a_matchscore_n_ge_10",
        "level3_model_b_profession_match_n_ge_10",
    ]:
        assert model_name in set(tables["model_summary"]["model"])


def test_level1_analysis_includes_topic_and_distance_robustness():
    n = 90
    df = pd.DataFrame(
        {
            "agent_name": [f"a{i % 12}" for i in range(n)],
            "article_title": [f"story{i}" for i in range(n)],
            "TopContentCluster": [list(CANONICAL_TOPICS)[i % 3] for i in range(n)],
            "log_reach": [1.0 + (i % 15) * 0.1 for i in range(n)],
            "log_duration": [2.0 + (i % 11) * 0.08 for i in range(n)],
            "structural_virality_winsorized": [1.0 + (i % 7) * 0.05 for i in range(n)],
            "any_reshare": [i % 2 for i in range(n)],
            "cascade_size": [1 + i % 20 for i in range(n)],
            "second_layer_width": [i % 8 for i in range(n)],
            "depth": [1 + i % 4 for i in range(n)],
            "wiener_index_winsorized": [5.0 + (i % 9) * 0.2 for i in range(n)],
            "centrality": [(i % 11) / 100 for i in range(n)],
            "agent_deg_centrality": [(i % 13) / 100 for i in range(n)],
            "avg_out_degree_centrality": [(i % 17) / 100 for i in range(n)],
            "CosineSim": [0.25 + (i % 20) * 0.02 for i in range(n)],
            "EuclideanDist": [5 + i % 30 for i in range(n)],
            "ManhattanDist": [8 + i % 35 for i in range(n)],
            "WordCount": [100 + i for i in range(n)],
            "HasImage": [i % 2 for i in range(n)],
            "NumImages": [i % 5 for i in range(n)],
        }
    )
    for index, column in enumerate(CANONICAL_TOPIC_SCORE_COLUMNS):
        df[column] = [((i + index * 3) % 100) / 100 for i in range(n)]

    tables = run_level1_content_analysis(df)
    models = set(tables["model_summary"]["model"])

    assert "level1_content_main" in models
    assert "level1_topic_score_robustness" in models
    assert "level1_topic_pca_robustness" in models
    assert "level1_distance_robustness_euclidean" in models
    assert "level1_distance_robustness_manhattan" in models
    modeled_outcomes = set(tables["model_summary"]["outcome"])
    assert {
        "depth",
        "structural_virality_winsorized",
        "wiener_index_winsorized",
    }.issubset(modeled_outcomes)
    assert {
        "centrality",
        "agent_deg_centrality",
        "avg_out_degree_centrality",
    }.isdisjoint(modeled_outcomes)
    rhs_text = " ".join(
        formula.split("~", 1)[1]
        for formula in tables["model_summary"]["formula"].dropna().astype(str)
        if "~" in formula
    )
    for forbidden_rhs in [
        "wiener_index",
        "centrality",
        "agent_deg_centrality",
        "avg_out_degree_centrality",
        "structural_virality",
    ]:
        assert forbidden_rhs not in rhs_text
    assert "topic_score_robustness_coefficients" in tables
    assert "distance_robustness_coefficients" in tables


def test_level1_content_main_uses_home_design_reference_topic():
    n = 96
    topics = [
        "Home Design & Decoration",
        "Brand & Marketing",
        "Events & Promotions",
        "Real Estate & Architecture",
    ]
    df = pd.DataFrame(
        {
            "agent_name": [f"a{i % 12}" for i in range(n)],
            "article_title": [f"story{i}" for i in range(n)],
            "TopContentCluster": [topics[i % len(topics)] for i in range(n)],
            "log_reach": [1.0 + (i % 15) * 0.1 for i in range(n)],
            "CosineSim": [0.25 + (i % 20) * 0.02 for i in range(n)],
            "WordCount": [100 + i for i in range(n)],
            "HasImage": [i % 2 for i in range(n)],
            "NumImages": [i % 5 for i in range(n)],
        }
    )

    tables = run_level1_content_analysis(df)
    main_summary = tables["model_summary"][
        (tables["model_summary"]["model"] == "level1_content_main")
        & (tables["model_summary"]["outcome"] == "log_reach")
    ].iloc[0]
    main_terms = tables["coefficients"][
        (tables["coefficients"]["model"] == "level1_content_main")
        & (tables["coefficients"]["outcome"] == "log_reach")
    ]["term"].astype(str)

    assert "Treatment(reference='Home Design & Decoration')" in main_summary["formula"]
    assert not main_terms.str.contains(r"\[T\.Home Design & Decoration\]", regex=True).any()
    assert main_terms.str.contains(r"\[T\.Brand & Marketing\]", regex=True).any()


def test_level1_analysis_includes_agent_and_article_clustered_se():
    n = 96
    df = pd.DataFrame(
        {
            "agent_name": [f"a{i % 12}" for i in range(n)],
            "article_title": [f"story{i % 24}" for i in range(n)],
            "TopContentCluster": [list(CANONICAL_TOPICS)[i % 3] for i in range(n)],
            "log_reach": [1.0 + (i % 15) * 0.1 for i in range(n)],
            "log_duration": [2.0 + (i % 11) * 0.08 for i in range(n)],
            "structural_virality_winsorized": [1.0 + (i % 7) * 0.05 for i in range(n)],
            "any_reshare": [i % 2 for i in range(n)],
            "cascade_size": [1 + i % 20 for i in range(n)],
            "second_layer_width": [i % 8 for i in range(n)],
            "CosineSim": [0.25 + (i % 20) * 0.02 for i in range(n)],
            "WordCount": [100 + i for i in range(n)],
            "HasImage": [i % 2 for i in range(n)],
            "NumImages": [i % 5 for i in range(n)],
        }
    )

    tables = run_level1_content_analysis(df)
    models = set(tables["model_summary"]["model"])

    assert "level1_content_main_agent_clustered_se" in models
    assert "level1_content_main_article_clustered_se" in models
    assert "clustered_se_coefficients" in tables
    assert not tables["clustered_se_coefficients"].empty


def test_level2_analysis_includes_no_article_count_robustness():
    n = 90
    df = pd.DataFrame(
        {
            "agent_name": [f"a{i}" for i in range(n)],
            "JobCategory": [f"J{i % 4}" for i in range(n)],
            "agent_gender": [i % 2 for i in range(n)],
            "log_agent_cascade_size_mean": [1.0 + (i % 10) * 0.1 for i in range(n)],
            "reshare_mean": [(i % 10) / 10 for i in range(n)],
            "depth_mean": [1 + i % 5 for i in range(n)],
            "second_layer_width_avg": [i % 7 for i in range(n)],
            "structural_virality_mean": [1 + (i % 8) * 0.1 for i in range(n)],
            "wiener_index_mean": [5 + (i % 9) * 0.4 for i in range(n)],
            "centrality_mean": [(i % 11) / 100 for i in range(n)],
            "duration_mean_of_means": [10 + i for i in range(n)],
            "article_count_per_agent": [1 + i % 12 for i in range(n)],
            "log_article_count_per_agent": [0.5 + (i % 12) * 0.1 for i in range(n)],
            "agent_deg_centrality_mean": [(i % 20) / 100 for i in range(n)],
            "avg_out_degree_centrality_mean": [(i % 15) / 100 for i in range(n)],
            "repeat_exposure_1st_nodes_pct": [(i % 6) / 10 for i in range(n)],
            "repeat_exposure_2nd_nodes_pct": [(i % 5) / 10 for i in range(n)],
            "gender_assortativity_mean": [(i % 4) / 10 for i in range(n)],
        }
    )

    tables = run_level2_agent_network_analysis(df)

    assert "level2_core_no_article_count" in set(tables["model_summary"]["model"])
    modeled_outcomes = set(tables["model_summary"]["outcome"])
    assert {
        "agent_deg_centrality_mean",
        "avg_out_degree_centrality_mean",
        "centrality_mean",
        "wiener_index_mean",
    }.issubset(modeled_outcomes)
    assert not any(
        str(model).startswith("level2_descriptor")
        for model in tables["model_summary"]["model"]
    )
    rhs_text = " ".join(
        formula.split("~", 1)[1]
        for formula in tables["model_summary"]["formula"].dropna().astype(str)
        if "~" in formula
    )
    for forbidden_rhs in [
        "agent_deg_centrality_mean",
        "avg_out_degree_centrality_mean",
        "centrality_mean",
        "wiener_index_mean",
        "repeat_exposure_1st_nodes_pct",
        "repeat_exposure_2nd_nodes_pct",
        "gender_assortativity_mean",
    ]:
        assert forbidden_rhs not in rhs_text


def test_variable_role_map_covers_three_level_model_variables():
    role_map = write_variable_role_map()
    variables = set(role_map["variable"])

    expected = {
        "EuclideanDist",
        "ManhattanDist",
        "topic_home_design_decoration",
        "reshare_mean",
        "depth_mean",
        "repeat_exposure_1st_nodes_pct",
        "gender_assortativity_mean",
        "ProfessionContentMatch_mean",
        "WordCount_mean",
        "is_sparse_cell_10",
    }

    assert expected.issubset(variables)
    network_rows = role_map[
        role_map["variable"].isin(
            [
                "agent_deg_centrality_mean",
                "avg_out_degree_centrality_mean",
                "centrality_mean",
                "wiener_index_mean",
            ]
        )
    ]
    assert not network_rows.empty
    assert network_rows["allowed_as_predictor"].eq(False).all()
    assert network_rows["allowed_as_outcome"].eq(True).all()
    assert network_rows["role"].str.contains("outcome").all()
    level1_centrality_rows = role_map[
        (role_map["level"] == "Level 1")
        & role_map["variable"].isin(["centrality", "agent_deg_centrality", "avg_out_degree_centrality"])
    ]
    assert level1_centrality_rows.empty
    assert len(role_map) >= 35


def test_findings_summary_contains_thesis_method_and_interpretation_blocks(tmp_path):
    level1 = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "article_title": ["Story A", "Story B"],
            "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
            "log_reach": [1.0, 2.0],
        }
    )
    level2 = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "JobCategory": ["Sales", "Design"],
            "log_agent_cascade_size_mean": [1.0, 2.0],
        }
    )
    level3 = pd.DataFrame(
        {
            "agent_name": ["Alice", "Bob"],
            "TopContentCluster": ["Home Design & Decoration", "Events & Promotions"],
            "log_agent_topic_cascade_size_mean": [1.0, 2.0],
        }
    )
    coefficient_rows = pd.DataFrame(
        [
            {
                "model": "level1_content_main",
                "outcome": "log_reach",
                "term": "z_CosineSim",
                "coef": 0.1,
                "standardized_beta": 0.1,
                "p_value": 0.01,
            },
            {
                "model": "level1_topic_pca_robustness",
                "outcome": "log_reach",
                "term": "z_CosineSim",
                "coef": 0.9,
                "standardized_beta": 0.9,
                "p_value": 0.001,
            },
            {
                "model": "level2_core",
                "outcome": "agent_deg_centrality_mean",
                "term": "C(JobCategory)[T.Design]",
                "coef": 0.2,
                "standardized_beta": None,
                "p_value": 0.02,
            },
            {
                "model": "level3_model_a_matchscore",
                "outcome": "log_agent_topic_cascade_size_mean",
                "term": "z_MatchScore_mean",
                "coef": 0.3,
                "standardized_beta": 0.3,
                "p_value": 0.03,
            },
            {
                "model": "level3_model_b_profession_match",
                "outcome": "log_agent_topic_cascade_size_mean",
                "term": "z_ProfessionContentMatch_mean",
                "coef": 0.4,
                "standardized_beta": 0.4,
                "p_value": 0.04,
            },
        ]
    )
    path = tmp_path / "Stage4_Findings_Summary.md"
    write_findings_summary(
        path,
        level1=level1,
        level2=level2,
        level3=level3,
        level1_tables={
            "coefficients": coefficient_rows,
            "model_summary": pd.DataFrame(
                {
                    "model": ["level1_content_main", "level1_topic_score_robustness", "level1_topic_pca_robustness", "level1_distance_robustness_euclidean"],
                    "n": [2, 2, 2, 2],
                }
            ),
        },
        level2_tables={
            "coefficients": coefficient_rows,
            "model_summary": pd.DataFrame({"model": ["level2_core", "level2_core_no_article_count"], "n": [2, 2]}),
        },
        level3_tables={
            "coefficients": coefficient_rows,
            "model_summary": pd.DataFrame(
                {
                    "model": ["level3_model_a_matchscore", "level3_model_b_profession_match", "level3_model_a_matchscore_weighted"],
                    "n": [2, 2, 2],
                }
            ),
            "sparse_cell_diagnostics": pd.DataFrame({"rows": [2], "pairs_n_ge_10": [1], "pairs_n_ge_30": [0]}),
        },
    )

    text = path.read_text(encoding="utf-8")
    for expected in [
        "Research question",
        "Data used",
        "Method",
        "Primary DV",
        "Controls",
        "Interpretation",
        "Standardized beta",
        "Leakage control",
        "Complete-case",
            "Sparse-cell",
            "If a category with only one agent is used as the reference",
            "should not be read as clean evidence that role is unrelated",
            "supplementary dependent variables",
            "different outcome set",
            "unit of analysis",
            "same metric should not be forced into every level",
            "Step-by-step workflow",
            "Step 1 - Source readiness precheck",
            "Step 2 - Build separate level-specific master files",
        "Step 3 - Standardize topic labels",
        "Step 4 - Assign variable roles before modeling",
        "Step 5 - Run Level 1 content analysis",
        "Step 6 - Run Level 2 agent-characteristic analysis",
        "Step 7 - Run Level 3 content-agent matching analysis",
        "Step 8 - Generate tables, figures, validation files, and notebook",
        "What this step does",
        "Why this step matters",
        "How to read the output",
        "Thesis wording",
    ]:
        assert expected in text
    assert "Key model signal: `z_CosineSim` on `log_reach`: coef=0.100" in text
    assert "Key model signal: `z_CosineSim` on `log_reach`: coef=0.900" not in text


def test_create_level_figures_generates_planned_figure_set(tmp_path, monkeypatch):
    monkeypatch.setattr(s4, "FIGURE_DIR", tmp_path)
    n = 80
    level1 = pd.DataFrame(
        {
            "TopContentCluster": [list(CANONICAL_TOPICS)[i % 4] for i in range(n)],
            "log_reach": [1.0 + (i % 12) * 0.1 for i in range(n)],
            "depth": [1 + i % 5 for i in range(n)],
            "reshare_pct": [(i % 10) / 10 for i in range(n)],
            "log_duration": [2.0 + (i % 9) * 0.1 for i in range(n)],
            "structural_virality_winsorized": [1.0 + (i % 7) * 0.1 for i in range(n)],
            "CosineSim": [i / n for i in range(n)],
        }
    )
    level2 = pd.DataFrame(
        {
            "JobCategory": [f"J{i % 4}" for i in range(n)],
            "log_agent_cascade_size_mean": [1.0 + (i % 11) * 0.1 for i in range(n)],
            "agent_deg_centrality_mean": [(i % 20) / 100 for i in range(n)],
            "avg_out_degree_centrality_mean": [(i % 15) / 100 for i in range(n)],
            "repeat_exposure_1st_nodes_pct": [(i % 6) / 10 for i in range(n)],
            "repeat_exposure_2nd_nodes_pct": [(i % 5) / 10 for i in range(n)],
        }
    )
    level3 = pd.DataFrame(
        {
            "JobCategory": [f"J{i % 4}" for i in range(n)],
            "TopContentCluster": [list(CANONICAL_TOPICS)[i % 4] for i in range(n)],
            "log_agent_topic_cascade_size_mean": [1.0 + (i % 13) * 0.1 for i in range(n)],
            "MatchScore_mean": [(i % 20) / 20 for i in range(n)],
            "agent_deg_centrality_mean": [(i % 18) / 100 for i in range(n)],
            "agent_topic_article_n": [1 + i % 35 for i in range(n)],
        }
    )

    paths = create_level_figures(level1, level2, level3)
    names = {path.name for path in paths}

    expected = {
        "level1_content_outcome_distributions.png",
        "level1_content_regression_summary.png",
        "level2_agent_performance_distribution.png",
        "level2_network_metric_correlations.png",
        "level2_repeat_exposure_patterns.png",
    }
    assert expected.issubset(names)
    assert all((tmp_path / name).exists() for name in expected)


def test_cleanup_legacy_outputs_removes_analysis_master(tmp_path):
    legacy = tmp_path / "analysis_master.xlsx"
    legacy.write_text("legacy", encoding="utf-8")
    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    legacy_figure = figure_dir / "topic_outcome_boxplots.png"
    legacy_figure.write_text("legacy figure", encoding="utf-8")
    current_figure = figure_dir / "level1_topic_outcome_boxplots.png"
    current_figure.write_text("current figure", encoding="utf-8")

    cleanup_legacy_outputs(tmp_path)

    assert not legacy.exists()
    assert not legacy_figure.exists()
    assert current_figure.exists()
