from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.oneway import anova_oneway


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
TABLE_DIR = OUT_DIR / "tables"
FIGURE_DIR = OUT_DIR / "figures"

PATHS = {
    "final": ROOT / "diffusion(S3)" / "final_results.xlsx",
    "agent_level": ROOT / "diffusion(S3)" / "agent_level_results.xlsx",
    "agent_topic": ROOT / "diffusion(S3)" / "agent_topic_level_results.xlsx",
    "corrected": ROOT / "diffusion(S3)" / "diffusion_corrected_layers.xlsx",
    "content": ROOT
    / "batch_outputs(S2)"
    / "filtered2_results_clustered_all(translated).xlsx",
    "article_meta": ROOT / "batch_outputs(S2)" / "filtered_results_all_cleaned.xlsx",
    "agent_gender": ROOT / "diffusion(S3)" / "unique_agentsgender.xlsx",
    "agent_dep_job": ROOT / "diffusion(S3)" / "agent_dep_job.csv",
}

EXPECTED_MASTER_ROWS = 6557
EXPECTED_AGENT_ROWS = 592
EXPECTED_AGENT_TOPIC_ROWS = 1142

TOPIC_ZH_TO_EN = {
    "家居设计与装修": "Home Design & Decoration",
    "房地产与建筑": "Real Estate & Architecture",
    "活动与促销": "Events & Promotions",
    "品牌与市场推广": "Brand & Marketing",
    "生活方式与文化": "Lifestyle & Culture",
    "客户服务与管理": "Customer Service & Management",
}

CANONICAL_TOPICS = tuple(TOPIC_ZH_TO_EN.values())

TOPIC_SCORE_COLUMN_MAP = {
    "家居设计与装修(Content)": "topic_home_design_decoration",
    "房地产与建筑(Content)": "topic_real_estate_architecture",
    "活动与促销(Content)": "topic_events_promotions",
    "品牌与市场推广(Content)": "topic_brand_marketing",
    "生活方式与文化(Content)": "topic_lifestyle_culture",
    "客户服务与管理(Content)": "topic_customer_service_management",
    "Home Design & Decoration(Title+Content)": "topic_home_design_decoration",
    "Real Estate & Architecture(Title+Content)": "topic_real_estate_architecture",
    "Events & Promotions(Title+Content)": "topic_events_promotions",
    "Brand & Marketing(Title+Content)": "topic_brand_marketing",
    "Lifestyle & Culture(Title+Content)": "topic_lifestyle_culture",
    "Customer Service & Management(Title+Content)": "topic_customer_service_management",
}

CANONICAL_TOPIC_SCORE_COLUMNS = tuple(dict.fromkeys(TOPIC_SCORE_COLUMN_MAP.values()))

OUTCOME_COLUMNS = [
    "cascade_size",
    "total_reads",
    "log_reach",
    "depth",
    "second_layer_width",
    "reshare_pct",
    "any_reshare",
    "duration_mean_s",
    "duration_mean_s_winsorized",
    "log_duration",
    "structural_virality",
    "structural_virality_winsorized",
]

ANALYSIS_OUTCOMES = [
    "log_reach",
    "depth",
    "reshare_pct",
    "log_duration",
    "structural_virality_winsorized",
]

PLOT_OUTCOMES = ["log_reach", "depth", "reshare_pct", "log_duration"]

LEGACY_FIGURE_NAMES = [
    "agent_topic_opportunity_heatmap.png",
    "anova_tukey_summary.png",
    "cosinesim_decile_trends.png",
    "diffusion_outcome_distributions.png",
    "jobcategory_outcome_boxplots.png",
    "matchscore_centrality_interaction.png",
    "matchscore_decile_trends.png",
    "topic_outcome_boxplots.png",
    "winsorization_comparison.png",
]

LEVEL1_FORBIDDEN_COLUMNS = {
    "MatchScore",
    "ProfessionContentMatch",
    "JobCategory",
    "agent_job",
    "agent_dep",
    "agent_gender",
    "matchscore_mean",
    "profession_content_match_mean",
    "centrality",
    "agent_deg_centrality",
    "avg_out_degree_centrality",
    "gender_assortativity",
}

READINESS_REQUIRED_COLUMNS = {
    "final": [
        "agent_name",
        "article_title",
        "Title",
        "first_layer_width",
        "second_layer_width",
        "depth",
        "reshare_pct",
        "duration_mean_s",
        "structural_virality",
        "MatchScore",
        "ProfessionContentMatch",
        "JobCategory",
    ],
    "agent_level": [
        "agent_name",
        "cascade_size_mean",
        "depth_mean",
        "reshare_mean",
    ],
    "agent_topic": [
        "agent_name",
        "TopContentCluster",
        "cascade_size_mean",
    ],
    "corrected": [
        "agent_name",
        "article_title",
        "reader_wechat_nn",
        "reader_read",
        "correct_layer",
    ],
    "content": [
        "Title",
        "TopContentCluster",
        "CosineSim",
        "EuclideanDist",
        "ManhattanDist",
    ],
    "article_meta": [
        "Title",
        "WordCount",
        "HasImage",
        "NumImages",
    ],
}


@dataclass
class Stage4Results:
    level1_master_path: Path
    level2_master_path: Path
    level3_master_path: Path
    level1_analysis_path: Path
    level2_analysis_path: Path
    level3_analysis_path: Path
    source_readiness_path: Path
    variable_role_map_path: Path
    join_quality_path: Path
    notebook_path: Path
    validation: dict
    figures: list[Path]


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def exact_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _with_agent_article_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_agent_exact"] = out["agent_name"].map(exact_text)
    out["_article_exact"] = out["article_title"].map(exact_text)
    out["_agent_key"] = out["agent_name"].map(normalize_text)
    out["_article_key"] = out["article_title"].map(normalize_text)
    return out


def _with_title_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_title_key"] = out["Title"].map(normalize_text)
    return out


def _dedupe_on_key(df: pd.DataFrame, key: str) -> pd.DataFrame:
    return df.sort_values(key).drop_duplicates(key, keep="first")


def duplicate_key_report(
    df: pd.DataFrame,
    *,
    key_col: str,
    value_cols: list[str],
    normalized_key_name: str = "normalized_key",
) -> pd.DataFrame:
    if key_col not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work[normalized_key_name] = work[key_col].map(normalize_text)
    rows = []
    for key, group in work.groupby(normalized_key_name, dropna=False):
        if len(group) < 2:
            continue
        conflicting = []
        for column in value_cols:
            if column in group.columns and group[column].dropna().map(str).nunique() > 1:
                conflicting.append(column)
        if not conflicting:
            continue
        rows.append(
            {
                normalized_key_name: key,
                "rows_n": int(len(group)),
                "conflicting_columns": ", ".join(conflicting),
                "raw_keys": " | ".join(map(str, group[key_col].dropna().unique()[:10])),
            }
        )
    return pd.DataFrame(rows)


def _coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _mode_or_first(series: pd.Series):
    clean = series.dropna()
    if clean.empty:
        return np.nan
    mode = clean.mode()
    return mode.iloc[0] if not mode.empty else clean.iloc[0]


def _sanitize_sheet_name(name: str) -> str:
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "_", str(name))
    return cleaned[:31] or "Sheet"


