# WeChat Marketing Diffusion Analysis

This repository contains a staged empirical analysis of WeChat article diffusion in a home decoration / real-estate marketing context. The project studies whether diffusion effectiveness is associated with article content, agent/network capability, and content-agent fit.

Core thesis idea:

```text
One Size Does Not Fit All:
marketing diffusion effectiveness depends not only on content,
not only on agent/network capability,
but also on the fit between content and agent-topic context.
```

## Recommended Reading Order For ChatGPT

If using ChatGPT Web or another LLM to understand this project, read files in this order:

1. `README.md` - project map and file guide.
2. `Stage4_Analysis_Plan.md` - detailed Stage 4 empirical design and leakage-control rules.
3. `analysis(S4)/Stage4_Findings_Summary.md` - current final findings and thesis-facing interpretation.
4. `analysis(S4)/stage4_pipeline.py` - reproducible Stage 4 data construction, modeling, tables, figures, and summary generation.
5. `analysis(S4)/factor_analysis_stage4.ipynb` - notebook generated for inspecting Stage 4 outputs.
6. Earlier-stage notebooks only when needed:
   - `wechat(S1)/Wechat analysis (stage 1).ipynb`
   - `LLM final 1(stage 2).ipynb`
   - `diffusion(S3)/diffusion network3 (stage 3).ipynb`

For high-level interpretation, start with the Stage 4 plan and findings summary before reading individual Excel outputs.

## Repository Structure

