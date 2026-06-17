from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "msc-thesis" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LEVEL2_PATH = ROOT / "analysis(S4)" / "level2_agent_network_master.xlsx"
LEVEL3_PATH = ROOT / "analysis(S4)" / "level3_agent_topic_match_master.xlsx"


OUTCOMES = [
    ("log_agent_cascade_size_mean", "log_agent_topic_cascade_size_mean", "Mean log reach", "reach"),
    ("depth_mean", "depth_mean", "Depth mean", "shape"),
    ("reshare_mean", "reshare_mean", "Reshare mean", "shape"),
    ("second_layer_width_avg", "second_layer_width_avg", "Second-layer width", "shape"),
    ("structural_virality_mean", "structural_virality_mean", "Structural virality", "shape"),
    ("centrality_mean", "centrality_mean", "Graph-level centrality", "centrality"),
    ("agent_deg_centrality_mean", "agent_deg_centrality_mean", "Agent degree centrality", "centrality"),
    ("avg_out_degree_centrality_mean", "avg_out_degree_centrality_mean", "Average out-degree centrality", "centrality"),
]


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    sd = values.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.nan, index=series.index)
    return (values - values.mean()) / sd


def standardize_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[f"z_{column}"] = zscore(out[column])
    return out


def fit_outcome_standardized(
    df: pd.DataFrame,
    outcome: str,
    formula_terms: list[str],
    required_columns: list[str],
    term: str,
) -> dict[str, float]:
    work = df.dropna(subset=[outcome, *required_columns]).copy()
    work["z_outcome"] = zscore(work[outcome])
    fit = smf.ols(f"z_outcome ~ {' + '.join(formula_terms)}", data=work).fit(cov_type="HC3")
    ci_low, ci_high = fit.conf_int().loc[term]
    return {
        "coef": float(fit.params[term]),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "n": float(fit.nobs),
    }


def collect_level2() -> pd.DataFrame:
    df = pd.read_excel(LEVEL2_PATH)
    df = standardize_columns(df, ["log_article_count_per_agent"])
    df["JobCategory"] = df["JobCategory"].astype(str)
    df["agent_gender"] = df["agent_gender"].astype(str)
    df = df[df["JobCategory"].ne("0")].copy()

    formula_terms = [
        "C(JobCategory, Treatment(reference='3'))",
        "C(agent_gender)",
        "z_log_article_count_per_agent",
    ]
    required = ["JobCategory", "agent_gender", "z_log_article_count_per_agent"]
    term = "C(JobCategory, Treatment(reference='3'))[T.1]"
    rows = []
    for level2_outcome, _, label, group in OUTCOMES:
        result = fit_outcome_standardized(df, level2_outcome, formula_terms, required, term)
        rows.append({"panel": "A", "outcome": label, "group": group, **result})
    return pd.DataFrame(rows)


def collect_level3() -> pd.DataFrame:
    df = pd.read_excel(LEVEL3_PATH)
    df = standardize_columns(
        df,
        [
            "MatchScore_mean",
            "log_agent_topic_article_n",
            "WordCount_mean",
            "HasImage_share",
            "NumImages_mean",
            "CosineSim_mean",
        ],
    )
    for column in ["TopContentCluster", "JobCategory", "agent_gender"]:
        df[column] = df[column].astype(str)

    formula_terms = [
        "z_MatchScore_mean",
        "C(TopContentCluster)",
        "C(JobCategory)",
        "C(agent_gender)",
        "z_log_agent_topic_article_n",
        "z_WordCount_mean",
        "z_HasImage_share",
        "z_NumImages_mean",
        "z_CosineSim_mean",
    ]
    required = [
        "z_MatchScore_mean",
        "TopContentCluster",
        "JobCategory",
        "agent_gender",
        "z_log_agent_topic_article_n",
        "z_WordCount_mean",
        "z_HasImage_share",
        "z_NumImages_mean",
        "z_CosineSim_mean",
    ]
    rows = []
    for _, level3_outcome, label, group in OUTCOMES:
        result = fit_outcome_standardized(df, level3_outcome, formula_terms, required, "z_MatchScore_mean")
        rows.append({"panel": "B", "outcome": label, "group": group, **result})
    return pd.DataFrame(rows)


def plot_forest(results: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 150,
        }
    )

    panel_titles = {
        "A": "A. Level 2 role contrast",
        "B": "B. Level 3 fit score",
    }
    colors = {"reach": "#0077BB", "shape": "#009988", "centrality": "#CC3311"}
    markers = {"reach": "o", "shape": "s", "centrality": "^"}

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.8), sharex=True, sharey=True)
    y = np.arange(len(OUTCOMES))[::-1]
    y_labels = [item[2] for item in OUTCOMES]

    x_min = float(results["ci_low"].min())
    x_max = float(results["ci_high"].max())
    pad = (x_max - x_min) * 0.08
    x_limits = (x_min - pad, x_max + pad)

    for ax, panel in zip(axes, ["A", "B"]):
        sub = results[results["panel"].eq(panel)].set_index("outcome").loc[y_labels].reset_index()
        for i, row in sub.iterrows():
            ypos = y[i]
            color = colors[row["group"]]
            ax.errorbar(
                row["coef"],
                ypos,
                xerr=[[row["coef"] - row["ci_low"]], [row["ci_high"] - row["coef"]]],
                fmt=markers[row["group"]],
                color=color,
                ecolor=color,
                elinewidth=1.2,
                capsize=3,
                markersize=4.5,
            )
        ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--")
        ax.axhline(2.5, color="#BBBBBB", linewidth=0.7)
        ax.set_title(panel_titles[panel], loc="left", fontweight="bold", pad=8)
        ax.set_xlim(*x_limits)
        ax.grid(axis="x", color="#E6E6E6", linewidth=0.6)
        ax.set_xlabel("Outcome-standardised coefficient (95% CI)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)

    axes[0].set_yticks(y)
    axes[0].set_yticklabels(y_labels)

    handles = [
        plt.Line2D([0], [0], marker=markers["reach"], color=colors["reach"], linestyle="", label="Reach"),
        plt.Line2D([0], [0], marker=markers["shape"], color=colors["shape"], linestyle="", label="Cascade shape"),
        plt.Line2D([0], [0], marker=markers["centrality"], color=colors["centrality"], linestyle="", label="Centrality"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    out_png = OUT_DIR / "figure_6_1_reach_centrality_forest.png"
    out_pdf = OUT_DIR / "figure_6_1_reach_centrality_forest.pdf"
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    results = pd.concat([collect_level2(), collect_level3()], ignore_index=True)
    results.to_csv(OUT_DIR / "figure_6_1_reach_centrality_forest_data.csv", index=False)
    plot_forest(results)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