def _safe_qcut(series: pd.Series, q: int, label_prefix: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    non_missing = numeric.dropna()
    if non_missing.nunique() < 2:
        return pd.Series(pd.NA, index=series.index, dtype="object")
    bins = min(q, int(non_missing.nunique()))
    codes = pd.qcut(numeric, q=bins, labels=False, duplicates="drop")
    actual_bins = int(codes.dropna().max()) + 1
    labels = [f"{label_prefix}{index}" for index in range(1, actual_bins + 1)]
    values = codes.map(lambda x: labels[int(x)] if pd.notna(x) else pd.NA)
    return pd.Series(
        pd.Categorical(values, categories=labels, ordered=True),
        index=series.index,
    )


def winsorize_series(series: pd.Series, upper_quantile: float = 0.99) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    cap = numeric.quantile(upper_quantile)
    if pd.isna(cap):
        return numeric
    return numeric.clip(upper=cap)


def _topic_score_columns(df: pd.DataFrame) -> list[str]:
    canonical = [
        column
        for column in CANONICAL_TOPIC_SCORE_COLUMNS
        if column in df.columns and pd.api.types.is_numeric_dtype(pd.to_numeric(df[column], errors="coerce"))
    ]
    if canonical:
        return canonical
    translated = [
        column
        for column in df.columns
        if "(Title+Content)" in str(column) and pd.api.types.is_numeric_dtype(df[column])
    ]
    if translated:
        return translated
    return [
        column
        for column in df.columns
        if str(column).endswith("(Content)")
        and pd.api.types.is_numeric_dtype(pd.to_numeric(df[column], errors="coerce"))
    ]


def _standardize_for_regression(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for index, column in enumerate(columns, start=1):
        if column not in out.columns:
            continue
        numeric = pd.to_numeric(out[column], errors="coerce")
        std = numeric.std(skipna=True)
        safe_name = f"z_topic_{index}" if "(Title+Content)" in str(column) or "(Content)" in str(column) else f"z_{column}"
        if std and not math.isclose(float(std), 0.0):
            out[safe_name] = (numeric - numeric.mean(skipna=True)) / std
        else:
            out[safe_name] = 0.0
    return out


def standardize_topic_labels_to_english(
    df: pd.DataFrame,
    column: str = "TopContentCluster",
    *,
    source_column: str | None = None,
) -> pd.DataFrame:
    out = df.copy()
    if column not in out.columns:
        return out
    if source_column and source_column not in out.columns:
        out[source_column] = out[column]
    out[column] = out[column].map(lambda value: TOPIC_ZH_TO_EN.get(str(value), value) if pd.notna(value) else value)
    return out


def rename_topic_score_columns_to_english(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for source, target in TOPIC_SCORE_COLUMN_MAP.items():
        if source not in out.columns:
            continue
        numeric = pd.to_numeric(out[source], errors="coerce")
        if target in out.columns and target != source:
            out[target] = out[target].combine_first(numeric)
        else:
            out[target] = numeric
    return out


def _with_title_exact(df: pd.DataFrame, title_col: str = "Title") -> pd.DataFrame:
    out = df.copy()
    out["_title_exact"] = out[title_col].map(exact_text)
    return out


def _prepare_content_exact(content: pd.DataFrame) -> pd.DataFrame:
    content = _with_title_exact(rename_topic_score_columns_to_english(content), "Title")
    keep = [
        column
        for column in [
            "_title_exact",
            "TopTitleCluster",
            "TopContentCluster",
            "CosineSim",
            "EuclideanDist",
            "ManhattanDist",
            *CANONICAL_TOPIC_SCORE_COLUMNS,
        ]
        if column in content.columns
    ]
    prepared = content[keep].drop_duplicates("_title_exact", keep="first").copy()
    prepared = standardize_topic_labels_to_english(
        prepared,
        "TopContentCluster",
        source_column="TopContentCluster_source",
    )
    for column in ["CosineSim", "EuclideanDist", "ManhattanDist", *CANONICAL_TOPIC_SCORE_COLUMNS]:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    return prepared


def _prepare_article_meta_exact(article_meta: pd.DataFrame | None) -> pd.DataFrame | None:
    if article_meta is None or article_meta.empty or "Title" not in article_meta.columns:
        return None
    meta = _with_title_exact(article_meta, "Title")
    keep = [column for column in ["_title_exact", "WordCount", "HasImage", "NumImages"] if column in meta.columns]
    meta = meta[keep].drop_duplicates("_title_exact", keep="first").copy()
    if "HasImage" in meta.columns:
        meta["HasImage"] = (
            meta["HasImage"].astype(str).str.strip().str.lower().isin(["yes", "y", "1", "true"])
        ).astype(int)
    for column in ["WordCount", "NumImages"]:
        if column in meta.columns:
            meta[column] = pd.to_numeric(meta[column], errors="coerce")
    return meta


def _drop_internal_columns(df: pd.DataFrame) -> pd.DataFrame:
    internal = [column for column in df.columns if str(column).startswith("_")]
    return df.drop(columns=internal, errors="ignore")


def _agent_attribute_frame(
    final: pd.DataFrame,
    agent_gender: pd.DataFrame | None = None,
    agent_dep_job: pd.DataFrame | None = None,
) -> pd.DataFrame:
    attrs = pd.DataFrame({"agent_name": sorted(final["agent_name"].dropna().unique())})
    attrs["_agent_key"] = attrs["agent_name"].map(normalize_text)
    for column in ["JobCategory", "agent_job"]:
        if column in final.columns:
            values = (
                final.assign(_agent_key=final["agent_name"].map(normalize_text))
                .groupby("_agent_key", dropna=False)[column]
                .agg(_mode_or_first)
                .reset_index()
            )
            attrs = attrs.merge(values, on="_agent_key", how="left")
    gender = _prepare_agent_gender(agent_gender)
    if gender is not None:
        attrs = attrs.merge(gender, on="_agent_key", how="left")
    dep = _prepare_agent_dep_job(agent_dep_job)
    if dep is not None:
        attrs = attrs.merge(dep, on="_agent_key", how="left")
        if "agent_job_lookup" in attrs.columns:
            attrs["agent_job"] = attrs.get("agent_job").combine_first(attrs["agent_job_lookup"])
            attrs = attrs.drop(columns=["agent_job_lookup"])
    if "JobCategory" in attrs.columns:
        attrs["JobCategory"] = attrs["JobCategory"].astype("string")
    return attrs


def aggregate_corrected_layers(corrected: pd.DataFrame) -> pd.DataFrame:
    keyed = _with_agent_article_keys(corrected)
    keyed["reader_read"] = pd.to_numeric(keyed.get("reader_read"), errors="coerce").fillna(0)
    keyed["correct_layer"] = pd.to_numeric(keyed.get("correct_layer"), errors="coerce")

    grouped = keyed.groupby(["_agent_exact", "_article_exact"], dropna=False)
    aggregate = grouped.agg(
        cascade_size=("reader_wechat_nn", "size"),
        unique_reader_count=("reader_wechat_nn", "nunique"),
        total_reads=("reader_read", "sum"),
        corrected_depth=("correct_layer", "max"),
        TopContentCluster_corrected=("TopContentCluster", _mode_or_first)
        if "TopContentCluster" in keyed.columns
        else ("reader_wechat_nn", "size"),
    ).reset_index()
    aggregate["_agent_key"] = aggregate["_agent_exact"].map(normalize_text)
    aggregate["_article_key"] = aggregate["_article_exact"].map(normalize_text)

    layer_counts = (
        keyed.pivot_table(
            index=["_agent_exact", "_article_exact"],
            columns="correct_layer",
            values="reader_wechat_nn",
            aggfunc="size",
            fill_value=0,
        )
        .rename(columns=lambda value: f"layer_{int(value)}_count")
        .reset_index()
    )
    aggregate = aggregate.merge(layer_counts, on=["_agent_exact", "_article_exact"], how="left")
    return aggregate


def _prepare_content(content: pd.DataFrame) -> pd.DataFrame:
    content = _with_title_key(content)
    keep = [
        column
        for column in content.columns
        if column
        in {
            "_title_key",
            "TopTitleCluster",
            "TopContentCluster",
            "CosineSim",
            "EuclideanDist",
            "ManhattanDist",
        }
        or "(Title+Content)" in str(column)
    ]
    return _dedupe_on_key(content[keep], "_title_key")


def _prepare_article_meta(article_meta: pd.DataFrame | None) -> pd.DataFrame | None:
    if article_meta is None or article_meta.empty or "Title" not in article_meta.columns:
        return None
    meta = _with_title_key(article_meta)
    keep = [
        column
        for column in ["_title_key", "WordCount", "HasImage", "NumImages"]
        if column in meta.columns
    ]
    meta = _dedupe_on_key(meta[keep], "_title_key")
    if "HasImage" in meta.columns:
        meta["HasImage"] = (
            meta["HasImage"].astype(str).str.strip().str.lower().isin(["yes", "y", "1", "true"])
        ).astype(int)
    for column in ["WordCount", "NumImages"]:
        if column in meta.columns:
            meta[column] = pd.to_numeric(meta[column], errors="coerce")
    return meta


def _prepare_agent_gender(agent_gender: pd.DataFrame | None) -> pd.DataFrame | None:
    if agent_gender is None or agent_gender.empty or "agent_name" not in agent_gender.columns:
        return None
    gender = agent_gender.copy()
    gender["_agent_key"] = gender["agent_name"].map(normalize_text)
    keep = ["_agent_key", "agent_gender"]
    gender = _dedupe_on_key(gender[keep], "_agent_key")
    gender["agent_gender"] = pd.to_numeric(gender["agent_gender"], errors="coerce")
    return gender


def _prepare_agent_dep_job(agent_dep_job: pd.DataFrame | None) -> pd.DataFrame | None:
    if agent_dep_job is None or agent_dep_job.empty:
        return None
    dep = agent_dep_job.copy()
    if "agent" in dep.columns:
        dep["_agent_key"] = dep["agent"].map(normalize_text)
    elif "agent_name" in dep.columns:
        dep["_agent_key"] = dep["agent_name"].map(normalize_text)
    else:
        return None
    keep = [column for column in ["_agent_key", "agent_dep", "agent_job"] if column in dep.columns]
    dep = _dedupe_on_key(dep[keep], "_agent_key")
    if "agent_job" in dep.columns:
        dep = dep.rename(columns={"agent_job": "agent_job_lookup"})
    return dep


def build_master_from_frames(
    *,
    final: pd.DataFrame,
    corrected: pd.DataFrame,
    content: pd.DataFrame,
    article_meta: pd.DataFrame | None = None,
    agent_gender: pd.DataFrame | None = None,
    agent_dep_job: pd.DataFrame | None = None,
) -> pd.DataFrame:
    master = _with_agent_article_keys(final)
    master["_row_id"] = np.arange(len(master))
    if "Title" in master.columns:
        master["_title_key"] = master["Title"].map(normalize_text)
    else:
        master["_title_key"] = master["article_title"].map(normalize_text)

    corrected_agg = aggregate_corrected_layers(corrected)
    exact_keys = ["_agent_exact", "_article_exact"]
    normalized_keys = ["_agent_key", "_article_key"]
    corrected_value_cols = [
        column
        for column in corrected_agg.columns
        if column not in {*exact_keys, *normalized_keys}
    ]
    master = master.merge(
        corrected_agg[[*exact_keys, *corrected_value_cols]],
        on=exact_keys,
        how="left",
    )

    unmatched = master["cascade_size"].isna() if "cascade_size" in master.columns else pd.Series(False, index=master.index)
    if unmatched.any():
        unique_fallback = corrected_agg[
            ~corrected_agg.duplicated(normalized_keys, keep=False)
        ][[*normalized_keys, *corrected_value_cols]].copy()
        unique_fallback = unique_fallback.rename(
            columns={column: f"{column}_fallback" for column in corrected_value_cols}
        )
        master = master.merge(unique_fallback, on=normalized_keys, how="left")
        for column in corrected_value_cols:
            fallback_column = f"{column}_fallback"
            if fallback_column in master.columns:
                master[column] = master[column].combine_first(master[fallback_column])
                master = master.drop(columns=[fallback_column])

    prepared_content = _prepare_content(content)
    master = master.merge(prepared_content, on="_title_key", how="left", suffixes=("", "_content"))
    if "TopContentCluster_content" in master.columns:
        master["TopContentCluster"] = master.get("TopContentCluster").combine_first(
            master["TopContentCluster_content"]
        )
        master = master.drop(columns=["TopContentCluster_content"])
    if "TopContentCluster" not in master.columns and "TopContentCluster_corrected" in master.columns:
        master["TopContentCluster"] = master["TopContentCluster_corrected"]
    elif "TopContentCluster_corrected" in master.columns:
        master["TopContentCluster"] = master["TopContentCluster"].combine_first(
            master["TopContentCluster_corrected"]
        )

    prepared_meta = _prepare_article_meta(article_meta)
    if prepared_meta is not None:
        master = master.merge(prepared_meta, on="_title_key", how="left")

    prepared_gender = _prepare_agent_gender(agent_gender)
    if prepared_gender is not None:
        master = master.merge(prepared_gender, on="_agent_key", how="left")

    prepared_dep = _prepare_agent_dep_job(agent_dep_job)
    if prepared_dep is not None:
        master = master.merge(prepared_dep, on="_agent_key", how="left")
        if "agent_job_lookup" in master.columns:
            if "agent_job" in master.columns:
                master["agent_job"] = master["agent_job"].combine_first(master["agent_job_lookup"])
            else:
                master["agent_job"] = master["agent_job_lookup"]
            master = master.drop(columns=["agent_job_lookup"])

    master = master.sort_values("_row_id").reset_index(drop=True)
    return master


def derive_analysis_variables(master: pd.DataFrame) -> pd.DataFrame:
    df = master.copy()
    numeric_columns = [
        "cascade_size",
        "unique_reader_count",
        "total_reads",
        "first_layer_width",
        "second_layer_width",
        "depth",
        "corrected_depth",
        "reshare_pct",
        "centrality",
        "wiener_index",
        "structural_virality",
        "gender_assortativity",
        "agent_deg_centrality",
        "avg_out_degree_centrality",
        "duration_mean_s",
        "duration_var_s2",
        "gender_pct_all_1",
        "gender_pct_all_0",
        "gender_pct_aud_0",
        "gender_pct_aud_1",
        "MatchScore",
        "ProfessionContentMatch",
        "CosineSim",
        "EuclideanDist",
        "ManhattanDist",
        "WordCount",
        "HasImage",
        "NumImages",
        "agent_gender",
    ]
    numeric_columns.extend(
        [column for column in df.columns if "(Title+Content)" in str(column) or "(Content)" in str(column)]
    )
    df = _coerce_numeric(df, numeric_columns)

    if "cascade_size" not in df.columns:
        df["cascade_size"] = df["first_layer_width"].fillna(0) + df["second_layer_width"].fillna(0)
    df["cascade_size"] = df["cascade_size"].fillna(0)
    df["total_reads"] = df.get("total_reads", df["cascade_size"]).fillna(0)

    for column in ["duration_mean_s", "wiener_index", "structural_virality"]:
        if column in df.columns:
            df[f"{column}_winsorized"] = winsorize_series(df[column])

    if "duration_mean_s_winsorized" not in df.columns and "duration_mean_s" in df.columns:
        df["duration_mean_s_winsorized"] = winsorize_series(df["duration_mean_s"])
    if "structural_virality_winsorized" not in df.columns and "structural_virality" in df.columns:
        df["structural_virality_winsorized"] = winsorize_series(df["structural_virality"])

    df["log_reach"] = np.log1p(df["cascade_size"])
    df["log_total_reads"] = np.log1p(df["total_reads"])
    df["log_duration"] = np.log1p(df["duration_mean_s_winsorized"].fillna(0))
    df["any_reshare"] = (df["reshare_pct"].fillna(0) > 0).astype(int)

    if "HasImage" in df.columns:
        df["HasImage"] = df["HasImage"].fillna(0).astype(int)
    if "NumImages" in df.columns:
        df["NumImages"] = df["NumImages"].fillna(0)

    if "CosineSim" in df.columns:
        df["CosineSimDecile"] = _safe_qcut(df["CosineSim"], 10, "D")
        df["CosineSimQuartile"] = _safe_qcut(df["CosineSim"], 4, "Q")
    if "MatchScore" in df.columns:
        df["MatchScoreDecile"] = _safe_qcut(df["MatchScore"], 10, "D")
        df["MatchScoreQuartile"] = _safe_qcut(df["MatchScore"], 4, "Q")
        median = df["MatchScore"].median(skipna=True)
        df["HighMatch"] = np.where(df["MatchScore"] >= median, "High match", "Low match")

    if "TopContentCluster" in df.columns:
        df["TopContentCluster"] = df["TopContentCluster"].astype("string")
    if "JobCategory" in df.columns:
        df["JobCategory"] = df["JobCategory"].astype("string")
    if "ProfessionContentMatch" in df.columns:
        df["ProfessionContentMatch"] = df["ProfessionContentMatch"].astype("Int64").astype("string")

    return df


def validate_master(
    master: pd.DataFrame,
    expected_rows: int = EXPECTED_MASTER_ROWS,
    *,
    raise_on_error: bool = False,
) -> dict:
    checks: dict[str, dict] = {}
    errors: list[str] = []

    def add_check(name: str, passed: bool, **details):
        checks[name] = {"passed": bool(passed), **details}
        if not passed:
            errors.append(name)

    add_check("row_count", len(master) == expected_rows, actual=int(len(master)), expected=expected_rows)

    if {"_agent_key", "_article_key"}.issubset(master.columns):
        duplicate_count = int(master.duplicated(["_agent_key", "_article_key"]).sum())
        checks["normalized_duplicate_agent_article_rows"] = {
            "passed": True,
            "duplicates": duplicate_count,
            "note": "Tracked but not fatal because NFKC normalization can merge visually equivalent titles.",
        }

    if "MatchScore" in master.columns:
        match = pd.to_numeric(master["MatchScore"], errors="coerce")
        add_check(
            "MatchScore_range",
            bool(match.dropna().between(0, 1).all()),
            min=float(match.min(skipna=True)),
            max=float(match.max(skipna=True)),
        )

    nonnegative_columns = [
        "cascade_size",
        "total_reads",
        "depth",
        "second_layer_width",
        "reshare_pct",
        "duration_mean_s",
        "structural_virality",
    ]
    for column in nonnegative_columns:
        if column in master.columns:
            numeric = pd.to_numeric(master[column], errors="coerce")
            add_check(
                f"{column}_nonnegative",
                bool((numeric.dropna() >= 0).all()),
                min=float(numeric.min(skipna=True)),
                missing=int(numeric.isna().sum()),
            )

    for column in _topic_score_columns(master):
        numeric = pd.to_numeric(master[column], errors="coerce")
        max_value = numeric.max(skipna=True)
        min_value = numeric.min(skipna=True)
        scale_ok = bool((numeric.dropna().between(0, 100).all()))
        add_check(
            f"topic_score_scale_{column}",
            scale_ok,
            min=float(min_value),
            max=float(max_value),
            expected="0-100 scale",
        )

    required = ["log_reach", "any_reshare", "log_duration", "duration_mean_s_winsorized"]
    missing_required = [column for column in required if column not in master.columns]
    add_check("derived_columns_present", not missing_required, missing=missing_required)

    validation = {
        "valid": not errors,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "checks": checks,
        "errors": errors,
    }
    if errors and raise_on_error:
        raise ValueError(f"Stage4 validation failed: {', '.join(errors)}")
    return validation


def load_inputs(paths: dict[str, Path] = PATHS) -> dict[str, pd.DataFrame]:
    return {
        "final": pd.read_excel(paths["final"]),
        "agent_level": pd.read_excel(paths["agent_level"]),
        "agent_topic": pd.read_excel(paths["agent_topic"]),
        "corrected": pd.read_excel(paths["corrected"]),
        "content": pd.read_excel(paths["content"]),
        "article_meta": pd.read_excel(paths["article_meta"]),
        "agent_gender": pd.read_excel(paths["agent_gender"]),
        "agent_dep_job": pd.read_csv(paths["agent_dep_job"], encoding="utf-8-sig"),
    }


def make_join_quality_tables(inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    tables["topic_label_standardization"] = _topic_label_standardization_report(inputs)

    content = inputs.get("content")
    if content is not None and not content.empty and "Title" in content.columns:
        content_value_cols = [
            column
            for column in [
                "TopTitleCluster",
                "TopContentCluster",
                "CosineSim",
                "EuclideanDist",
                "ManhattanDist",
                *_topic_score_columns(content),
            ]
            if column in content.columns
        ]
        tables["content_title_conflicts"] = duplicate_key_report(
            content,
            key_col="Title",
            value_cols=content_value_cols,
        )

    article_meta = inputs.get("article_meta")
    if article_meta is not None and not article_meta.empty and "Title" in article_meta.columns:
        meta_value_cols = [column for column in ["WordCount", "HasImage", "NumImages"] if column in article_meta.columns]
        tables["article_meta_title_conflicts"] = duplicate_key_report(
            article_meta,
            key_col="Title",
            value_cols=meta_value_cols,
        )

    agent_dep_job = inputs.get("agent_dep_job")
    if agent_dep_job is not None and not agent_dep_job.empty:
        agent_key = "agent" if "agent" in agent_dep_job.columns else "agent_name" if "agent_name" in agent_dep_job.columns else None
        if agent_key:
            dep_value_cols = [column for column in ["agent_dep", "agent_job"] if column in agent_dep_job.columns]
            tables["agent_dep_job_conflicts"] = duplicate_key_report(
                agent_dep_job,
                key_col=agent_key,
                value_cols=dep_value_cols,
                normalized_key_name="normalized_agent",
            )

    corrected = inputs.get("corrected")
    if corrected is not None and not corrected.empty:
        reader_missing = (
            corrected["reader_wechat_nn"].isna()
            | corrected["reader_wechat_nn"].astype(str).str.strip().eq("")
            if "reader_wechat_nn" in corrected.columns
            else pd.Series(False, index=corrected.index)
        )
        group_cols = [column for column in ["agent_name", "article_title"] if column in corrected.columns]
        if group_cols:
            groups_with_missing = int(corrected.loc[reader_missing, group_cols].drop_duplicates().shape[0])
            total_groups = int(corrected[group_cols].drop_duplicates().shape[0])
        else:
            groups_with_missing = 0
            total_groups = np.nan
        tables["corrected_reader_id_missing"] = pd.DataFrame(
            [
                {
                    "corrected_rows": int(len(corrected)),
                    "corrected_agent_article_groups": total_groups,
                    "missing_reader_wechat_nn_rows": int(reader_missing.sum()),
                    "agent_article_groups_with_missing_reader_id": groups_with_missing,
                    "cascade_size_note": "cascade_size counts corrected-layer rows; unique_reader_count excludes missing reader_wechat_nn.",
                }
            ]
        )

    tables["source_row_counts"] = pd.DataFrame(
        [{"source": name, "rows": int(len(frame)), "columns": int(frame.shape[1])} for name, frame in inputs.items()]
    )
    return tables


def _topic_label_standardization_report(inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict] = []
    topic_sources = [
        ("final", "TopContentCluster"),
        ("content", "TopContentCluster"),
        ("corrected", "TopContentCluster"),
        ("agent_topic", "TopContentCluster"),
    ]
    for source, column in topic_sources:
        frame = inputs.get(source)
        if frame is None or frame.empty or column not in frame.columns:
            continue
        counts = frame[column].dropna().map(normalize_text).value_counts(dropna=False)
        for label, rows_n in counts.items():
            if not label:
                continue
            mapped_label = TOPIC_ZH_TO_EN.get(label, label)
            mapped = mapped_label in CANONICAL_TOPICS
            rows.append(
                {
                    "source": source,
                    "column": column,
                    "source_label": label,
                    "TopContentCluster": mapped_label if mapped else pd.NA,
                    "rows_n": int(rows_n),
                    "mapped": bool(mapped),
                }
            )
    if rows:
        return pd.DataFrame(rows).sort_values(["mapped", "source", "source_label"]).reset_index(drop=True)
    return pd.DataFrame(
        [{"source": "mapping_dictionary", "column": "TopContentCluster", "source_label": zh, "TopContentCluster": en, "rows_n": 0, "mapped": True} for zh, en in TOPIC_ZH_TO_EN.items()]
    )


def _duplicate_count(frame: pd.DataFrame, columns: list[str], *, normalize: bool = False) -> int:
    if frame.empty or not set(columns).issubset(frame.columns):
        return 0
    work = frame[columns].copy()
    if normalize:
        for column in columns:
            work[column] = work[column].map(normalize_text)
    return int(work.duplicated(columns).sum())


def _required_column_status(inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for source, required in READINESS_REQUIRED_COLUMNS.items():
        frame = inputs.get(source)
        existing = set(frame.columns) if frame is not None else set()
        missing = [column for column in required if column not in existing]
        rows.append(
            {
                "source": source,
                "required_columns_n": len(required),
                "missing_columns_n": len(missing),
                "missing_columns": ", ".join(missing),
                "passed": len(missing) == 0,
            }
        )
    return pd.DataFrame(rows)


def _title_coverage_row(final: pd.DataFrame, target: pd.DataFrame, *, target_name: str) -> dict:
    if "Title" not in final.columns or "Title" not in target.columns:
        return {
            "join": f"final_to_{target_name}_exact_title",
            "final_unique_titles": np.nan,
            f"{target_name}_unique_titles": np.nan,
            "missing_final_titles_in_target": np.nan,
            "normalized_fallback_possible": np.nan,
            "exact_join_ok": False,
        }
    exact_final_titles = set(final["Title"].dropna().map(exact_text))
    exact_target_titles = set(target["Title"].dropna().map(exact_text))
    normalized_target_titles = set(target["Title"].dropna().map(normalize_text))
    missing_exact = exact_final_titles - exact_target_titles
    fallback_possible = {
        title for title in missing_exact if normalize_text(title) in normalized_target_titles
    }
    return {
        "join": f"final_to_{target_name}_exact_title",
        "final_unique_titles": len(exact_final_titles),
        f"{target_name}_unique_titles": len(exact_target_titles),
        "missing_final_titles_in_target": len(missing_exact),
        "normalized_fallback_possible": len(fallback_possible),
        "exact_join_ok": len(missing_exact) == 0,
    }


def build_analysis_master(paths: dict[str, Path] = PATHS) -> pd.DataFrame:
    inputs = load_inputs(paths)
    legacy_inputs = {
        key: inputs[key]
        for key in ["final", "corrected", "content", "article_meta", "agent_gender", "agent_dep_job"]
        if key in inputs
    }
    master = build_master_from_frames(**legacy_inputs)
    return derive_analysis_variables(master)


def cleanup_legacy_outputs(out_dir: Path = OUT_DIR) -> None:
    for relative in [
        "analysis_master.xlsx",
        "tables/validation_report.json",
        "tables/descriptive_statistics.xlsx",
        "tables/anova_tukey_results.xlsx",
        "tables/regression_results.xlsx",
    ]:
        path = out_dir / relative
        if path.exists():
            path.unlink()
    for figure_name in LEGACY_FIGURE_NAMES:
        path = out_dir / "figures" / figure_name
        if path.exists():
            path.unlink()


def _clean_level1_content_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols: list[str] = []
    for column in df.columns:
        column_text = str(column)
        if column in LEVEL1_FORBIDDEN_COLUMNS:
            drop_cols.append(column)
        elif column_text.endswith("_content"):
            drop_cols.append(column)
        elif "(Content)" in column_text or "(Title+Content)" in column_text:
            drop_cols.append(column)
        elif column_text.startswith("gender_pct_"):
            drop_cols.append(column)
        elif column_text.startswith("repeat_exposure_"):
            drop_cols.append(column)
    return df.drop(columns=drop_cols, errors="ignore")


def build_level1_content_master(
    *,
    final: pd.DataFrame,
    corrected: pd.DataFrame,
    content: pd.DataFrame,
    article_meta: pd.DataFrame | None = None,
) -> pd.DataFrame:
    master = _with_agent_article_keys(rename_topic_score_columns_to_english(final))
    master["_row_id"] = np.arange(len(master))
    master["_title_exact"] = master["Title"].map(exact_text) if "Title" in master.columns else master["article_title"].map(exact_text)

    corrected_agg = standardize_topic_labels_to_english(
        aggregate_corrected_layers(corrected),
        "TopContentCluster_corrected",
        source_column="TopContentCluster_corrected_source",
    )
    exact_keys = ["_agent_exact", "_article_exact"]
    normalized_keys = ["_agent_key", "_article_key"]
    corrected_value_cols = [column for column in corrected_agg.columns if column not in {*exact_keys, *normalized_keys}]
    master = master.merge(corrected_agg[[*exact_keys, *corrected_value_cols]], on=exact_keys, how="left")

    unmatched = master["cascade_size"].isna() if "cascade_size" in master.columns else pd.Series(False, index=master.index)
    if unmatched.any():
        unique_fallback = corrected_agg[
            ~corrected_agg.duplicated(normalized_keys, keep=False)
        ][[*normalized_keys, *corrected_value_cols]].copy()
        unique_fallback = unique_fallback.rename(columns={column: f"{column}_fallback" for column in corrected_value_cols})
        master = master.merge(unique_fallback, on=normalized_keys, how="left")
        for column in corrected_value_cols:
            fallback_column = f"{column}_fallback"
            if fallback_column in master.columns:
                master[column] = master[column].combine_first(master[fallback_column])
                master = master.drop(columns=[fallback_column])

    prepared_content = _prepare_content_exact(content)
    master = master.merge(prepared_content, on="_title_exact", how="left", suffixes=("", "_content"))
    if "TopContentCluster_content" in master.columns:
        master["TopContentCluster"] = master.get("TopContentCluster").combine_first(master["TopContentCluster_content"])
        master = master.drop(columns=["TopContentCluster_content"])
    if "TopContentCluster" not in master.columns and "TopContentCluster_corrected" in master.columns:
        master["TopContentCluster"] = master["TopContentCluster_corrected"]
    elif "TopContentCluster_corrected" in master.columns:
        master["TopContentCluster"] = master["TopContentCluster"].combine_first(master["TopContentCluster_corrected"])
    master = standardize_topic_labels_to_english(master, "TopContentCluster")

    prepared_meta = _prepare_article_meta_exact(article_meta)
    if prepared_meta is not None:
        master = master.merge(prepared_meta, on="_title_exact", how="left")

    layer_cols = [column for column in master.columns if re.fullmatch(r"layer_\d+_count", str(column))]
    positive_layer_cols = [column for column in layer_cols if column != "layer_0_count"]
    if positive_layer_cols:
        master["cascade_size_excl_layer0"] = master[positive_layer_cols].sum(axis=1)
    if {"first_layer_width", "second_layer_width"}.issubset(master.columns):
        master["direct_width_reach"] = (
            pd.to_numeric(master["first_layer_width"], errors="coerce").fillna(0)
            + pd.to_numeric(master["second_layer_width"], errors="coerce").fillna(0)
        )

    master = master.drop(columns=[column for column in LEVEL1_FORBIDDEN_COLUMNS if column in master.columns], errors="ignore")
    master = derive_analysis_variables(master)
    master = _clean_level1_content_columns(master)
    return _drop_internal_columns(master.sort_values("_row_id").reset_index(drop=True))


def build_level2_agent_network_master(
    *,
    agent_level: pd.DataFrame,
    final: pd.DataFrame,
    agent_gender: pd.DataFrame | None = None,
    agent_dep_job: pd.DataFrame | None = None,
) -> pd.DataFrame:
    master = agent_level.copy()
    attrs = _agent_attribute_frame(final, agent_gender=agent_gender, agent_dep_job=agent_dep_job)
    master["_agent_key"] = master["agent_name"].map(normalize_text)
    article_counts = (
        final.assign(_agent_key=final["agent_name"].map(normalize_text))
        .groupby("_agent_key", dropna=False)
        .size()
        .rename("article_count_per_agent")
        .reset_index()
    )
    master = master.merge(attrs.drop(columns=["agent_name"], errors="ignore"), on="_agent_key", how="left")
    master = master.merge(article_counts, on="_agent_key", how="left")
    master["article_count_per_agent"] = pd.to_numeric(master["article_count_per_agent"], errors="coerce").fillna(0)
    master["log_article_count_per_agent"] = np.log1p(master["article_count_per_agent"])
    master["log_agent_cascade_size_mean"] = np.log1p(pd.to_numeric(master["cascade_size_mean"], errors="coerce").fillna(0))
    master = master.drop(columns=["matchscore_mean", "profession_content_match_mean"], errors="ignore")
    for column in ["JobCategory", "agent_gender"]:
        if column in master.columns:
            master[column] = master[column].astype("string")
    return _drop_internal_columns(master)


def build_level3_agent_topic_match_master(
    *,
    agent_topic: pd.DataFrame,
    final: pd.DataFrame,
    content: pd.DataFrame,
    article_meta: pd.DataFrame | None = None,
    agent_gender: pd.DataFrame | None = None,
    agent_dep_job: pd.DataFrame | None = None,
) -> pd.DataFrame:
    topic_master = standardize_topic_labels_to_english(
        agent_topic.copy(),
        "TopContentCluster",
        source_column="TopContentCluster_source_zh",
    )
    final_with_content = rename_topic_score_columns_to_english(final.copy())
    final_with_content["_title_exact"] = final_with_content["Title"].map(exact_text)
    content_prepared = _prepare_content_exact(content)
    final_with_content = final_with_content.merge(content_prepared, on="_title_exact", how="left", suffixes=("", "_content"))
    if "TopContentCluster_content" in final_with_content.columns:
        final_with_content["TopContentCluster"] = final_with_content.get("TopContentCluster").combine_first(final_with_content["TopContentCluster_content"])
        final_with_content = final_with_content.drop(columns=["TopContentCluster_content"])
    final_with_content = standardize_topic_labels_to_english(final_with_content, "TopContentCluster")

    meta = _prepare_article_meta_exact(article_meta)
    if meta is not None:
        final_with_content = final_with_content.merge(meta, on="_title_exact", how="left")

    for column in ["MatchScore", "ProfessionContentMatch", "WordCount", "HasImage", "NumImages", "CosineSim"]:
        if column in final_with_content.columns:
            final_with_content[column] = pd.to_numeric(final_with_content[column], errors="coerce")

    grouped = (
        final_with_content.dropna(subset=["agent_name", "TopContentCluster"])
        .groupby(["agent_name", "TopContentCluster"], dropna=False)
        .agg(
            agent_topic_article_n=("MatchScore", "size"),
            MatchScore_mean=("MatchScore", "mean"),
            MatchScore_median=("MatchScore", "median"),
            ProfessionContentMatch_mean=("ProfessionContentMatch", "mean"),
            matched_case_count=("ProfessionContentMatch", "sum"),
            WordCount_mean=("WordCount", "mean"),
            HasImage_share=("HasImage", "mean"),
            NumImages_mean=("NumImages", "mean"),
            CosineSim_mean=("CosineSim", "mean"),
        )
        .reset_index()
    )
    master = topic_master.merge(grouped, on=["agent_name", "TopContentCluster"], how="left")

    attrs = _agent_attribute_frame(final, agent_gender=agent_gender, agent_dep_job=agent_dep_job)
    master = master.merge(attrs, on="agent_name", how="left", suffixes=("", "_attr"))
    if "JobCategory_attr" in master.columns:
        master["JobCategory"] = master.get("JobCategory").combine_first(master["JobCategory_attr"])
        master = master.drop(columns=["JobCategory_attr"])
    if "agent_job_attr" in master.columns:
            master["agent_job"] = master.get("agent_job").combine_first(master["agent_job_attr"])
            master = master.drop(columns=["agent_job_attr"])

    if "JobCategory" in final_with_content.columns:
        final_with_content["JobCategory"] = final_with_content["JobCategory"].astype("string")
    if "JobCategory" in master.columns:
        master["JobCategory"] = master["JobCategory"].astype("string")
    job_topic_counts = (
        final_with_content.dropna(subset=["JobCategory", "TopContentCluster"])
        .groupby(["JobCategory", "TopContentCluster"], dropna=False)
        .size()
        .rename("job_topic_cell_n")
        .reset_index()
    )
    master = master.merge(job_topic_counts, on=["JobCategory", "TopContentCluster"], how="left")
    master["agent_topic_article_n"] = pd.to_numeric(master["agent_topic_article_n"], errors="coerce").fillna(0)
    master["job_topic_cell_n"] = pd.to_numeric(master["job_topic_cell_n"], errors="coerce").fillna(0)
    master["log_agent_topic_article_n"] = np.log1p(master["agent_topic_article_n"])
    master["log_agent_topic_cascade_size_mean"] = np.log1p(pd.to_numeric(master["cascade_size_mean"], errors="coerce").fillna(0))
    master["is_sparse_cell_10"] = (master["agent_topic_article_n"] < 10).astype(int)
    master["is_sparse_cell_30"] = (master["agent_topic_article_n"] < 30).astype(int)
    for column in ["JobCategory", "agent_gender", "TopContentCluster"]:
        if column in master.columns:
            master[column] = master[column].astype("string")
    return _drop_internal_columns(master)


def check_source_readiness(
    inputs: dict[str, pd.DataFrame],
    *,
    expected_rows: dict[str, int] | None = None,
    raise_on_error: bool = False,
) -> dict[str, pd.DataFrame]:
    rows = []
    expected = expected_rows or {
        "final": EXPECTED_MASTER_ROWS,
        "agent_level": EXPECTED_AGENT_ROWS,
        "agent_topic": EXPECTED_AGENT_TOPIC_ROWS,
    }
    gate_rows: list[dict] = []

    def add_gate(
        check: str,
        passed: bool,
        *,
        source: str = "all",
        severity: str = "error",
        details: str = "",
        actual: object = np.nan,
        expected_value: object = np.nan,
    ) -> None:
        gate_rows.append(
            {
                "check": check,
                "source": source,
                "severity": severity,
                "passed": bool(passed),
                "ready_to_build": bool(passed or severity != "error"),
                "actual": actual,
                "expected": expected_value,
                "details": details,
            }
        )

    for name, frame in inputs.items():
        expected_n = expected.get(name, np.nan)
        row_count_ok = bool(name not in expected or len(frame) == expected[name])
        rows.append(
            {
                "source": name,
                "rows": int(len(frame)),
                "columns": int(frame.shape[1]),
                "expected_rows": expected_n,
                "row_count_ok": row_count_ok,
            }
        )
        if name in expected:
            add_gate(
                "row_count",
                row_count_ok,
                source=name,
                actual=int(len(frame)),
                expected_value=int(expected[name]),
            )

    required_status = _required_column_status(inputs)
    for _, row in required_status.iterrows():
        add_gate(
            "source_required_columns",
            bool(row["passed"]),
            source=row["source"],
            actual=int(row["missing_columns_n"]),
            expected_value=0,
            details=str(row["missing_columns"]),
        )

    final = inputs["final"]
    content = inputs["content"]
    article_meta = inputs.get("article_meta", pd.DataFrame())
    title_join = pd.DataFrame(
        [
            _title_coverage_row(final, content, target_name="content"),
            _title_coverage_row(final, article_meta, target_name="article_meta"),
        ]
    )
    for _, row in title_join.iterrows():
        add_gate(
            row["join"],
            bool(row["exact_join_ok"]),
            actual=int(row["missing_final_titles_in_target"]) if pd.notna(row["missing_final_titles_in_target"]) else np.nan,
            expected_value=0,
            details=f"normalized_fallback_possible={row['normalized_fallback_possible']}",
        )

    primary_key_rows = []
    primary_specs = [
        ("final", ["agent_name", "article_title"], "final_agent_article_key_unique"),
        ("agent_level", ["agent_name"], "agent_level_primary_key_unique"),
        ("agent_topic", ["agent_name", "TopContentCluster"], "agent_topic_primary_key_unique"),
    ]
    for source, columns, check_name in primary_specs:
        frame = inputs.get(source, pd.DataFrame())
        work = standardize_topic_labels_to_english(frame.copy(), "TopContentCluster") if "TopContentCluster" in frame.columns else frame
        duplicate_n = _duplicate_count(work, columns, normalize=False)
        normalized_duplicate_n = _duplicate_count(work, columns, normalize=True)
        primary_key_rows.append(
            {
                "source": source,
                "key_columns": ", ".join(columns),
                "duplicate_rows_n": duplicate_n,
                "normalized_duplicate_rows_n": normalized_duplicate_n,
                "passed": duplicate_n == 0,
            }
        )
        add_gate(check_name, duplicate_n == 0, source=source, actual=duplicate_n, expected_value=0)
        add_gate(
            "normalized_key_ambiguity",
            normalized_duplicate_n == 0,
            source=source,
            severity="warning",
            actual=normalized_duplicate_n,
            expected_value=0,
            details="Exact keys are authoritative; normalized duplicates are reported because fallback joins can become ambiguous.",
        )

    topic_mapping = _topic_label_standardization_report(inputs)
    unmapped_rows = int(topic_mapping.loc[~topic_mapping["mapped"].astype(bool), "rows_n"].sum()) if not topic_mapping.empty else 0
    add_gate(
        "topic_label_standardization",
        unmapped_rows == 0,
        actual=unmapped_rows,
        expected_value=0,
        details="All observed topic labels must map to English canonical labels.",
    )

    gate = pd.DataFrame(gate_rows)
    errors = gate.loc[~gate["ready_to_build"], "check"].dropna().astype(str).unique().tolist()
    if errors and raise_on_error:
        raise ValueError(f"Source readiness failed: {', '.join(errors)}")

    return {
        "readiness_gate": gate,
        "source_summary": pd.DataFrame(rows),
        "required_column_status": required_status,
        "title_join_coverage": title_join,
        "primary_key_diagnostics": pd.DataFrame(primary_key_rows),
        "topic_label_standardization": topic_mapping,
        **make_join_quality_tables(inputs),
    }


def write_variable_role_map() -> pd.DataFrame:
    rows = []

    def add(
        variable: str,
        level: str,
        source_file: str,
        role: str,
        allowed_as_predictor: bool,
        allowed_as_outcome: bool,
        leakage_note: str = "",
        thesis_interpretation_note: str = "",
    ) -> None:
        rows.append(
            (
                variable,
                level,
                source_file,
                role,
                allowed_as_predictor,
                allowed_as_outcome,
                leakage_note,
                thesis_interpretation_note,
            )
        )

    for variable in ["agent_name", "article_title", "Title"]:
        add(variable, "Level 1", "final_results", "identifier", False, False, "", "Article-agent case identifier only.")
    add("TopContentCluster", "Level 1", "S2 translated", "content predictor", True, False, "", "Main categorical content-topic predictor.")
    add("TopTitleCluster", "Level 1", "S2 translated", "descriptive content field", False, False, "", "Title-only topic descriptor.")
    for variable in CANONICAL_TOPIC_SCORE_COLUMNS:
        add(variable, "Level 1", "S2 translated", "topic-score robustness predictor", True, False, "", "Use only in robustness/PCA specifications, not with all topic dummies.")
    for variable in ["CosineSim", "EuclideanDist", "ManhattanDist"]:
        add(variable, "Level 1", "S2 translated", "semantic alignment predictor", True, False, "", "CosineSim is main; distances are robustness alternatives.")
    for variable in ["WordCount", "HasImage", "NumImages"]:
        add(variable, "Level 1", "S2 metadata", "content control", True, False, "", "Observable article-format control.")
    for variable in [
        "cascade_size",
        "total_reads",
        "unique_reader_count",
        "first_layer_width",
        "second_layer_width",
        "depth",
        "corrected_depth",
        "reshare_pct",
        "duration_mean_s",
        "duration_mean_s_winsorized",
        "log_reach",
        "log_total_reads",
        "log_duration",
        "any_reshare",
        "wiener_index",
        "wiener_index_winsorized",
        "structural_virality",
        "structural_virality_winsorized",
        "cascade_size_excl_layer0",
        "direct_width_reach",
    ]:
        add(variable, "Level 1", "corrected layers/final_results", "diffusion outcome", False, True, "Observed after posting; do not use as leakage-free predictor.", "Content-level diffusion performance or cascade-shape outcome.")

    for variable in ["agent_name", "agent_dep", "agent_job"]:
        add(variable, "Level 2", "S3/final_results/agent_dep_job", "agent descriptor", False, False, "", "Used for description or deriving existing S3 categories, not as high-cardinality main regression predictors.")
    for variable in ["JobCategory", "agent_gender"]:
        add(variable, "Level 2", "final_results/S3", "agent attribute predictor", True, False, "", "Main role/gender grouping variable.")
    add("article_count_per_agent", "Level 2", "final_results", "exposure/stability control", True, False, "", "Number of observed article-agent cases for the agent.")
    add("log_article_count_per_agent", "Level 2", "final_results", "exposure/stability control", True, False, "", "Main article-count adjustment.")
    for variable in [
        "cascade_size_mean",
        "log_agent_cascade_size_mean",
        "reshare_mean",
        "depth_mean",
        "second_layer_width_avg",
        "structural_virality_mean",
        "duration_mean_of_means",
    ]:
        add(variable, "Level 2", "agent_level_results", "agent-level diffusion outcome", False, True, "Aggregated observed diffusion result.", "Agent-level average diffusion pattern or capability measure.")
    for variable in [
        "agent_deg_centrality_mean",
        "avg_out_degree_centrality_mean",
        "centrality_mean",
        "repeat_exposure_1st_nodes_pct",
        "repeat_exposure_2nd_nodes_pct",
        "gender_assortativity_mean",
    ]:
        add(variable, "Level 2", "agent_level_results", "diffusion-pattern descriptor", False, False, "Derived from observed diffusion/network; do not interpret as an ex-ante causal predictor.", "Use only as a supplementary diagnostic or descriptive heterogeneity descriptor.")

    for variable in ["agent_name", "TopContentCluster", "JobCategory", "agent_gender"]:
        add(variable, "Level 3", "agent_topic/final_results/S3", "agent-topic grouping variable", True, False, "", "Defines content-agent matching cells and controls.")
    for variable in ["MatchScore_mean", "MatchScore_median", "ProfessionContentMatch_mean", "matched_case_count"]:
        add(variable, "Level 3", "final_results aggregated", "matching predictor", True, False, "", "Continuous and binary matching specifications must be estimated separately.")
    for variable in [
        "agent_topic_article_n",
        "log_agent_topic_article_n",
        "job_topic_cell_n",
        "WordCount_mean",
        "HasImage_share",
        "NumImages_mean",
        "CosineSim_mean",
    ]:
        add(variable, "Level 3", "final_results/S2 aggregated", "leakage-safe control", True, False, "", "Exposure volume or content feature control.")
    for variable in ["is_sparse_cell_10", "is_sparse_cell_30"]:
        add(variable, "Level 3", "final_results aggregated", "diagnostic flag", False, False, "", "Sparse-cell interpretation/sensitivity flag.")
    for variable in [
        "cascade_size_mean",
        "log_agent_topic_cascade_size_mean",
        "depth_mean",
        "reshare_mean",
        "structural_virality_mean",
        "duration_mean_of_means",
    ]:
        add(variable, "Level 3", "agent_topic_level_results", "agent-topic diffusion outcome", False, True, "Aggregated observed diffusion result.", "Outcome for content-agent matching analysis.")
    return pd.DataFrame(
        rows,
        columns=[
            "variable",
            "level",
            "source_file",
            "role",
            "allowed_as_predictor",
            "allowed_as_outcome",
            "leakage_note",
            "thesis_interpretation_note",
        ],
    )


def _describe_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in df.columns]
    desc = df[available].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    desc.insert(0, "variable", desc.index)
    return desc.reset_index(drop=True)


def _group_outcomes(df: pd.DataFrame, group_col: str, outcomes: list[str]) -> pd.DataFrame:
    if group_col not in df.columns:
        return pd.DataFrame()
    available = [column for column in outcomes if column in df.columns]
    work = df[[group_col, *available]].dropna(subset=[group_col])
    if work.empty:
        return pd.DataFrame()
    grouped = work.groupby(group_col, dropna=False)[available].agg(["count", "mean", "median", "std"])
    grouped.columns = [f"{outcome}_{stat}" for outcome, stat in grouped.columns]
    return grouped.reset_index()


def _opportunity_tables(master: pd.DataFrame, min_cell_n: int) -> dict[str, pd.DataFrame]:
    required = {"JobCategory", "TopContentCluster"}
    if not required.issubset(master.columns):
        return {}
    metrics = {
        "log_reach": "log_reach_mean",
        "depth": "depth_mean",
        "reshare_pct": "reshare_pct_mean",
        "MatchScore": "MatchScore_mean",
    }
    available_metrics = {column: name for column, name in metrics.items() if column in master.columns}
    if not available_metrics:
        return {}

    grouped = (
        master.groupby(["JobCategory", "TopContentCluster"], dropna=False)
        .agg(cell_n=("log_reach", "size"), **{name: (column, "mean") for column, name in available_metrics.items()})
        .reset_index()
    )
    grouped["is_sparse"] = (grouped["cell_n"] < min_cell_n).astype(int)
    for report_col in available_metrics.values():
        grouped[f"{report_col}_reportable"] = grouped[report_col].where(grouped["is_sparse"].eq(0))

    tables = {"job_topic_opportunity_long": grouped}
    counts = grouped.pivot(index="JobCategory", columns="TopContentCluster", values="cell_n").reset_index()
    tables["job_topic_opportunity_counts"] = counts
    pivot_specs = {
        "job_topic_opportunity_log_reach": "log_reach_mean_reportable",
        "job_topic_opportunity_depth": "depth_mean_reportable",
        "job_topic_opportunity_reshare": "reshare_pct_mean_reportable",
        "job_topic_opportunity_match": "MatchScore_mean_reportable",
    }
    for name, value_col in pivot_specs.items():
        if value_col in grouped.columns:
            tables[name] = grouped.pivot(
                index="JobCategory", columns="TopContentCluster", values=value_col
            ).reset_index()
    return tables


def make_descriptive_tables(master: pd.DataFrame, min_opportunity_cell_n: int = 30) -> dict[str, pd.DataFrame]:
    overview = pd.DataFrame(
        [
            ("agent_article_rows", len(master)),
            ("unique_agents", master["agent_name"].nunique() if "agent_name" in master else np.nan),
            ("unique_articles", master["article_title"].nunique() if "article_title" in master else np.nan),
            (
                "unique_topics",
                master["TopContentCluster"].nunique(dropna=True)
                if "TopContentCluster" in master
                else np.nan,
            ),
            (
                "unique_job_categories",
                master["JobCategory"].nunique(dropna=True) if "JobCategory" in master else np.nan,
            ),
        ],
        columns=["metric", "value"],
    )

    missingness = pd.DataFrame(
        {
            "variable": master.columns,
            "missing_n": master.isna().sum().values,
            "missing_pct": master.isna().mean().values,
        }
    ).sort_values(["missing_pct", "variable"], ascending=[False, True])

    tables = {
        "sample_overview": overview,
        "outcome_descriptives": _describe_numeric(master, OUTCOME_COLUMNS),
        "key_variable_missingness": missingness,
        "topic_distribution": master["TopContentCluster"].value_counts(dropna=False).rename_axis(
            "TopContentCluster"
        ).reset_index(name="n")
        if "TopContentCluster" in master
        else pd.DataFrame(),
        "jobcategory_distribution": master["JobCategory"].value_counts(dropna=False).rename_axis(
            "JobCategory"
        ).reset_index(name="n")
        if "JobCategory" in master
        else pd.DataFrame(),
        "profession_match_distribution": master["ProfessionContentMatch"]
        .value_counts(dropna=False)
        .rename_axis("ProfessionContentMatch")
        .reset_index(name="n")
        if "ProfessionContentMatch" in master
        else pd.DataFrame(),
        "topic_outcomes": _group_outcomes(master, "TopContentCluster", ANALYSIS_OUTCOMES),
        "jobcategory_outcomes": _group_outcomes(master, "JobCategory", ANALYSIS_OUTCOMES),
        "cosine_deciles": _group_outcomes(master, "CosineSimDecile", ANALYSIS_OUTCOMES),
        "cosine_quartiles": _group_outcomes(master, "CosineSimQuartile", ANALYSIS_OUTCOMES),
        "matchscore_deciles": _group_outcomes(master, "MatchScoreDecile", ANALYSIS_OUTCOMES),
        "high_low_match": _group_outcomes(master, "HighMatch", ANALYSIS_OUTCOMES),
        "agent_heterogeneity": _group_outcomes(master, "agent_name", ANALYSIS_OUTCOMES)
        .sort_values("log_reach_mean", ascending=False)
        if "agent_name" in master
        else pd.DataFrame(),
    }

    topic_cols = _topic_score_columns(master)
    corr_cols = [*topic_cols, "CosineSim", "MatchScore", *ANALYSIS_OUTCOMES]
    corr_cols = [column for column in corr_cols if column in master.columns]
    if corr_cols:
        corr = master[corr_cols].corr(numeric_only=True)
        tables["content_outcome_correlations"] = corr.reset_index(names="variable")

    tables.update(_opportunity_tables(master, min_opportunity_cell_n))

    if {"agent_gender", "gender_pct_aud_0", "gender_pct_aud_1"}.issubset(master.columns):
        tables["agent_gender_summary"] = _group_outcomes(
            master, "agent_gender", ["gender_pct_aud_0", "gender_pct_aud_1", *ANALYSIS_OUTCOMES]
        )

    return tables


def write_excel_tables(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        wrote_any = False
        for name, table in tables.items():
            if table is None:
                continue
            sheet = _sanitize_sheet_name(name)
            table.to_excel(writer, sheet_name=sheet, index=False)
            worksheet = writer.sheets[sheet]
            worksheet.freeze_panes(1, 0)
            for idx, column in enumerate(table.columns):
                width = min(max(len(str(column)) + 2, 12), 48)
                worksheet.set_column(idx, idx, width)
            wrote_any = True
        if not wrote_any:
            pd.DataFrame({"message": ["No tables generated"]}).to_excel(writer, index=False)


def _welch_anova(work: pd.DataFrame, group_col: str, outcome: str) -> dict:
    samples = [values["y"].values for _, values in work.groupby("group")]
    result = anova_oneway(samples, use_var="unequal")
    return {
        "group": group_col,
        "outcome": outcome,
        "n": int(len(work)),
        "groups_n": int(work["group"].nunique()),
        "welch_stat": float(result.statistic),
        "p_value": float(result.pvalue),
        "df_num": float(result.df[0]),
        "df_denom": float(result.df[1]),
    }


def _games_howell_pairs(work: pd.DataFrame, group_col: str, outcome: str) -> pd.DataFrame:
    stats_by_group = work.groupby("group")["y"].agg(["mean", "var", "count"]).reset_index()
    rows = []
    groups_n = len(stats_by_group)
    for i in range(groups_n):
        for j in range(i + 1, groups_n):
            g1 = stats_by_group.iloc[i]
            g2 = stats_by_group.iloc[j]
            n1, n2 = float(g1["count"]), float(g2["count"])
            v1 = float(g1["var"]) if pd.notna(g1["var"]) else 0.0
            v2 = float(g2["var"]) if pd.notna(g2["var"]) else 0.0
            se2 = v1 / n1 + v2 / n2
            if se2 <= 0:
                continue
            mean_diff = float(g2["mean"] - g1["mean"])
            q_stat = abs(mean_diff) / math.sqrt(0.5 * se2)
            numerator = se2**2
            denominator = ((v1 / n1) ** 2 / (n1 - 1) if n1 > 1 else 0) + (
                (v2 / n2) ** 2 / (n2 - 1) if n2 > 1 else 0
            )
            df = numerator / denominator if denominator else np.nan
            p_value = float(stats.studentized_range.sf(q_stat, groups_n, df)) if pd.notna(df) else np.nan
            rows.append(
                {
                    "group": group_col,
                    "outcome": outcome,
                    "group1": g1["group"],
                    "group2": g2["group"],
                    "meandiff": mean_diff,
                    "q_stat": float(q_stat),
                    "df": float(df) if pd.notna(df) else np.nan,
                    "p_value": p_value,
                    "n1": int(n1),
                    "n2": int(n2),
                }
            )
    return pd.DataFrame(rows)


def _dunn_pairs(work: pd.DataFrame, group_col: str, outcome: str) -> pd.DataFrame:
    ranked = work.copy()
    ranked["rank"] = stats.rankdata(ranked["y"].values, method="average")
    tie_correction = stats.tiecorrect(ranked["rank"].values)
    n_total = len(ranked)
    rank_stats = ranked.groupby("group")["rank"].agg(["mean", "count"]).reset_index()
    rows = []
    for i in range(len(rank_stats)):
        for j in range(i + 1, len(rank_stats)):
            g1 = rank_stats.iloc[i]
            g2 = rank_stats.iloc[j]
            n1, n2 = float(g1["count"]), float(g2["count"])
            variance = (n_total * (n_total + 1) / 12.0) * tie_correction * (1.0 / n1 + 1.0 / n2)
            if variance <= 0:
                continue
            z_stat = float((g1["mean"] - g2["mean"]) / math.sqrt(variance))
            p_value = float(2 * stats.norm.sf(abs(z_stat)))
            rows.append(
                {
                    "group": group_col,
                    "outcome": outcome,
                    "group1": g1["group"],
                    "group2": g2["group"],
                    "z_stat": z_stat,
                    "p_value": p_value,
                    "n1": int(n1),
                    "n2": int(n2),
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        _, adjusted, _, reject = multipletests(result["p_value"], method="holm")
        result["p_adjusted_holm"] = adjusted
        result["reject_0_05"] = reject
    return result


def run_group_tests(master: pd.DataFrame) -> dict[str, pd.DataFrame]:
    groups = ["TopContentCluster", "JobCategory", "ProfessionContentMatch"]
    anova_rows = []
    welch_rows = []
    tukey_rows = []
    games_howell_rows = []
    kruskal_rows = []
    dunn_rows = []

    for group_col in groups:
        if group_col not in master.columns:
            continue
        for outcome in ANALYSIS_OUTCOMES:
            if outcome not in master.columns:
                continue
            work = master[[group_col, outcome]].dropna().rename(columns={group_col: "group", outcome: "y"})
            work["group"] = work["group"].astype(str)
            counts = work["group"].value_counts()
            valid_groups = counts[counts >= 2].index
            work = work[work["group"].isin(valid_groups)]
            if work["group"].nunique() < 2:
                continue

            model = smf.ols("y ~ C(group)", data=work).fit()
            table = anova_lm(model, typ=2)
            ss_between = float(table.loc["C(group)", "sum_sq"])
            ss_total = float(ss_between + table.loc["Residual", "sum_sq"])
            eta_sq = ss_between / ss_total if ss_total else np.nan
            anova_rows.append(
                {
                    "group": group_col,
                    "outcome": outcome,
                    "n": int(len(work)),
                    "groups_n": int(work["group"].nunique()),
                    "f_stat": float(table.loc["C(group)", "F"]),
                    "p_value": float(table.loc["C(group)", "PR(>F)"]),
                    "eta_squared": eta_sq,
                }
            )
            try:
                welch_rows.append(_welch_anova(work, group_col, outcome))
            except Exception as exc:
                welch_rows.append(
                    {
                        "group": group_col,
                        "outcome": outcome,
                        "n": int(len(work)),
                        "groups_n": int(work["group"].nunique()),
                        "error": repr(exc),
                    }
                )

            samples = [values["y"].values for _, values in work.groupby("group")]
            h_stat, h_p = stats.kruskal(*samples)
            epsilon_sq = max((h_stat - work["group"].nunique() + 1) / (len(work) - work["group"].nunique()), 0)
            kruskal_rows.append(
                {
                    "group": group_col,
                    "outcome": outcome,
                    "n": int(len(work)),
                    "groups_n": int(work["group"].nunique()),
                    "h_stat": float(h_stat),
                    "p_value": float(h_p),
                    "epsilon_squared": float(epsilon_sq),
                }
            )

            tukey = pairwise_tukeyhsd(endog=work["y"], groups=work["group"], alpha=0.05)
            tukey_table = pd.DataFrame(tukey.summary().data[1:], columns=tukey.summary().data[0])
            tukey_table.insert(0, "group", group_col)
            tukey_table.insert(1, "outcome", outcome)
            tukey_table.insert(2, "n", int(len(work)))
            tukey_rows.append(tukey_table)
            games_howell = _games_howell_pairs(work, group_col, outcome)
            if not games_howell.empty:
                games_howell_rows.append(games_howell)
            dunn = _dunn_pairs(work, group_col, outcome)
            if not dunn.empty:
                dunn_rows.append(dunn)

    return {
        "anova_summary": pd.DataFrame(anova_rows),
        "welch_anova_summary": pd.DataFrame(welch_rows),
        "tukey_pairs": pd.concat(tukey_rows, ignore_index=True) if tukey_rows else pd.DataFrame(),
        "games_howell_pairs": pd.concat(games_howell_rows, ignore_index=True)
        if games_howell_rows
        else pd.DataFrame(),
        "kruskal_summary": pd.DataFrame(kruskal_rows),
        "dunn_pairs": pd.concat(dunn_rows, ignore_index=True) if dunn_rows else pd.DataFrame(),
    }


def _regression_data(master: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = master.copy()
    topic_cols = _topic_score_columns(df)
    continuous = [
        *topic_cols,
        "CosineSim",
        "EuclideanDist",
        "ManhattanDist",
        "WordCount",
        "NumImages",
        "MatchScore",
        "agent_deg_centrality",
    ]
    df = _standardize_for_regression(df, continuous)
    topic_terms = [f"z_topic_{idx}" for idx in range(1, len(topic_cols) + 1) if f"z_topic_{idx}" in df]
    return df, topic_terms


def _model_records(model, model_name: str, outcome: str, family: str) -> tuple[dict, pd.DataFrame]:
    summary = {
        "model": model_name,
        "outcome": outcome,
        "family": family,
        "n": int(model.nobs),
        "aic": float(getattr(model, "aic", np.nan)),
        "bic": float(getattr(model, "bic", np.nan)) if np.isfinite(getattr(model, "bic", np.nan)) else np.nan,
        "adj_r2": float(getattr(model, "rsquared_adj", np.nan)),
        "pseudo_r2": float(1 - model.llf / model.llnull)
        if hasattr(model, "llf") and hasattr(model, "llnull") and model.llnull
        else np.nan,
    }
    conf = model.conf_int()
    coeff = pd.DataFrame(
        {
            "term": model.params.index,
            "coef": model.params.values,
            "std_error": model.bse.values,
            "p_value": model.pvalues.values,
            "ci_low": conf[0].values,
            "ci_high": conf[1].values,
        }
    )
    coeff["standardized_beta"] = np.where(coeff["term"].astype(str).str.startswith("z_"), coeff["coef"], np.nan)
    coeff.insert(0, "model", model_name)
    coeff.insert(1, "outcome", outcome)
    coeff.insert(2, "family", family)
    return summary, coeff


def _fit_formula(
    df: pd.DataFrame,
    formula: str,
    outcome: str,
    *,
    family: str,
    model_name: str,
    cluster_groups: pd.Series | None = None,
    weights: str | pd.Series | None = None,
) -> tuple[dict, pd.DataFrame] | None:
    try:
        required = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)) - {"C"})
        work = df.dropna(subset=[column for column in required if column in df.columns]).copy()
        aligned_weights = None
        if weights is not None:
            if isinstance(weights, str):
                if weights not in work.columns:
                    return None
                aligned_weights = pd.to_numeric(work[weights], errors="coerce")
            else:
                aligned_weights = pd.to_numeric(weights.loc[work.index], errors="coerce")
            keep = aligned_weights.notna() & aligned_weights.gt(0)
            work = work.loc[keep].copy()
            aligned_weights = aligned_weights.loc[work.index]
        if len(work) < 50:
            return None
        aligned_groups = cluster_groups.loc[work.index] if cluster_groups is not None else None
        family_label = "weighted_ols" if family == "weighted_ols" or aligned_weights is not None else family
        if family in {"ols", "weighted_ols"}:
            if aligned_groups is not None:
                model = smf.wls(formula, data=work, weights=aligned_weights) if aligned_weights is not None else smf.ols(formula, data=work)
                fit = model.fit(
                    cov_type="cluster", cov_kwds={"groups": aligned_groups}
                )
            elif aligned_weights is not None:
                fit = smf.wls(formula, data=work, weights=aligned_weights).fit(cov_type="HC3")
            else:
                fit = smf.ols(formula, data=work).fit(cov_type="HC3")
        elif family == "binomial":
            cov_type = "cluster" if aligned_groups is not None else "HC0"
            cov_kwds = {"groups": aligned_groups} if aligned_groups is not None else None
            fit = smf.glm(formula, data=work, family=sm.families.Binomial()).fit(
                cov_type=cov_type, cov_kwds=cov_kwds
            )
        elif family == "poisson":
            cov_type = "cluster" if aligned_groups is not None else "HC0"
            cov_kwds = {"groups": aligned_groups} if aligned_groups is not None else None
            fit = smf.glm(formula, data=work, family=sm.families.Poisson()).fit(
                cov_type=cov_type, cov_kwds=cov_kwds
            )
        elif family == "negative_binomial":
            cov_type = "cluster" if aligned_groups is not None else "HC0"
            cov_kwds = {"groups": aligned_groups} if aligned_groups is not None else None
            fit = smf.negativebinomial(formula, data=work).fit(
                disp=False,
                maxiter=200,
                cov_type=cov_type,
                cov_kwds=cov_kwds,
            )
        else:
            raise ValueError(f"Unknown family: {family}")
        return _model_records(fit, model_name, outcome, family_label)
    except Exception as exc:  # Keep the pipeline running while reporting model failures.
        summary = {
            "model": model_name,
            "outcome": outcome,
            "family": family,
            "n": 0,
            "aic": np.nan,
            "bic": np.nan,
            "adj_r2": np.nan,
            "pseudo_r2": np.nan,
            "error": repr(exc),
        }
        coeff = pd.DataFrame()
        return summary, coeff


def _overdispersion_diagnostic(df: pd.DataFrame, formula: str, outcome: str, model_name: str) -> dict:
    required = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)) - {"C"})
    work = df.dropna(subset=[column for column in required if column in df.columns]).copy()
    if len(work) < 50:
        return {
            "model": model_name,
            "outcome": outcome,
            "n": int(len(work)),
            "error": "insufficient rows",
        }
    try:
        fit = smf.glm(formula, data=work, family=sm.families.Poisson()).fit()
        dispersion = float(fit.pearson_chi2 / fit.df_resid) if fit.df_resid else np.nan
        return {
            "model": model_name,
            "outcome": outcome,
            "n": int(fit.nobs),
            "df_resid": float(fit.df_resid),
            "pearson_chi2": float(fit.pearson_chi2),
            "pearson_chi2_df": dispersion,
            "overdispersed_flag": bool(dispersion > 2),
        }
    except Exception as exc:
        return {
            "model": model_name,
            "outcome": outcome,
            "n": int(len(work)),
            "error": repr(exc),
        }


def _safe_topic_job_interaction(
    df: pd.DataFrame,
    *,
    min_cell_n: int = 30,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    required = {"log_reach", "TopContentCluster", "JobCategory"}
    if not required.issubset(df.columns):
        return {}, pd.DataFrame(), pd.DataFrame()

    work = df.copy()
    cell_counts = (
        work.groupby(["TopContentCluster", "JobCategory"], dropna=False)
        .size()
        .rename("cell_n")
        .reset_index()
    )
    work = work.merge(cell_counts, on=["TopContentCluster", "JobCategory"], how="left")
    work = work[work["cell_n"] >= min_cell_n].copy()
    terms = ["C(TopContentCluster) * C(JobCategory)"]
    for term in ["z_CosineSim", "z_WordCount", "HasImage", "z_NumImages", "MatchScore"]:
        if term in work.columns:
            terms.append(term)
    formula = f"log_reach ~ {' + '.join(terms)}"
    required_formula = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula)) - {"C"})
    work = work.dropna(subset=[column for column in required_formula if column in work.columns]).copy()
    diagnostics = {
        "model": "topic_x_jobcategory_safe",
        "outcome": "log_reach",
        "min_cell_n": min_cell_n,
        "n": int(len(work)),
        "cells_used": int(work[["TopContentCluster", "JobCategory"]].drop_duplicates().shape[0]),
    }
    if len(work) < 50 or work["TopContentCluster"].nunique() < 2 or work["JobCategory"].nunique() < 2:
        diagnostics["status"] = "skipped_insufficient_non_sparse_cells"
        return diagnostics, pd.DataFrame(), cell_counts

    try:
        model = smf.ols(formula, data=work)
        x = model.exog
        rank = int(np.linalg.matrix_rank(x))
        condition_number = float(np.linalg.cond(x))
        diagnostics.update(
            {
                "design_columns": int(x.shape[1]),
                "design_rank": rank,
                "condition_number": condition_number,
            }
        )
        if rank < x.shape[1] or condition_number > 1e12:
            diagnostics["status"] = "skipped_rank_deficient"
            return diagnostics, pd.DataFrame(), cell_counts
        fit = model.fit(cov_type="HC3")
        summary, coeff = _model_records(fit, "topic_x_jobcategory_safe", "log_reach", "ols")
        summary.update(diagnostics)
        summary["status"] = "fit"
        return summary, coeff, cell_counts
    except Exception as exc:
        diagnostics["status"] = "error"
        diagnostics["error"] = repr(exc)
        return diagnostics, pd.DataFrame(), cell_counts