```text
.
|-- wechat(S1)/                 # Stage 1: WeChat article/source preparation and early analysis
|-- batch_outputs(S2)/          # Stage 2: LLM/topic analysis outputs and clustered article features
|-- diffusion(S3)/              # Stage 3: diffusion/network construction and agent-level outputs
|-- analysis(S4)/               # Stage 4: final three-level empirical analysis
|-- Stage4_Analysis_Plan.md     # Stage 4 research plan, data rules, and modeling framework
|-- LLM final 1(stage 2).ipynb  # Stage 2 LLM/topic workflow notebook
|-- Interim Report.pdf          # Interim report reference
`-- DASE7099 Dissertation Proposal.docx
```

Local-only folders such as `.venv/`, `.uv-cache/`, `.pytest_cache/`, and Jupyter checkpoint folders are intentionally ignored by Git.

## Stage 1: WeChat Data Preparation

Folder: `wechat(S1)/`

Purpose:

- Prepare the initial WeChat article-level data.
- Build early article/title/detail datasets.
- Explore article content and network-related preprocessing.

Key files:

| File | Description |
| --- | --- |
| `wechat(S1)/article.csv` | Article title list used as an early source table. |
| `wechat(S1)/detail.csv` | Article detail/source data from Stage 1 processing. |
| `wechat(S1)/detail_filtered2.xlsx` | Filtered article detail table used by later stages. |
| `wechat(S1)/word_article_title_path.csv` | Title/path mapping output. |
| `wechat(S1)/Wechat analysis (stage 1).ipynb` | Main Stage 1 notebook. |
| `wechat(S1)/code file/*.ipynb` | Supporting notebooks for LDA, clustering, paths, regression, and full network exploration. |

## Stage 2: Topic And Content Feature Analysis

Folder: `batch_outputs(S2)/`

Main notebook: `LLM final 1(stage 2).ipynb`

Purpose:

- Use LLM-assisted processing and topic clustering to classify article content.
- Generate article-level content features for downstream diffusion analysis.
- Produce per-topic and per-cluster analysis files.

Key files:

| File or folder | Description |
| --- | --- |
| `batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx` | Important Stage 2 content table with English translated topic labels; used by Stage 4. |
| `batch_outputs(S2)/filtered_results_all_cleaned.xlsx` | Cleaned article metadata used by Stage 4 for features such as word count and image fields. |
| `batch_outputs(S2)/topic_clusters_gpt4o.xlsx` | GPT-assisted topic cluster output. |
| `batch_outputs(S2)/topic_clusters_raw.txt` | Raw topic-cluster notes/output. |
| `batch_outputs(S2)/cluster analysis/` | Per-article cluster analysis spreadsheets. |
| `batch_outputs(S2)/topic analysis/` | Per-article topic analysis spreadsheets. |

Canonical Stage 4 topic labels are standardized to English:

- `Home Design & Decoration`
- `Real Estate & Architecture`
- `Events & Promotions`
- `Brand & Marketing`
- `Lifestyle & Culture`
- `Customer Service & Management`

## Stage 3: Diffusion And Network Construction

Folder: `diffusion(S3)/`

Purpose:

- Build diffusion cascades from WeChat sharing/reading paths.
- Generate article-agent, agent-level, and agent-topic-level diffusion metrics.
- Prepare agent attributes and diffusion outcome dimensions for Stage 4.

Key files:

| File | Description |
| --- | --- |
| `diffusion(S3)/final_results.xlsx` | Main article-agent diffusion table; 6,557 rows x 29 columns. Used as the core Stage 4 Level 1 and matching source. |
| `diffusion(S3)/agent_level_results.xlsx` | Agent-level diffusion/network table; 592 rows x 27 columns. Used in Stage 4 Level 2. |
| `diffusion(S3)/agent_topic_level_results.xlsx` | Agent-topic diffusion table; 1,142 rows x 26 columns. Used in Stage 4 Level 3. |
| `diffusion(S3)/diffusion_corrected_layers.xlsx` | Corrected diffusion-layer data used to reconstruct cascade outcomes. |
| `diffusion(S3)/unique_agentsgender.xlsx` | Prepared agent gender attribute source. |
| `diffusion(S3)/agent_dep_job.csv` | Agent department/job attribute source. |
| `diffusion(S3)/diffusion network*.ipynb` | Stage 3 diffusion-network notebooks. |
| `diffusion(S3)/*.png` | Network visualization images. |

Important Stage 3 variables include cascade size, depth, first/second-layer width, reshare percentage, structural virality, Wiener index, centrality, match score, profession-content match, job category, and agent attributes.

## Stage 4: Three-Level Empirical Analysis

Folder: `analysis(S4)/`

Purpose:

Stage 4 is the current final analysis layer. It intentionally separates the project into three analytical levels instead of mixing all variables into one oversized master table.

### Level 1: Content

Question: Are content characteristics associated with article-agent diffusion outcomes?

Main file:

- `analysis(S4)/level1_content_master.xlsx` - 6,557 rows x 66 columns.

Inputs:

- `diffusion(S3)/final_results.xlsx`
- `diffusion(S3)/diffusion_corrected_layers.xlsx`
- `batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx`
- `batch_outputs(S2)/filtered_results_all_cleaned.xlsx`

Main outcome:

- `log_reach = log1p(cascade_size)`

Supplementary outcomes:

- article-agent width, depth, reshare, duration, structural virality, and Wiener index

Main predictors/controls:

- `TopContentCluster`
- topic-score columns
- `CosineSim`
- `WordCount`
- `HasImage`
- `NumImages`

### Level 2: Agent / Network

Question: Are agent role and attributes associated with agent-level diffusion outcome dimensions?

Main file:

- `analysis(S4)/level2_agent_network_master.xlsx` - 592 rows x 32 columns.

Inputs:

- `diffusion(S3)/agent_level_results.xlsx`
- `diffusion(S3)/final_results.xlsx`
- `diffusion(S3)/unique_agentsgender.xlsx`
- `diffusion(S3)/agent_dep_job.csv`

Main outcome:

- `log_agent_cascade_size_mean = log1p(cascade_size_mean)`

Supplementary outcomes:

- agent-level mean depth, reshare, structural virality, Wiener index, centrality, repeat exposure, and network-composition measures

Main predictors/controls:

- `JobCategory`
- `agent_gender`
- `log_article_count_per_agent`

### Level 3: Content-Agent Matching

Question: Does content-agent fit explain why one content strategy does not work equally well for all agent-topic combinations?

Main file:

- `analysis(S4)/level3_agent_topic_match_master.xlsx` - 1,142 rows x 45 columns.

Inputs:

- `diffusion(S3)/agent_topic_level_results.xlsx`
- article-agent matching variables from `diffusion(S3)/final_results.xlsx`
- Stage 2 content controls
- agent attributes

Main outcome:

- `log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)`

Supplementary outcomes:

- agent-topic mean depth, reshare, structural virality, Wiener index, centrality, and related cascade-shape outcomes

Main matching predictors:

- `MatchScore_mean`
- `ProfessionContentMatch_mean`

## Stage 4 Outputs

Key generated files:

| File | Description |
| --- | --- |
| `analysis(S4)/Stage4_Findings_Summary.md` | Human-readable summary of data construction, leakage control, models, and findings. |
| `analysis(S4)/stage4_pipeline.py` | Reproducible Python pipeline for Stage 4. |
| `analysis(S4)/factor_analysis_stage4.ipynb` | Generated inspection notebook for Stage 4 results. |
| `analysis(S4)/tables/source_readiness_report.xlsx` | Precheck report for required source files, keys, missingness, and join readiness. |
| `analysis(S4)/tables/join_quality_report.xlsx` | Join quality and topic-label standardization report. |
| `analysis(S4)/tables/variable_role_map.xlsx` | Variable role map used to prevent leakage. |
| `analysis(S4)/tables/level1_content_analysis.xlsx` | Level 1 regression/group-test outputs. |
| `analysis(S4)/tables/level2_agent_network_analysis.xlsx` | Level 2 regression/group-test outputs. |
| `analysis(S4)/tables/level3_agent_topic_matching_analysis.xlsx` | Level 3 matching outputs across primary and supplementary outcomes. |
| `analysis(S4)/tables/three_level_validation_report.json` | Row-count and validation summary. |
| `analysis(S4)/figures/*.png` | Thesis-facing figures for Levels 1-3. |

Important figures:

- `analysis(S4)/figures/level1_content_regression_summary.png`
- `analysis(S4)/figures/level1_cosinesim_decile_trends.png`
- `analysis(S4)/figures/level2_network_metric_correlations.png`
- `analysis(S4)/figures/level3_agent_topic_matchscore_trends.png`

## Reproducing Stage 4

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe analysis(S4)\stage4_pipeline.py
```

The pipeline writes master files, Excel analysis tables, figures, validation reports, the Stage 4 findings summary, and the generated notebook.

Tests for the Stage 4 pipeline are in:

```text
analysis(S4)/tests/test_stage4_pipeline.py
```

Run them from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest analysis(S4)\tests
```

## Interpretation Notes

- The project is explanatory and associational, not causal.
- Stage 4 treats diffusion-derived cascade and network measures as primary or supplementary dependent variables, not ordinary leakage-free predictors.
- Different levels use different supplementary outcomes because Level 1 is article-agent, Level 2 is agent-level, and Level 3 is agent-topic.
- Level 1 excludes centrality-class network-position outcomes; centrality is modeled only at Level 2 and Level 3 where agent or agent-topic aggregation gives it a coherent interpretation.
- `analysis_master.xlsx` is intentionally not used in the final Stage 4 framework.
- Topic labels are standardized to English before Stage 4 modeling.
- Complete-case model sample sizes can be smaller than master-file row counts.
- Level 3 sparse agent-topic cells should be interpreted cautiously.

## Security And Privacy Notes

- Do not commit API keys, GitHub tokens, or other credentials.
- Notebook credentials should be stored in environment variables or local config files ignored by Git.
- The repository `.gitignore` excludes local environments, caches, Jupyter checkpoints, and local assistant/editor configuration.