def run_regressions(master: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df, topic_terms = _regression_data(master)
    for column in ["JobCategory", "TopContentCluster", "ProfessionContentMatch"]:
        if column in df.columns:
            df[column] = df[column].astype(str)

    base_terms = [term for term in topic_terms if term in df.columns]
    for term in ["z_CosineSim", "z_WordCount", "HasImage", "z_NumImages"]:
        if term in df.columns:
            base_terms.append(term)
    role_terms = [*base_terms]
    if "JobCategory" in df.columns:
        role_terms.append("C(JobCategory)")
    matchscore_terms = [*role_terms, "MatchScore"] if "MatchScore" in df.columns else [*role_terms]
    profession_match_terms = (
        [*role_terms, "C(ProfessionContentMatch)"] if "ProfessionContentMatch" in df.columns else [*role_terms]
    )

    mechanism_terms = [*matchscore_terms]
    if {"MatchScore", "z_agent_deg_centrality"}.issubset(df.columns):
        mechanism_terms.extend(["z_agent_deg_centrality", "MatchScore:z_agent_deg_centrality"])

    model_summaries = []
    coeffs = []
    clustered_coeffs = []
    negative_binomial_coeffs = []
    distance_coeffs = []
    overdispersion_rows = []

    ols_outcomes = ["log_reach", "log_duration", "structural_virality_winsorized"]
    for outcome in ols_outcomes:
        if outcome not in df.columns:
            continue
        for name, terms in [
            ("content", base_terms),
            ("matchscore", matchscore_terms),
            ("profession_match", profession_match_terms),
            ("mechanism_interaction", mechanism_terms),
        ]:
            if not terms:
                continue
            formula = f"{outcome} ~ {' + '.join(terms)}"
            result = _fit_formula(
                df,
                formula,
                outcome,
                family="ols",
                model_name=name,
            )
            if result:
                summary, coeff = result
                summary["formula"] = formula
                model_summaries.append(summary)
                if not coeff.empty:
                    coeffs.append(coeff)

            if name in {"matchscore", "profession_match"} and "_agent_key" in df.columns:
                result = _fit_formula(
                    df,
                    formula,
                    outcome,
                    family="ols",
                    model_name=f"{name}_agent_clustered_se",
                    cluster_groups=df["_agent_key"],
                )
                if result:
                    summary, coeff = result
                    summary["formula"] = formula
                    model_summaries.append(summary)
                    if not coeff.empty:
                        clustered_coeffs.append(coeff)

    interaction_summary, interaction_coeff, topic_job_cell_counts = _safe_topic_job_interaction(df)
    interaction_diagnostics = pd.DataFrame([interaction_summary]) if interaction_summary else pd.DataFrame()
    if interaction_summary:
        model_summaries.append(interaction_summary)
    if not interaction_coeff.empty:
        coeffs.append(interaction_coeff)

    if "any_reshare" in df.columns:
        for spec_name, terms in [("matchscore", matchscore_terms), ("profession_match", profession_match_terms)]:
            if not terms:
                continue
            formula = f"any_reshare ~ {' + '.join(terms)}"
            for model_name, cluster_groups in [
                (f"{spec_name}_logistic", None),
                (
                    f"{spec_name}_logistic_agent_clustered_se",
                    df["_agent_key"] if "_agent_key" in df.columns else None,
                ),
            ]:
                if model_name.endswith("clustered_se") and cluster_groups is None:
                    continue
                result = _fit_formula(
                    df,
                    formula,
                    "any_reshare",
                    family="binomial",
                    model_name=model_name,
                    cluster_groups=cluster_groups,
                )
                if result:
                    summary, coeff = result
                    summary["formula"] = formula
                    model_summaries.append(summary)
                    if not coeff.empty:
                        if cluster_groups is None:
                            coeffs.append(coeff)
                        else:
                            clustered_coeffs.append(coeff)

    for outcome in ["cascade_size", "second_layer_width"]:
        if outcome in df.columns and matchscore_terms:
            formula = f"{outcome} ~ {' + '.join(matchscore_terms)}"
            overdispersion_rows.append(
                _overdispersion_diagnostic(df, formula, outcome, "matchscore_poisson_robustness")
            )
            for family, model_name in [
                ("poisson", "matchscore_poisson_robustness"),
                ("negative_binomial", "matchscore_negative_binomial"),
            ]:
                result = _fit_formula(
                    df,
                    formula,
                    outcome,
                    family=family,
                    model_name=model_name,
                )
                if result:
                    summary, coeff = result
                    summary["formula"] = formula
                    model_summaries.append(summary)
                    if not coeff.empty:
                        if family == "negative_binomial":
                            negative_binomial_coeffs.append(coeff)
                        else:
                            coeffs.append(coeff)

    distance_outcomes = ["log_reach", "log_duration", "structural_virality_winsorized", "any_reshare"]
    for distance_term in ["z_EuclideanDist", "z_ManhattanDist"]:
        if distance_term not in df.columns:
            continue
        distance_terms = [term for term in matchscore_terms if term != "z_CosineSim"]
        if distance_term not in distance_terms:
            distance_terms.insert(0, distance_term)
        if not distance_terms:
            continue
        for outcome in distance_outcomes:
            if outcome not in df.columns:
                continue
            family = "binomial" if outcome == "any_reshare" else "ols"
            result = _fit_formula(
                df,
                f"{outcome} ~ {' + '.join(distance_terms)}",
                outcome,
                family=family,
                model_name=f"{distance_term.replace('z_', '')}_robustness",
            )
            if result:
                summary, coeff = result
                summary["formula"] = f"{outcome} ~ {' + '.join(distance_terms)}"
                model_summaries.append(summary)
                if not coeff.empty:
                    distance_coeffs.append(coeff)

    coefficients = pd.concat(coeffs, ignore_index=True) if coeffs else pd.DataFrame()
    clustered = pd.concat(clustered_coeffs, ignore_index=True) if clustered_coeffs else pd.DataFrame()
    negative_binomial = (
        pd.concat(negative_binomial_coeffs, ignore_index=True) if negative_binomial_coeffs else pd.DataFrame()
    )
    distance_robustness = pd.concat(distance_coeffs, ignore_index=True) if distance_coeffs else pd.DataFrame()
    overdispersion = pd.DataFrame(overdispersion_rows)
    summaries = pd.DataFrame(model_summaries)

    if not coefficients.empty:
        key_terms = coefficients[
            coefficients["term"].isin(
                [
                    "MatchScore",
                    "C(ProfessionContentMatch)[T.1]",
                    "z_CosineSim",
                    "z_WordCount",
                    "HasImage",
                    "z_NumImages",
                    "z_agent_deg_centrality",
                    "MatchScore:z_agent_deg_centrality",
                ]
            )
        ].copy()
        key_terms["direction"] = np.sign(key_terms["coef"]).map({-1.0: "negative", 0.0: "zero", 1.0: "positive"})
        direction = (
            key_terms.groupby(["term", "outcome", "family", "direction"])
            .size()
            .reset_index(name="models_n")
            .sort_values(["term", "outcome", "models_n"], ascending=[True, True, False])
        )
    else:
        direction = pd.DataFrame()

    return {
        "model_summary": summaries,
        "coefficients": coefficients,
        "clustered_se_coefficients": clustered,
        "negative_binomial_coefficients": negative_binomial,
        "distance_robustness_coefficients": distance_robustness,
        "overdispersion_diagnostics": overdispersion,
        "interaction_diagnostics": interaction_diagnostics,
        "topic_job_cell_counts": topic_job_cell_counts,
        "direction_stability": direction,
    }


def _concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat([frame for frame in frames if frame is not None and not frame.empty], ignore_index=True) if frames else pd.DataFrame()


def _condition_diagnostic(df: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
    available = [column for column in columns if column in df.columns]
    work = df[available].apply(pd.to_numeric, errors="coerce").dropna()
    if len(work) < 3 or len(available) < 2:
        return pd.DataFrame([{"diagnostic": label, "n": int(len(work)), "status": "insufficient_data"}])
    corr = work.corr()
    return pd.DataFrame(
        [
            {
                "diagnostic": label,
                "n": int(len(work)),
                "columns": ", ".join(available),
                "condition_number": float(np.linalg.cond(work.to_numpy())),
                "max_abs_correlation": float(corr.where(~np.eye(len(corr), dtype=bool)).abs().max().max()),
                "status": "computed",
            }
        ]
    )


def _add_topic_pca_columns(
    df: pd.DataFrame,
    topic_cols: list[str],
    *,
    max_components: int = 3,
) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    available = [column for column in topic_cols if column in df.columns]
    if len(available) < 2:
        return df.copy(), [], pd.DataFrame()
    out = df.copy()
    matrix = out[available].apply(pd.to_numeric, errors="coerce")
    std = matrix.std(skipna=True).replace(0, np.nan)
    standardized = (matrix - matrix.mean(skipna=True)) / std
    standardized = standardized.fillna(0)
    if len(standardized) < 3:
        return out, [], pd.DataFrame()
    _, singular_values, vt = np.linalg.svd(standardized.to_numpy(), full_matrices=False)
    components_n = min(max_components, vt.shape[0], len(available))
    if components_n < 1:
        return out, [], pd.DataFrame()
    scores = standardized.to_numpy() @ vt[:components_n].T
    pc_cols = []
    for index in range(components_n):
        column = f"z_topic_pc{index + 1}"
        score = pd.Series(scores[:, index], index=out.index)
        score_std = score.std(skipna=True)
        out[column] = (score - score.mean(skipna=True)) / score_std if score_std and not pd.isna(score_std) else score
        pc_cols.append(column)
    variance = singular_values**2
    total = variance.sum()
    pca_summary = pd.DataFrame(
        [
            {
                "component": column,
                "explained_variance_ratio": float(variance[index] / total) if total else np.nan,
                "topic_score_columns": ", ".join(available),
            }
            for index, column in enumerate(pc_cols)
        ]
    )
    return out, pc_cols, pca_summary


def run_level1_content_analysis(master: pd.DataFrame) -> dict[str, pd.DataFrame]:
    topic_cols = _topic_score_columns(master)
    df = _standardize_for_regression(
        master.copy(),
        ["CosineSim", "WordCount", "NumImages", "EuclideanDist", "ManhattanDist", *topic_cols],
    )
    if "TopContentCluster" in df.columns:
        df["TopContentCluster"] = df["TopContentCluster"].astype(str)
    summaries: list[dict] = []
    coeffs: list[pd.DataFrame] = []
    topic_robust_summaries: list[dict] = []
    topic_robust_coeffs: list[pd.DataFrame] = []
    distance_summaries: list[dict] = []
    distance_coeffs: list[pd.DataFrame] = []
    clustered_summaries: list[dict] = []
    clustered_coeffs: list[pd.DataFrame] = []
    base_terms = [
        term
        for term in ["C(TopContentCluster)", "z_CosineSim", "z_WordCount", "HasImage", "z_NumImages"]
        if term.startswith("C(") or term in df.columns
    ]
    outcome_specs = [
        ("log_reach", "ols"),
        ("log_duration", "ols"),
        ("structural_virality_winsorized", "ols"),
        ("any_reshare", "binomial"),
        ("cascade_size", "negative_binomial"),
        ("second_layer_width", "negative_binomial"),
    ]
    for outcome, family in outcome_specs:
        if outcome not in df.columns:
            continue
        result = _fit_formula(
            df,
            f"{outcome} ~ {' + '.join(base_terms)}",
            outcome,
            family=family,
            model_name="level1_content_main",
        )
        if result:
            summary, coeff = result
            summary["formula"] = f"{outcome} ~ {' + '.join(base_terms)}"
            summaries.append(summary)
            coeffs.append(coeff)
        formula = f"{outcome} ~ {' + '.join(base_terms)}"
        for cluster_column, model_suffix in [
            ("agent_name", "agent_clustered_se"),
            ("article_title", "article_clustered_se"),
        ]:
            if cluster_column not in df.columns or df[cluster_column].nunique(dropna=True) < 2:
                continue
            clustered_result = _fit_formula(
                df,
                formula,
                outcome,
                family=family,
                model_name=f"level1_content_main_{model_suffix}",
                cluster_groups=df[cluster_column].map(normalize_text),
            )
            if clustered_result:
                summary, coeff = clustered_result
                summary["formula"] = formula
                summaries.append(summary)
                clustered_summaries.append(summary)
                if not coeff.empty:
                    clustered_coeffs.append(coeff)

    reference_topic = "topic_home_design_decoration" if "topic_home_design_decoration" in topic_cols else topic_cols[0] if topic_cols else None
    score_terms = [f"z_{column}" for column in topic_cols if column != reference_topic and f"z_{column}" in df.columns]
    score_controls = [term for term in ["z_CosineSim", "z_WordCount", "HasImage", "z_NumImages"] if term in df.columns]
    if score_terms:
        terms = [*score_terms, *score_controls]
        for outcome, family in outcome_specs:
            if outcome not in df.columns:
                continue
            formula = f"{outcome} ~ {' + '.join(terms)}"
            result = _fit_formula(
                df,
                formula,
                outcome,
                family=family,
                model_name="level1_topic_score_robustness",
            )
            if result:
                summary, coeff = result
                summary["formula"] = formula
                summaries.append(summary)
                coeffs.append(coeff)
                topic_robust_summaries.append(summary)
                topic_robust_coeffs.append(coeff)

    df_pca, pc_cols, pca_summary = _add_topic_pca_columns(df, topic_cols)
    if pc_cols:
        pca_terms = [*pc_cols, *score_controls]
        for outcome, family in outcome_specs:
            if outcome not in df_pca.columns:
                continue
            formula = f"{outcome} ~ {' + '.join(pca_terms)}"
            result = _fit_formula(
                df_pca,
                formula,
                outcome,
                family=family,
                model_name="level1_topic_pca_robustness",
            )
            if result:
                summary, coeff = result
                summary["formula"] = formula
                summaries.append(summary)
                coeffs.append(coeff)
                topic_robust_summaries.append(summary)
                topic_robust_coeffs.append(coeff)

    for distance_column, model_name in [
        ("EuclideanDist", "level1_distance_robustness_euclidean"),
        ("ManhattanDist", "level1_distance_robustness_manhattan"),
    ]:
        distance_term = f"z_{distance_column}"
        if distance_term not in df.columns:
            continue
        terms = [
            term
            for term in ["C(TopContentCluster)", distance_term, "z_WordCount", "HasImage", "z_NumImages"]
            if term.startswith("C(") or term in df.columns
        ]
        for outcome, family in outcome_specs:
            if outcome not in df.columns:
                continue
            formula = f"{outcome} ~ {' + '.join(terms)}"
            result = _fit_formula(
                df,
                formula,
                outcome,
                family=family,
                model_name=model_name,
            )
            if result:
                summary, coeff = result
                summary["formula"] = formula
                summaries.append(summary)
                coeffs.append(coeff)
                distance_summaries.append(summary)
                distance_coeffs.append(coeff)

    topic_distribution = (
        df.groupby("TopContentCluster", dropna=False)
        .size()
        .rename("article_agent_rows")
        .reset_index()
        if "TopContentCluster" in df.columns
        else pd.DataFrame()
    )
    descriptive = _describe_numeric(df, [column for column in OUTCOME_COLUMNS + ["CosineSim", "WordCount", "NumImages"] if column in df.columns])
    return {
        "descriptive": descriptive,
        "topic_distribution": topic_distribution,
        "model_summary": pd.DataFrame(summaries),
        "coefficients": _concat_frames(coeffs),
        "clustered_se_summary": pd.DataFrame(clustered_summaries),
        "clustered_se_coefficients": _concat_frames(clustered_coeffs),
        "topic_score_robustness_summary": pd.DataFrame(topic_robust_summaries),
        "topic_score_robustness_coefficients": _concat_frames(topic_robust_coeffs),
        "topic_pca_summary": pca_summary,
        "distance_robustness_summary": pd.DataFrame(distance_summaries),
        "distance_robustness_coefficients": _concat_frames(distance_coeffs),
        "collinearity_diagnostics": _condition_diagnostic(
            df,
            ["CosineSim", "WordCount", "NumImages", "EuclideanDist", "ManhattanDist"],
            "level1_content_continuous_predictors",
        ),
    }


def run_level2_agent_network_analysis(master: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = _standardize_for_regression(
        master.copy(),
        [
            "log_article_count_per_agent",
            "agent_deg_centrality_mean",
            "avg_out_degree_centrality_mean",
            "repeat_exposure_1st_nodes_pct",
            "repeat_exposure_2nd_nodes_pct",
            "gender_assortativity_mean",
        ],
    )
    for column in ["JobCategory", "agent_gender"]:
        if column in df.columns:
            df[column] = df[column].astype(str)
    summaries: list[dict] = []
    coeffs: list[pd.DataFrame] = []
    core_terms = [term for term in ["C(JobCategory)", "C(agent_gender)", "z_log_article_count_per_agent"] if term.startswith("C(") or term in df.columns]
    core_no_count_terms = [term for term in ["C(JobCategory)", "C(agent_gender)"] if term.startswith("C(") or term in df.columns]
    outcomes = [
        "log_agent_cascade_size_mean",
        "reshare_mean",
        "depth_mean",
        "second_layer_width_avg",
        "structural_virality_mean",
        "duration_mean_of_means",
    ]
    for outcome in outcomes:
        if outcome not in df.columns:
            continue
        result = _fit_formula(df, f"{outcome} ~ {' + '.join(core_terms)}", outcome, family="ols", model_name="level2_core")
        if result:
            summary, coeff = result
            summary["formula"] = f"{outcome} ~ {' + '.join(core_terms)}"
            summaries.append(summary)
            coeffs.append(coeff)

    for outcome in outcomes:
        if outcome not in df.columns or not core_no_count_terms:
            continue
        formula = f"{outcome} ~ {' + '.join(core_no_count_terms)}"
        result = _fit_formula(
            df,
            formula,
            outcome,
            family="ols",
            model_name="level2_core_no_article_count",
        )
        if result:
            summary, coeff = result
            summary["formula"] = formula
            summaries.append(summary)
            coeffs.append(coeff)

    descriptor_blocks = {
        "level2_descriptor_centrality": ["z_agent_deg_centrality_mean", "z_avg_out_degree_centrality_mean"],
        "level2_descriptor_repeat_exposure": ["z_repeat_exposure_1st_nodes_pct", "z_repeat_exposure_2nd_nodes_pct"],
        "level2_descriptor_network_composition": ["z_gender_assortativity_mean"],
    }
    for model_name, block_terms in descriptor_blocks.items():
        terms = [term for term in [*core_terms, *block_terms] if term.startswith("C(") or term in df.columns]
        result = _fit_formula(
            df,
            f"log_agent_cascade_size_mean ~ {' + '.join(terms)}",
            "log_agent_cascade_size_mean",
            family="ols",
            model_name=model_name,
        )
        if result:
            summary, coeff = result
            summary["formula"] = f"log_agent_cascade_size_mean ~ {' + '.join(terms)}"
            summaries.append(summary)
            coeffs.append(coeff)

    return {
        "descriptive": _describe_numeric(df, [column for column in outcomes + ["article_count_per_agent", "log_article_count_per_agent"] if column in df.columns]),
        "jobcategory_distribution": df["JobCategory"].value_counts(dropna=False).rename_axis("JobCategory").reset_index(name="agents_n") if "JobCategory" in df.columns else pd.DataFrame(),
        "model_summary": pd.DataFrame(summaries),
        "coefficients": _concat_frames(coeffs),
        "collinearity_diagnostics": _condition_diagnostic(
            df,
            [
                "log_article_count_per_agent",
                "agent_deg_centrality_mean",
                "avg_out_degree_centrality_mean",
                "repeat_exposure_1st_nodes_pct",
                "repeat_exposure_2nd_nodes_pct",
                "gender_assortativity_mean",
            ],
            "level2_descriptor_variables",
        ),
    }


def _level2_centrality_supported(level2_tables: dict[str, pd.DataFrame], alpha: float = 0.05) -> bool:
    coeff = level2_tables.get("coefficients", pd.DataFrame())
    if coeff.empty or not {"model", "term", "p_value"}.issubset(coeff.columns):
        return False
    rows = coeff[
        coeff["model"].astype(str).eq("level2_descriptor_centrality")
        & coeff["term"].astype(str).isin(["z_agent_deg_centrality_mean", "z_avg_out_degree_centrality_mean"])
    ]
    if rows.empty:
        return False
    return bool(pd.to_numeric(rows["p_value"], errors="coerce").lt(alpha).any())


def run_level3_agent_topic_matching_analysis(
    master: pd.DataFrame,
    *,
    run_moderation: bool = True,
) -> dict[str, pd.DataFrame]:
    df = _standardize_for_regression(
        master.copy(),
        [
            "MatchScore_mean",
            "ProfessionContentMatch_mean",
            "log_agent_topic_article_n",
            "WordCount_mean",
            "HasImage_share",
            "NumImages_mean",
            "CosineSim_mean",
            "agent_deg_centrality_mean",
        ],
    )
    for column in ["TopContentCluster", "JobCategory", "agent_gender"]:
        if column in df.columns:
            df[column] = df[column].astype(str)
    summaries: list[dict] = []
    coeffs: list[pd.DataFrame] = []
    weighted_summaries: list[dict] = []
    weighted_coeffs: list[pd.DataFrame] = []
    sparse_summaries: list[dict] = []
    sparse_coeffs: list[pd.DataFrame] = []
    controls = [
        "C(TopContentCluster)",
        "C(JobCategory)",
        "C(agent_gender)",
        "z_log_agent_topic_article_n",
        "z_WordCount_mean",
        "z_HasImage_share",
        "z_NumImages_mean",
        "z_CosineSim_mean",
    ]
    controls = [term for term in controls if term.startswith("C(") or term in df.columns]
    specs = {
        "level3_model_a_matchscore": ["z_MatchScore_mean", *controls],
        "level3_model_b_profession_match": ["z_ProfessionContentMatch_mean", *controls],
    }
    for model_name, terms in specs.items():
        terms = [term for term in terms if term.startswith("C(") or term in df.columns]
        formula = f"log_agent_topic_cascade_size_mean ~ {' + '.join(terms)}"
        result = _fit_formula(
            df,
            formula,
            "log_agent_topic_cascade_size_mean",
            family="ols",
            model_name=model_name,
        )
        if result:
            summary, coeff = result
            summary["formula"] = formula
            summaries.append(summary)
            coeffs.append(coeff)

        weighted_result = _fit_formula(
            df,
            formula,
            "log_agent_topic_cascade_size_mean",
            family="weighted_ols",
            model_name=f"{model_name}_weighted",
            weights="agent_topic_article_n",
        )
        if weighted_result:
            summary, coeff = weighted_result
            summary["formula"] = formula
            summaries.append(summary)
            coeffs.append(coeff)
            weighted_summaries.append(summary)
            weighted_coeffs.append(coeff)

    for threshold in [10, 30]:
        if "agent_topic_article_n" not in df.columns:
            continue
        sparse_df = df[pd.to_numeric(df["agent_topic_article_n"], errors="coerce").ge(threshold)].copy()
        for model_name, terms in specs.items():
            terms = [term for term in terms if term.startswith("C(") or term in sparse_df.columns]
            formula = f"log_agent_topic_cascade_size_mean ~ {' + '.join(terms)}"
            result = _fit_formula(
                sparse_df,
                formula,
                "log_agent_topic_cascade_size_mean",
                family="ols",
                model_name=f"{model_name}_n_ge_{threshold}",
            )
            if result:
                summary, coeff = result
                summary["formula"] = formula
                summaries.append(summary)
                coeffs.append(coeff)
                sparse_summaries.append(summary)
                sparse_coeffs.append(coeff)

    moderation_terms = [
        "z_MatchScore_mean",
        "z_agent_deg_centrality_mean",
        "z_MatchScore_mean:z_agent_deg_centrality_mean",
        "C(TopContentCluster)",
        "C(JobCategory)",
        "C(agent_gender)",
        "z_log_agent_topic_article_n",
    ]
    moderation_terms = [term for term in moderation_terms if term.startswith("C(") or ":" in term or term in df.columns]
    if run_moderation and "z_MatchScore_mean" in df.columns and "z_agent_deg_centrality_mean" in df.columns:
        formula = f"log_agent_topic_cascade_size_mean ~ {' + '.join(moderation_terms)}"
        result = _fit_formula(
            df,
            formula,
            "log_agent_topic_cascade_size_mean",
            family="ols",
            model_name="level3_matchscore_centrality_moderation",
        )
        if result:
            summary, coeff = result
            summary["formula"] = formula
            summaries.append(summary)
            coeffs.append(coeff)

    sparse = pd.DataFrame(
        [
            {
                "rows": int(len(df)),
                "pairs_n_ge_10": int((pd.to_numeric(df.get("agent_topic_article_n", 0), errors="coerce") >= 10).sum()),
                "pairs_n_ge_30": int((pd.to_numeric(df.get("agent_topic_article_n", 0), errors="coerce") >= 30).sum()),
            }
        ]
    )
    return {
        "descriptive": _describe_numeric(
            df,
            [
                "log_agent_topic_cascade_size_mean",
                "MatchScore_mean",
                "ProfessionContentMatch_mean",
                "agent_topic_article_n",
                "WordCount_mean",
                "HasImage_share",
                "NumImages_mean",
                "CosineSim_mean",
            ],
        ),
        "sparse_cell_diagnostics": sparse,
        "job_topic_opportunity": (
            df.groupby(["JobCategory", "TopContentCluster"], dropna=False)
            .agg(
                cell_n=("agent_topic_article_n", "sum"),
                mean_log_reach=("log_agent_topic_cascade_size_mean", "mean"),
                mean_matchscore=("MatchScore_mean", "mean"),
                mean_profession_match=("ProfessionContentMatch_mean", "mean"),
            )
            .reset_index()
            if {"JobCategory", "TopContentCluster"}.issubset(df.columns)
            else pd.DataFrame()
        ),
        "matching_collinearity_diagnostics": _condition_diagnostic(
            df,
            ["MatchScore_mean", "ProfessionContentMatch_mean"],
            "level3_matching_variables",
        ),
        "model_summary": pd.DataFrame(summaries),
        "coefficients": _concat_frames(coeffs),
        "weighted_regression_summary": pd.DataFrame(weighted_summaries),
        "weighted_regression_coefficients": _concat_frames(weighted_coeffs),
        "sparse_sensitivity_summary": pd.DataFrame(sparse_summaries),
        "sparse_sensitivity_coefficients": _concat_frames(sparse_coeffs),
    }


def _save_current_figure(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path


def create_figures(master: pd.DataFrame, anova_tables: dict[str, pd.DataFrame]) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    paths: list[Path] = []

    available = [column for column in OUTCOME_COLUMNS if column in master.columns]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, column in zip(axes.ravel(), available[:6]):
        sns.histplot(master[column].dropna(), bins=40, kde=False, ax=ax, color="#386fa4")
        ax.set_title(column)
        ax.set_xlabel("")
    for ax in axes.ravel()[len(available[:6]) :]:
        ax.axis("off")
    paths.append(_save_current_figure(FIGURE_DIR / "diffusion_outcome_distributions.png"))

    if "TopContentCluster" in master.columns:
        fig, axes = plt.subplots(2, 2, figsize=(15, 9))
        for ax, outcome in zip(axes.ravel(), PLOT_OUTCOMES):
            if outcome in master.columns:
                sns.boxplot(data=master, x="TopContentCluster", y=outcome, ax=ax, color="#8ecae6")
                ax.tick_params(axis="x", rotation=35)
                ax.set_title(f"Topic x {outcome}")
                ax.set_xlabel("")
        paths.append(_save_current_figure(FIGURE_DIR / "topic_outcome_boxplots.png"))

    if "JobCategory" in master.columns:
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        for ax, outcome in zip(axes.ravel(), PLOT_OUTCOMES):
            if outcome in master.columns:
                sns.boxplot(data=master, x="JobCategory", y=outcome, ax=ax, color="#b7e4c7")
                ax.set_title(f"JobCategory x {outcome}")
                ax.set_xlabel("")
        paths.append(_save_current_figure(FIGURE_DIR / "jobcategory_outcome_boxplots.png"))

    if "CosineSimDecile" in master.columns:
        trend = (
            master.groupby("CosineSimDecile", dropna=True)[[c for c in PLOT_OUTCOMES if c in master.columns]]
            .mean()
            .reset_index()
        )
        long = trend.melt("CosineSimDecile", var_name="outcome", value_name="mean")
        plt.figure(figsize=(11, 6))
        sns.lineplot(data=long, x="CosineSimDecile", y="mean", hue="outcome", marker="o")
        plt.title("CosineSim decile trends")
        paths.append(_save_current_figure(FIGURE_DIR / "cosinesim_decile_trends.png"))

    if "MatchScoreDecile" in master.columns:
        trend = (
            master.groupby("MatchScoreDecile", dropna=True)[[c for c in PLOT_OUTCOMES if c in master.columns]]
            .mean()
            .reset_index()
        )
        long = trend.melt("MatchScoreDecile", var_name="outcome", value_name="mean")
        plt.figure(figsize=(11, 6))
        sns.lineplot(data=long, x="MatchScoreDecile", y="mean", hue="outcome", marker="o")
        plt.title("MatchScore decile trends")
        paths.append(_save_current_figure(FIGURE_DIR / "matchscore_decile_trends.png"))

    anova = anova_tables.get("anova_summary", pd.DataFrame())
    if not anova.empty:
        plot = anova.copy()
        plot["neg_log10_p"] = -np.log10(plot["p_value"].clip(lower=1e-300))
        plt.figure(figsize=(12, 7))
        sns.barplot(data=plot, x="outcome", y="neg_log10_p", hue="group")
        plt.axhline(-math.log10(0.05), color="#d00000", linestyle="--", linewidth=1)
        plt.xticks(rotation=30, ha="right")
        plt.title("ANOVA significance summary")
        paths.append(_save_current_figure(FIGURE_DIR / "anova_tukey_summary.png"))

    if {"MatchScoreDecile", "agent_deg_centrality", "log_reach"}.issubset(master.columns):
        interaction = master.dropna(subset=["agent_deg_centrality", "MatchScoreDecile", "log_reach"]).copy()
        if interaction["agent_deg_centrality"].nunique() > 2:
            interaction["CentralityGroup"] = pd.qcut(
                interaction["agent_deg_centrality"], q=3, labels=["Low", "Medium", "High"], duplicates="drop"
            )
            grouped = (
                interaction.groupby(["MatchScoreDecile", "CentralityGroup"], observed=False)["log_reach"]
                .mean()
                .reset_index()
            )
            plt.figure(figsize=(11, 6))
            sns.lineplot(
                data=grouped,
                x="MatchScoreDecile",
                y="log_reach",
                hue="CentralityGroup",
                marker="o",
            )
            plt.title("Observed MatchScore x agent centrality association")
            paths.append(_save_current_figure(FIGURE_DIR / "matchscore_centrality_interaction.png"))

    if {"JobCategory", "TopContentCluster", "log_reach"}.issubset(master.columns):
        matrix = master.pivot_table(
            index="JobCategory",
            columns="TopContentCluster",
            values="log_reach",
            aggfunc="mean",
        )
        plt.figure(figsize=(12, 6))
        sns.heatmap(matrix, annot=True, fmt=".2f", cmap="YlGnBu", linewidths=0.3)
        plt.title("JobCategory x Topic opportunity matrix (mean log reach)")
        paths.append(_save_current_figure(FIGURE_DIR / "agent_topic_opportunity_heatmap.png"))

    if {"duration_mean_s", "duration_mean_s_winsorized", "structural_virality", "structural_virality_winsorized"}.issubset(
        master.columns
    ):
        compare = master[
            [
                "duration_mean_s",
                "duration_mean_s_winsorized",
                "structural_virality",
                "structural_virality_winsorized",
            ]
        ].melt(var_name="variable", value_name="value")
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=compare, x="variable", y="value", showfliers=False, color="#ffd166")
        plt.xticks(rotation=25, ha="right")
        plt.title("Before/after 99% winsorization comparison")
        paths.append(_save_current_figure(FIGURE_DIR / "winsorization_comparison.png"))

    return paths


def create_level_figures(level1: pd.DataFrame, level2: pd.DataFrame, level3: pd.DataFrame) -> list[Path]:
    paths: list[Path] = []
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    level1_outcomes = [
        column
        for column in [
            "log_reach",
            "depth",
            "reshare_pct",
            "log_duration",
            "structural_virality_winsorized",
            "cascade_size",
        ]
        if column in level1.columns
    ]
    if level1_outcomes:
        fig, axes = plt.subplots(2, 3, figsize=(13, 7))
        for ax, column in zip(axes.ravel(), level1_outcomes[:6]):
            sns.histplot(pd.to_numeric(level1[column], errors="coerce").dropna(), bins=30, ax=ax, color="#5b8def")
            ax.set_title(column)
            ax.set_xlabel("")
        for ax in axes.ravel()[len(level1_outcomes[:6]) :]:
            ax.axis("off")
        paths.append(_save_current_figure(FIGURE_DIR / "level1_content_outcome_distributions.png"))

    regression_summary_terms = [
        column
        for column in ["CosineSim", "WordCount", "HasImage", "NumImages", "EuclideanDist", "ManhattanDist"]
        if column in level1.columns and "log_reach" in level1.columns
    ]
    if regression_summary_terms:
        rows = []
        for column in regression_summary_terms:
            x = pd.to_numeric(level1[column], errors="coerce")
            y = pd.to_numeric(level1["log_reach"], errors="coerce")
            work = pd.DataFrame({"x": x, "y": y}).dropna()
            rows.append(
                {
                    "predictor": column,
                    "association_with_log_reach": work["x"].corr(work["y"]) if len(work) > 2 and work["x"].nunique() > 1 else np.nan,
                }
            )
        plot_df = pd.DataFrame(rows).dropna(subset=["association_with_log_reach"])
        if not plot_df.empty:
            plt.figure(figsize=(9, 4))
            sns.barplot(data=plot_df, x="predictor", y="association_with_log_reach", color="#7fb069")
            plt.axhline(0, color="#333333", linewidth=0.8)
            plt.xticks(rotation=20, ha="right")
            plt.title("Level 1 content predictor associations with log reach")
            paths.append(_save_current_figure(FIGURE_DIR / "level1_content_regression_summary.png"))

    if {"log_reach", "TopContentCluster"}.issubset(level1.columns):
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=level1, x="TopContentCluster", y="log_reach", showfliers=False)
        plt.xticks(rotation=30, ha="right")
        plt.title("Level 1 topic differences in log reach")
        paths.append(_save_current_figure(FIGURE_DIR / "level1_topic_outcome_boxplots.png"))

    if {"CosineSim", "log_reach"}.issubset(level1.columns):
        plot_df = level1.dropna(subset=["CosineSim", "log_reach"]).copy()
        if plot_df["CosineSim"].nunique() > 2:
            plot_df["CosineSimDecile"] = _safe_qcut(plot_df["CosineSim"], 10, "D")
            trend = plot_df.groupby("CosineSimDecile", observed=False)["log_reach"].mean().reset_index()
            plt.figure(figsize=(10, 5))
            sns.lineplot(data=trend, x="CosineSimDecile", y="log_reach", marker="o")
            plt.title("Level 1 CosineSim decile trend")
            paths.append(_save_current_figure(FIGURE_DIR / "level1_cosinesim_decile_trends.png"))

    if {"JobCategory", "log_agent_cascade_size_mean"}.issubset(level2.columns):
        plt.figure(figsize=(8, 4))
        sns.histplot(pd.to_numeric(level2["log_agent_cascade_size_mean"], errors="coerce").dropna(), bins=30, color="#6a8caf")
        plt.title("Level 2 agent performance distribution")
        paths.append(_save_current_figure(FIGURE_DIR / "level2_agent_performance_distribution.png"))

        plt.figure(figsize=(10, 5))
        sns.boxplot(data=level2, x="JobCategory", y="log_agent_cascade_size_mean", showfliers=False)
        plt.title("Level 2 agent performance by JobCategory")
        paths.append(_save_current_figure(FIGURE_DIR / "level2_job_agent_performance.png"))

    network_cols = [
        column
        for column in [
            "agent_deg_centrality_mean",
            "avg_out_degree_centrality_mean",
            "centrality_mean",
            "gender_assortativity_mean",
            "repeat_exposure_1st_nodes_pct",
            "repeat_exposure_2nd_nodes_pct",
            "log_agent_cascade_size_mean",
        ]
        if column in level2.columns
    ]
    if len(network_cols) >= 2:
        corr = level2[network_cols].apply(pd.to_numeric, errors="coerce").corr()
        plt.figure(figsize=(8, 6))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, linewidths=0.3)
        plt.title("Level 2 network metric correlations")
        paths.append(_save_current_figure(FIGURE_DIR / "level2_network_metric_correlations.png"))

    repeat_cols = [
        column
        for column in ["repeat_exposure_1st_nodes_pct", "repeat_exposure_2nd_nodes_pct"]
        if column in level2.columns
    ]
    if repeat_cols:
        plot_df = level2[repeat_cols].apply(pd.to_numeric, errors="coerce").melt(var_name="metric", value_name="value")
        plt.figure(figsize=(8, 4))
        sns.boxplot(data=plot_df, x="metric", y="value", showfliers=False, color="#d6a157")
        plt.xticks(rotation=15, ha="right")
        plt.title("Level 2 repeat exposure patterns")
        paths.append(_save_current_figure(FIGURE_DIR / "level2_repeat_exposure_patterns.png"))

    if {"JobCategory", "TopContentCluster", "log_agent_topic_cascade_size_mean"}.issubset(level3.columns):
        matrix = level3.pivot_table(
            index="JobCategory",
            columns="TopContentCluster",
            values="log_agent_topic_cascade_size_mean",
            aggfunc="mean",
        )
        plt.figure(figsize=(12, 5))
        sns.heatmap(matrix, cmap="viridis", annot=True, fmt=".2f")
        plt.title("Level 3 JobCategory x Topic opportunity matrix")
        paths.append(_save_current_figure(FIGURE_DIR / "level3_job_topic_opportunity_heatmap.png"))

    if {"MatchScore_mean", "log_agent_topic_cascade_size_mean"}.issubset(level3.columns):
        plot_df = level3.dropna(subset=["MatchScore_mean", "log_agent_topic_cascade_size_mean"]).copy()
        if plot_df["MatchScore_mean"].nunique() > 2:
            plot_df["MatchScoreDecile"] = _safe_qcut(plot_df["MatchScore_mean"], 10, "D")
            trend = plot_df.groupby("MatchScoreDecile", observed=False)["log_agent_topic_cascade_size_mean"].mean().reset_index()
            plt.figure(figsize=(10, 5))
            sns.lineplot(data=trend, x="MatchScoreDecile", y="log_agent_topic_cascade_size_mean", marker="o")
            plt.title("Level 3 MatchScore trend")
            paths.append(_save_current_figure(FIGURE_DIR / "level3_agent_topic_matchscore_trends.png"))

    if {"MatchScore_mean", "agent_deg_centrality_mean", "log_agent_topic_cascade_size_mean"}.issubset(level3.columns):
        plot_df = level3.dropna(
            subset=["MatchScore_mean", "agent_deg_centrality_mean", "log_agent_topic_cascade_size_mean"]
        ).copy()
        if plot_df["MatchScore_mean"].nunique() > 2 and plot_df["agent_deg_centrality_mean"].nunique() > 2:
            plot_df["MatchScoreDecile"] = _safe_qcut(plot_df["MatchScore_mean"], 10, "D")
            centrality_codes = pd.qcut(
                pd.to_numeric(plot_df["agent_deg_centrality_mean"], errors="coerce"),
                q=3,
                labels=False,
                duplicates="drop",
            )
            centrality_labels = ["Low", "Medium", "High"]
            plot_df["CentralityGroup"] = centrality_codes.map(
                lambda value: centrality_labels[int(value)] if pd.notna(value) else pd.NA
            )
            grouped = (
                plot_df.dropna(subset=["MatchScoreDecile", "CentralityGroup"])
                .groupby(["MatchScoreDecile", "CentralityGroup"], observed=False)["log_agent_topic_cascade_size_mean"]
                .mean()
                .reset_index()
            )
            if not grouped.empty:
                plt.figure(figsize=(10, 5))
                sns.lineplot(
                    data=grouped,
                    x="MatchScoreDecile",
                    y="log_agent_topic_cascade_size_mean",
                    hue="CentralityGroup",
                    marker="o",
                )
                plt.title("Level 3 MatchScore x centrality moderation")
                paths.append(_save_current_figure(FIGURE_DIR / "level3_matchscore_centrality_moderation.png"))

    if "agent_topic_article_n" in level3.columns:
        plot_df = level3[["agent_topic_article_n"]].copy()
        plot_df["cell_group"] = np.select(
            [
                pd.to_numeric(plot_df["agent_topic_article_n"], errors="coerce").ge(30),
                pd.to_numeric(plot_df["agent_topic_article_n"], errors="coerce").ge(10),
            ],
            ["n >= 30", "10 <= n < 30"],
            default="n < 10",
        )
        counts = plot_df["cell_group"].value_counts().reindex(["n < 10", "10 <= n < 30", "n >= 30"]).fillna(0).reset_index()
        counts.columns = ["cell_group", "agent_topic_pairs"]
        plt.figure(figsize=(7, 4))
        sns.barplot(data=counts, x="cell_group", y="agent_topic_pairs", color="#6c9a8b")
        plt.title("Level 3 sparse-cell diagnostics")
        paths.append(_save_current_figure(FIGURE_DIR / "level3_sparse_cell_diagnostics.png"))
    return paths


def write_findings_summary(
    path: Path,
    *,
    level1: pd.DataFrame,
    level2: pd.DataFrame,
    level3: pd.DataFrame,
    level1_tables: dict[str, pd.DataFrame],
    level2_tables: dict[str, pd.DataFrame],
    level3_tables: dict[str, pd.DataFrame],
) -> None:
    def _top_term(
        tables: dict[str, pd.DataFrame],
        term_hint: str,
        *,
        model_hint: str | None = None,
        exact_term: bool = False,
        alpha: float = 0.05,
    ) -> str:
        coeff = tables.get("coefficients", pd.DataFrame())
        if coeff.empty:
            return "No fitted coefficient available."
        rows = coeff.copy()
        if model_hint and "model" in rows.columns:
            rows = rows[rows["model"].astype(str).eq(model_hint)]
        if exact_term:
            rows = rows[rows["term"].astype(str).eq(term_hint)]
        else:
            rows = rows[rows["term"].astype(str).str.contains(term_hint, regex=False, na=False)]
        if rows.empty:
            return f"No coefficient containing `{term_hint}` was estimated."
        row = rows.sort_values("p_value", na_position="last").iloc[0]
        p_value = pd.to_numeric(row.get("p_value"), errors="coerce")
        beta = row.get("standardized_beta", np.nan)
        beta_text = f", standardized beta={beta:.3f}" if pd.notna(beta) else ""
        signal = f"`{row['term']}` on `{row['outcome']}`: coef={row['coef']:.3f}{beta_text}, p={p_value:.3g}."
        if pd.notna(p_value) and p_value >= alpha:
            return f"No coefficient in this block is below p<{alpha:g}; strongest observed term is {signal}"
        return signal

    def _model_count(tables: dict[str, pd.DataFrame], model_name: str) -> int:
        summary = tables.get("model_summary", pd.DataFrame())
        if summary.empty or "model" not in summary.columns:
            return 0
        return int(summary["model"].astype(str).eq(model_name).sum())

    def _model_n(tables: dict[str, pd.DataFrame], model_name: str) -> str:
        summary = tables.get("model_summary", pd.DataFrame())
        if summary.empty or "model" not in summary.columns or "n" not in summary.columns:
            return "not reported"
        rows = summary[summary["model"].astype(str).eq(model_name)]
        if rows.empty:
            return "not reported"
        n_values = sorted(pd.to_numeric(rows["n"], errors="coerce").dropna().astype(int).unique().tolist())
        if not n_values:
            return "not reported"
        if len(n_values) == 1:
            return f"{n_values[0]:,}"
        return f"{min(n_values):,}-{max(n_values):,}"

    def _coefficient_value(
        tables: dict[str, pd.DataFrame],
        term: str,
        *,
        model_hint: str | None = None,
    ) -> float | None:
        coeff = tables.get("coefficients", pd.DataFrame())
        if coeff.empty:
            return None
        rows = coeff.copy()
        if model_hint and "model" in rows.columns:
            rows = rows[rows["model"].astype(str).eq(model_hint)]
        rows = rows[rows["term"].astype(str).eq(term)]
        if rows.empty:
            return None
        value = pd.to_numeric(rows.sort_values("p_value", na_position="last").iloc[0].get("coef"), errors="coerce")
        return float(value) if pd.notna(value) else None

    sparse = level3_tables.get("sparse_cell_diagnostics", pd.DataFrame())
    if sparse.empty:
        sparse_text = "Sparse-cell diagnostics were not available."
    else:
        row = sparse.iloc[0]
        sparse_text = (
            f"{int(row['pairs_n_ge_10'])} of {int(row['rows'])} agent-topic pairs have n>=10; "
            f"{int(row['pairs_n_ge_30'])} have n>=30."
        )
    moderation_coef = _coefficient_value(
        level3_tables,
        "z_MatchScore_mean:z_agent_deg_centrality_mean",
        model_hint="level3_matchscore_centrality_moderation",
    )
    if moderation_coef is None:
        moderation_interpretation = "The moderation model was not estimated or did not return the interaction coefficient."
    elif moderation_coef < 0:
        moderation_interpretation = (
            "In the current run the moderation coefficient is negative, which means the matching-diffusion association is weaker "
            "among agents with higher reconstructed centrality and stronger among agents with lower reconstructed centrality."
        )
    else:
        moderation_interpretation = (
            "In the current run the moderation coefficient is non-negative, which means higher reconstructed centrality does not reduce the observed association between matching and diffusion."
        )

    text = f"""# Stage 4 Findings Summary

Generated: {datetime.now().isoformat(timespec="seconds")}

## Research question

Stage 4 answers two linked questions. First, do content factors, agent characteristics, and content-agent matching factors relate to diffusion performance? Second, if they do, which specific factors matter most after keeping the three analytical levels separate?

The empirical logic is deliberately sequential. Level 1 asks whether the article itself matters. Level 2 asks whether agent characteristics are associated with observed average diffusion patterns. Level 3 then asks whether the fit between a specific agent and a specific content topic matters after the first two layers are understood. Reconstructed network metrics are treated as diffusion-pattern descriptors, not ordinary ex-ante network predictors. This sequence supports the thesis claim that marketing diffusion is not a one-size-fits-all problem.

## Step-by-step workflow

### Step 1 - Source readiness precheck

What this step does: before any modeling, the pipeline checks whether the required source files exist and whether they contain the keys and variables needed for Stage 4. The checked sources are `diffusion(S3)/final_results.xlsx`, `diffusion(S3)/agent_level_results.xlsx`, `diffusion(S3)/agent_topic_level_results.xlsx`, `diffusion(S3)/diffusion_corrected_layers.xlsx`, `batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx`, `batch_outputs(S2)/filtered_results_all_cleaned.xlsx`, `diffusion(S3)/unique_agentsgender.xlsx`, and `diffusion(S3)/agent_dep_job.csv`.

Why this step matters: Stage 4 combines outputs from S2 and S3. If titles, agent names, topic labels, or diffusion metrics are missing or duplicated, the later regressions may look clean but be built on broken joins. This precheck forces the analysis to report missingness, duplicate keys, role/category conflicts, and topic-label standardization issues before results are interpreted.

Output: `analysis(S4)/tables/source_readiness_report.xlsx`.

How to read the output: use this file as a data audit trail. A source file should have the expected row count, required keys, and required outcome inputs. Warnings in this report should be described as data limitations, not hidden.

### Step 2 - Build separate level-specific master files

What this step does: Stage 4 creates three separate master files rather than one mixed `analysis_master.xlsx`.

- Level 1 content master: {len(level1):,} article-agent diffusion cases. Data used: `final_results.xlsx`, S2 content features, S2 article metadata, and corrected diffusion layers. Primary DV: `log_reach = log1p(cascade_size)`, with duration, reshare, depth, and virality outcomes used as additional outcomes.
- Level 2 agent-characteristic master: {len(level2):,} agents. Data used: `agent_level_results.xlsx`, existing S3 `JobCategory`, prepared gender, job, and department attributes. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`.
- Level 3 agent-topic matching master: {len(level3):,} agent-topic rows. Data used: `agent_topic_level_results.xlsx`, article-agent matching scores from `final_results.xlsx`, S2 content controls, and agent attributes. Primary DV: `log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)`.

Why this step matters: each analytical level has a different unit of observation. Level 1 is article-agent, Level 2 is agent, and Level 3 is agent-topic. Mixing them into one table would blur the meaning of a coefficient and increase leakage risk.

Output: `analysis(S4)/level1_content_master.xlsx`, `analysis(S4)/level2_agent_network_master.xlsx`, and `analysis(S4)/level3_agent_topic_match_master.xlsx`.

How to read the output: each master file should be interpreted only at its own level. A Level 1 row is not directly comparable with a Level 2 row, because the dependent variable and unit of analysis are different.

### Step 3 - Standardize topic labels

What this step does: topic labels from Stage 2 and Stage 3 are converted into the English canonical labels used throughout Stage 4: `Home Design & Decoration`, `Real Estate & Architecture`, `Events & Promotions`, `Brand & Marketing`, `Lifestyle & Culture`, and `Customer Service & Management`.

Why this step matters: some source files store Chinese topic labels and some store English translated topic labels. If the labels are not standardized before joining and modeling, the same topic can be treated as two different categories.

Output: `analysis(S4)/tables/topic_label_mapping_report.xlsx` and the topic-label sheets inside `analysis(S4)/tables/join_quality_report.xlsx`.

How to read the output: unmapped labels or mixed-language labels should be treated as data-cleaning problems. In the current Stage 4 outputs, modeling columns use English canonical topic labels.

### Step 4 - Assign variable roles before modeling

What this step does: every major variable is assigned a role such as outcome, content predictor, agent attribute predictor, matching predictor, diffusion-pattern descriptor, control, or validation-only field.

Why this step matters: diffusion-derived variables can be tempting to use as predictors, but many of them are calculated from the same diffusion process as the dependent variables. Treating them as ordinary predictors can create post-treatment leakage. The role map keeps the analysis honest by specifying which variables can be used as predictors, which can be outcomes, and which should only be descriptive or validation fields.

Output: `analysis(S4)/tables/variable_role_map.xlsx`.

How to read the output: this file explains why, for example, `MatchScore_mean` belongs in Level 3 rather than Level 1, and why centrality is interpreted as a diffusion-pattern descriptor rather than a clean causal treatment.

Thesis wording: describe these models as associational. Use words like "is associated with", "is related to", and "is consistent with" rather than causal wording such as "causes" or "affects" unless a causal identification strategy is added.

### Step 5 - Run Level 1 content analysis

What this step does: Level 1 tests whether article content characteristics are associated with diffusion outcomes without adding agent-characteristic or matching variables. Content topic, topic scores, `CosineSim`, `WordCount`, `HasImage`, and `NumImages` are joined by exact article `Title`. Main models use `TopContentCluster` as a categorical predictor and content metadata as controls.

Why this step matters: this is the content-only baseline. It answers whether articles with different content characteristics diffuse differently before asking whether agents or matching explain additional variation.

Output: `analysis(S4)/tables/level1_content_analysis.xlsx` and Level 1 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is {_model_n(level1_tables, "level1_content_main")}. Continuous predictors are standardized, so Standardized beta values can be compared across continuous predictors. Categorical topic coefficients are interpreted relative to the reference topic.

Key model signal: {_top_term(level1_tables, "z_CosineSim", exact_term=True)}

Interpretation: a positive `z_CosineSim` coefficient means title-content semantic consistency is associated with higher diffusion. A negative coefficient would mean semantic distance is associated with weaker diffusion. In thesis wording, this supports the idea that content quality/consistency matters, but it does not by itself prove causality.

Robustness: the pipeline adds {_model_count(level1_tables, "level1_topic_score_robustness")} five-topic-score models, {_model_count(level1_tables, "level1_topic_pca_robustness")} topic-PCA models, and {_model_count(level1_tables, "level1_distance_robustness_euclidean") + _model_count(level1_tables, "level1_distance_robustness_manhattan")} alternative-distance models.

### Step 6 - Run Level 2 agent-characteristic analysis

What this step does: Level 2 tests whether agent role and agent attributes are associated with average diffusion patterns. The unit is one row per agent. The core model uses `JobCategory`, `agent_gender`, and `log_article_count_per_agent`; additional descriptor blocks examine centrality, repeat exposure, and network composition as reconstructed diffusion-pattern descriptors.

Why this step matters: even good content may diffuse differently depending on who shares it. Level 2 separates agent-characteristic heterogeneity from the content-only story, while treating reconstructed network metrics as descriptions of observed diffusion patterns.

Output: `analysis(S4)/tables/level2_agent_network_analysis.xlsx` and Level 2 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is {_model_n(level2_tables, "level2_core")}. Role/gender coefficients describe group differences in average diffusion capability. Centrality and repeat-exposure results are descriptive diffusion-pattern associations because they are derived from observed network/diffusion structure.

Role/gender model signal: {_top_term(level2_tables, "JobCategory", model_hint="level2_core")}

Interpretation of role category: JobCategory is not statistically significant in the current Level 2 core model, so the thesis should report this as evidence that formal role category alone does not explain average diffusion capability. This is substantively useful because it separates agent labels from diffusion-pattern descriptors such as reconstructed centrality and exposure.

Centrality descriptor signal: {_top_term(level2_tables, "z_agent_deg_centrality_mean", model_hint="level2_descriptor_centrality", exact_term=True)}

Thesis wording: say that agents with stronger observed diffusion tend to occupy more central positions in the reconstructed diffusion network. Centrality should be framed as a diffusion-pattern descriptor, not as a leakage-free causal predictor.

Robustness: the pipeline adds {_model_count(level2_tables, "level2_core_no_article_count")} core models without the article-count control.

### Step 7 - Run Level 3 content-agent matching analysis

What this step does: Level 3 tests whether content-agent fit is associated with diffusion for each agent-topic combination. The unit is one row per agent and English `TopContentCluster`. `MatchScore_mean` and `ProfessionContentMatch_mean` are aggregated from article-agent rows, but they are estimated in separate core models to avoid collinearity and interpretation problems.

Why this step matters: this is the direct empirical test of the "one size does not fit all" thesis. It asks whether the same content category performs differently depending on the agent's topical/job fit. Reconstructed centrality is used only in a supplementary descriptive moderation analysis.

Output: `analysis(S4)/tables/level3_agent_topic_matching_analysis.xlsx` and Level 3 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is {_model_n(level3_tables, "level3_model_a_matchscore")}. `MatchScore_mean` captures continuous content-agent fit. `ProfessionContentMatch_mean` captures the share or intensity of profession-content match. Weighted models use `agent_topic_article_n` as precision/exposure weights, and sparse-cell sensitivity models check whether findings depend on very small agent-topic cells.

Key continuous matching signal: {_top_term(level3_tables, "z_MatchScore_mean", model_hint="level3_model_a_matchscore", exact_term=True)}

Key binary/proportion matching signal: {_top_term(level3_tables, "z_ProfessionContentMatch_mean", model_hint="level3_model_b_profession_match", exact_term=True)}

Moderation signal: {_top_term(level3_tables, "z_MatchScore_mean:z_agent_deg_centrality_mean", model_hint="level3_matchscore_centrality_moderation", exact_term=True)}

Interpretation: a positive matching coefficient means better content-agent fit is associated with stronger diffusion for that agent-topic combination. The moderation model asks whether the matching-diffusion association differs across reconstructed centrality levels; it is reported as supplementary descriptive heterogeneity rather than as a causal moderation test. {moderation_interpretation}

Sparse-cell note: {sparse_text}

Thesis wording: this level supports the managerial implication that personalized content assignment may matter. The centrality moderation result should be discussed only as descriptive heterogeneity across reconstructed diffusion-position groups.

### Step 8 - Generate tables, figures, validation files, and notebook

What this step does: after the three models are built, the pipeline writes master files, Excel model tables, join-quality reports, validation JSON, figures, this findings summary, and a notebook for inspection.

Why this step matters: the outputs are designed to make the analysis reproducible and readable. The Excel files preserve model details; the figures provide thesis-facing visual summaries; the notebook offers a quick way to reload and inspect results.

Output: `analysis(S4)/tables/*.xlsx`, `analysis(S4)/figures/*.png`, `analysis(S4)/tables/three_level_validation_report.json`, `analysis(S4)/Stage4_Findings_Summary.md`, and `analysis(S4)/factor_analysis_stage4.ipynb`.

How to read the output: start with this findings file, then inspect the three level-specific Excel analysis files for exact coefficients, sample sizes, and robustness checks. Use the figures for presentation and thesis narrative, but cite the tables for exact values.

## Data Construction

Stage 4 follows the three-level framework from the interim report. All topic labels are standardized to English canonical labels. `analysis_master.xlsx` is not used. Complete-case model samples may be smaller than master row counts when a model variable is missing; main model n ranges are reported above.

## Leakage control

Diffusion-derived variables are treated as outcomes or diffusion-pattern descriptors, not ordinary leakage-free predictors. Level 1 excludes matching and agent-characteristic variables. Level 2 excludes content-agent matching aggregates. Level 3 uses matching variables plus leakage-safe content/exposure controls, and does not use realized diffusion descriptors as ordinary controls.

## Main interpretation by level

### Level 1 Content

Why calculated: Level 1 tests whether content characteristics are associated with diffusion outcomes without adding matching variables.

Method: content topic, topic scores, `CosineSim`, `WordCount`, `HasImage`, and `NumImages` are joined by exact article `Title`. Main models use `TopContentCluster` as a categorical predictor and content metadata as controls. Controls: `CosineSim`, `WordCount`, `HasImage`, and `NumImages`; alternative distance controls are used only in robustness checks. The six topic-score columns are not entered together with topic dummies in the main model; they are used only in robustness specifications. Main complete-case n: {_model_n(level1_tables, "level1_content_main")}.

Key model signal: {_top_term(level1_tables, "z_CosineSim", exact_term=True)}

Interpretation: a positive `z_CosineSim` coefficient means title-content semantic consistency is associated with higher diffusion; a negative coefficient would indicate that more semantic distance is associated with weaker diffusion. Standardized beta values are used to compare continuous predictors measured on different scales.

### Level 2 Agent Characteristics

Why calculated: Level 2 tests whether agent roles and observable agent characteristics are associated with average diffusion patterns. Reconstructed network metrics describe the resulting diffusion structure rather than ex-ante network causes.

Method: one row per agent. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`. Controls: `JobCategory`, `agent_gender`, and `log_article_count_per_agent` in the core model. `article_count_per_agent` is calculated from `final_results.xlsx` and used as a stability/opportunity control. Main complete-case n: {_model_n(level2_tables, "level2_core")}.

Role/gender model signal: {_top_term(level2_tables, "JobCategory", model_hint="level2_core")}

Centrality descriptor signal: {_top_term(level2_tables, "z_agent_deg_centrality_mean", model_hint="level2_descriptor_centrality", exact_term=True)}

Interpretation: role/gender coefficients describe group differences in average agent diffusion capability, while centrality and repeat-exposure blocks describe diffusion-pattern associations. They are not interpreted as causal effects because they are derived from observed diffusion/network structure.

### Level 3 Content-Agent Matching

Why calculated: Level 3 directly tests the thesis claim that one content strategy does not fit all agents or roles.

Method: one row per agent and English `TopContentCluster`. `MatchScore_mean` and `ProfessionContentMatch_mean` are aggregated from article-agent rows, but they are estimated in separate core models to avoid collinearity and interpretation problems. Controls: `TopContentCluster`, `JobCategory`, `agent_gender`, `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, and `CosineSim_mean`. Main complete-case n: {_model_n(level3_tables, "level3_model_a_matchscore")}.

Key continuous matching signal: {_top_term(level3_tables, "z_MatchScore_mean", model_hint="level3_model_a_matchscore", exact_term=True)}

Key binary/proportion matching signal: {_top_term(level3_tables, "z_ProfessionContentMatch_mean", model_hint="level3_model_b_profession_match", exact_term=True)}

Moderation signal: {_top_term(level3_tables, "z_MatchScore_mean:z_agent_deg_centrality_mean", model_hint="level3_matchscore_centrality_moderation", exact_term=True)}

Interpretation: a positive matching coefficient means better content-agent fit is associated with stronger diffusion for that agent-topic combination. {moderation_interpretation}

## Limitations

The analysis is explanatory and associational. Standardized beta is useful for comparing continuous predictors, but categorical coefficients should be interpreted relative to their reference groups. Diffusion-derived descriptors are treated as outcomes or diffusion-pattern descriptors, not leakage-free causal predictors. Sparse-cell Level 3 evidence should be interpreted cautiously, especially for individual agent-topic pairs.
"""
    path.write_text(text, encoding="utf-8")


def write_notebook(path: Path) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            "# Stage 4 Three-Level Analysis\n\n"
            "This notebook regenerates Level 1 content, Level 2 agent-characteristic, and Level 3 agent-topic matching outputs."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import sys\n"
            "import pandas as pd\n"
            "\n"
            "NOTEBOOK_DIR = Path.cwd()\n"
            "if not (NOTEBOOK_DIR / 'stage4_pipeline.py').exists():\n"
            "    NOTEBOOK_DIR = (Path.cwd() / 'analysis(S4)').resolve()\n"
            "sys.path.insert(0, str(NOTEBOOK_DIR))\n"
            "\n"
            "from stage4_pipeline import main\n\n"
            "results = main(regenerate_notebook=False)\n"
            "results"
        ),
        nbf.v4.new_code_cell(
            "df_level1 = pd.read_excel(NOTEBOOK_DIR / 'level1_content_master.xlsx')\n"
            "df_level2 = pd.read_excel(NOTEBOOK_DIR / 'level2_agent_network_master.xlsx')\n"
            "df_level3 = pd.read_excel(NOTEBOOK_DIR / 'level3_agent_topic_match_master.xlsx')\n"
            "df_level1.head()"
        ),
        nbf.v4.new_code_cell(
            "level1_regression_results = pd.read_excel(NOTEBOOK_DIR / 'tables' / 'level1_content_analysis.xlsx', sheet_name='coefficients')\n"
            "level3_regression_results = pd.read_excel(NOTEBOOK_DIR / 'tables' / 'level3_agent_topic_matching_analysis.xlsx', sheet_name='model_summary')\n"
            "level1_sheets = pd.ExcelFile(NOTEBOOK_DIR / 'tables' / 'level1_content_analysis.xlsx').sheet_names\n"
            "level3_sheets = pd.ExcelFile(NOTEBOOK_DIR / 'tables' / 'level3_agent_topic_matching_analysis.xlsx').sheet_names\n"
            "assert len(df_level1) == 6557\n"
            "assert 'MatchScore' not in df_level1.columns\n"
            "assert 'ProfessionContentMatch' not in df_level1.columns\n"
            "assert not any(str(c).endswith('_content') for c in df_level1.columns)\n"
            "assert not any('(Content)' in str(c) or '(Title+Content)' in str(c) for c in df_level1.columns)\n"
            "assert df_level2['agent_name'].nunique() == 592\n"
            "assert 'matchscore_mean' not in df_level2.columns\n"
            "assert 'profession_content_match_mean' not in df_level2.columns\n"
            "assert df_level3[['agent_name', 'TopContentCluster']].duplicated().sum() == 0\n"
            "assert 'standardized_beta' in level1_regression_results.columns\n"
            "assert 'topic_score_robustness_summary' in level1_sheets\n"
            "assert 'weighted_regression_summary' in level3_sheets\n"
            "assert 'MatchScore_mean + ProfessionContentMatch_mean' not in ' '.join(level3_regression_results['formula'].dropna().astype(str))\n"
            "print('All Stage 4 validation checks passed.')"
        ),
        nbf.v4.new_markdown_cell(
            "Generated outputs are under `analysis(S4)/tables` and `analysis(S4)/figures`."
        ),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)


def main(*, regenerate_notebook: bool = True) -> Stage4Results:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_legacy_outputs(OUT_DIR)

    inputs = load_inputs()
    source_readiness_path = TABLE_DIR / "source_readiness_report.xlsx"
    source_readiness_tables = check_source_readiness(inputs, raise_on_error=True)
    write_excel_tables(source_readiness_path, source_readiness_tables)

    level1 = build_level1_content_master(
        final=inputs["final"],
        corrected=inputs["corrected"],
        content=inputs["content"],
        article_meta=inputs["article_meta"],
    )
    level2 = build_level2_agent_network_master(
        agent_level=inputs["agent_level"],
        final=inputs["final"],
        agent_gender=inputs["agent_gender"],
        agent_dep_job=inputs["agent_dep_job"],
    )
    level3 = build_level3_agent_topic_match_master(
        agent_topic=inputs["agent_topic"],
        final=inputs["final"],
        content=inputs["content"],
        article_meta=inputs["article_meta"],
        agent_gender=inputs["agent_gender"],
        agent_dep_job=inputs["agent_dep_job"],
    )

    validation = {
        "valid": bool(
            len(level1) == EXPECTED_MASTER_ROWS
            and level2["agent_name"].nunique() == EXPECTED_AGENT_ROWS
            and len(level3) == EXPECTED_AGENT_TOPIC_ROWS
            and not (OUT_DIR / "analysis_master.xlsx").exists()
        ),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "checks": {
            "level1_rows": {"actual": int(len(level1)), "expected": EXPECTED_MASTER_ROWS},
            "level2_agents": {"actual": int(level2["agent_name"].nunique()), "expected": EXPECTED_AGENT_ROWS},
            "level3_rows": {"actual": int(len(level3)), "expected": EXPECTED_AGENT_TOPIC_ROWS},
            "analysis_master_removed": {"passed": not (OUT_DIR / "analysis_master.xlsx").exists()},
        },
    }

    level1_master_path = OUT_DIR / "level1_content_master.xlsx"
    level2_master_path = OUT_DIR / "level2_agent_network_master.xlsx"
    level3_master_path = OUT_DIR / "level3_agent_topic_match_master.xlsx"
    level1.to_excel(level1_master_path, index=False)
    level2.to_excel(level2_master_path, index=False)
    level3.to_excel(level3_master_path, index=False)

    validation_path = TABLE_DIR / "three_level_validation_report.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    role_map = write_variable_role_map()
    variable_role_map_path = TABLE_DIR / "variable_role_map.xlsx"
    role_map.to_excel(variable_role_map_path, index=False)

    level1_tables = run_level1_content_analysis(level1)
    level2_tables = run_level2_agent_network_analysis(level2)
    level3_tables = run_level3_agent_topic_matching_analysis(
        level3,
        run_moderation=_level2_centrality_supported(level2_tables),
    )

    level1_analysis_path = TABLE_DIR / "level1_content_analysis.xlsx"
    level2_analysis_path = TABLE_DIR / "level2_agent_network_analysis.xlsx"
    level3_analysis_path = TABLE_DIR / "level3_agent_topic_matching_analysis.xlsx"
    write_excel_tables(level1_analysis_path, level1_tables)
    write_excel_tables(level2_analysis_path, level2_tables)
    write_excel_tables(level3_analysis_path, level3_tables)

    join_quality_path = TABLE_DIR / "join_quality_report.xlsx"
    write_excel_tables(join_quality_path, make_join_quality_tables(inputs))

    topic_label_mapping_path = TABLE_DIR / "topic_label_mapping_report.xlsx"
    source_readiness_tables["topic_label_standardization"].to_excel(topic_label_mapping_path, index=False)

    figures = create_level_figures(level1, level2, level3)

    write_findings_summary(
        OUT_DIR / "Stage4_Findings_Summary.md",
        level1=level1,
        level2=level2,
        level3=level3,
        level1_tables=level1_tables,
        level2_tables=level2_tables,
        level3_tables=level3_tables,
    )

    notebook_path = OUT_DIR / "factor_analysis_stage4.ipynb"
    if regenerate_notebook:
        write_notebook(notebook_path)

    return Stage4Results(
        level1_master_path=level1_master_path,
        level2_master_path=level2_master_path,
        level3_master_path=level3_master_path,
        level1_analysis_path=level1_analysis_path,
        level2_analysis_path=level2_analysis_path,
        level3_analysis_path=level3_analysis_path,
        source_readiness_path=source_readiness_path,
        variable_role_map_path=variable_role_map_path,
        join_quality_path=join_quality_path,
        notebook_path=notebook_path,
        validation=validation,
        figures=figures,
    )


if __name__ == "__main__":
    results = main()
    print(json.dumps(
        {
            "level1_master": str(results.level1_master_path),
            "level2_master": str(results.level2_master_path),
            "level3_master": str(results.level3_master_path),
            "level1_analysis": str(results.level1_analysis_path),
            "level2_analysis": str(results.level2_analysis_path),
            "level3_analysis": str(results.level3_analysis_path),
            "source_readiness": str(results.source_readiness_path),
            "variable_role_map": str(results.variable_role_map_path),
            "join_quality": str(results.join_quality_path),
            "notebook": str(results.notebook_path),
            "figures": [str(path) for path in results.figures],
            "validation_valid": results.validation["valid"],
        },
        ensure_ascii=False,
        indent=2,
    ))
