# Stage 4 Three-Level Analysis Plan

## Summary

Stage 4 must strictly follow the three-level analytical framework described in the interim report, with one important clarification: the three levels are **content**, **agent characteristics**, and **content-agent matching**. Agents are part of the social network and are the origin points of diffusion, so their observable features can proxy the local audience and sharing context. Diffusion-derived network metrics, however, are reconstructed from observed diffusion records and should be treated as diffusion-pattern descriptors rather than ordinary ex-ante network predictors. The previous `analysis_master.xlsx` mixed variables from multiple analytical levels and should no longer be used as the central Stage 4 dataset.

Stage 4 answers two connected research questions:

1. **Are content factors, agent characteristics, and content-agent matching factors associated with diffusion effectiveness?**
2. **If they are associated, which specific factors matter, and through which diffusion dimensions?**

Use "affect" only when describing the broad research motivation. In statistical findings and model interpretation, use association language unless a causal identification strategy is explicitly justified.

The thesis theme remains:

```text
One Size Does Not Fit All:
Marketing diffusion effectiveness depends not only on content,
not only on agent characteristics and embedded sharing context,
but also on the fit between content and agent-topic context.
```

Stage 4 is an explanatory empirical analysis for a master's thesis. It should be broad, rigorous, interpretable, and clearly connected to the managerial implication of personalized content assignment.

## Core Principle

Do **not** build one oversized master table that mixes all analytical levels.

Instead, generate separate datasets for each research layer:

```text
analysis(S4)/level1_content_master.xlsx
analysis(S4)/level2_agent_network_master.xlsx
analysis(S4)/level3_agent_topic_match_master.xlsx
```

Delete the old mixed file:

```text
analysis(S4)/analysis_master.xlsx
```

The pipeline should remove this legacy file at the start of a Stage 4 rerun if it exists. If backward compatibility is temporarily needed during development, `analysis_master.xlsx` may be kept only as a short-lived intermediate artifact, but it must not be cited in the thesis and should not be part of final Stage 4 outputs.

## Topic Label Standardization

Stage 4 should use **English topic labels as the canonical topic labels** in all master files, models, tables, figures, and thesis-facing findings.

Canonical topic labels:

```text
Home Design & Decoration
Real Estate & Architecture
Events & Promotions
Brand & Marketing
Lifestyle & Culture
Customer Service & Management
```

Several source files use Chinese topic labels, while `batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx` uses English topic labels. Stage 4 must standardize this before any analysis:

| Chinese source label | English canonical label |
| --- | --- |
| 家居设计与装修 | Home Design & Decoration |
| 房地产与建筑 | Real Estate & Architecture |
| 活动与促销 | Events & Promotions |
| 品牌与市场推广 | Brand & Marketing |
| 生活方式与文化 | Lifestyle & Culture |
| 客户服务与管理 | Customer Service & Management |

Implementation rules:

- `TopContentCluster` in all Stage 4 master files should contain English canonical labels.
- Chinese topic labels may be retained only in provenance or validation fields such as `TopContentCluster_source_zh`.
- English topic-score columns should be created with stable names, for example `topic_home_design_decoration`, `topic_real_estate_architecture`, and so on.
- Do not let English and Chinese topic labels coexist in the same modeling column.
- The join quality report must include a `topic_label_standardization` sheet showing source labels, mapped English labels, unmapped labels, and row counts.

## Attribute Provenance And Leakage Control

Agent attributes are not newly inferred in Stage 4.

- `agent_gender` should come from the gender data already prepared before Stage 4. In earlier processing, `unique_agentsgender.xlsx` was used, and agents not listed there were manually assigned gender based on agent names. Stage 4 should treat this as an existing cleaned attribute source and should not re-infer gender.
- `agent_job` and `agent_dep` should come from the job/department data already prepared from `agent_dep_job.csv`. Stage 4 should treat these as existing agent attributes and should not reclassify raw job names unless a separate documented mapping is required for presentation.
- `JobCategory` was already assigned during S3 based on job type. Stage 4 should carry forward the existing S3-assigned `JobCategory`; it should not reclassify agent jobs.

Data leakage must be handled explicitly.

- Only variables that represent diffusion effectiveness should be used as dependent variables/outcomes.
- Variables mechanically calculated from the same diffusion process must not be used as predictors for an outcome that they directly or indirectly define.
- Diffusion-structure variables such as depth, width, centrality, Wiener index, structural virality, repeat exposure, and reshare metrics may be outcomes, diffusion-pattern descriptors, or robustness indicators depending on the model, but their role must be declared before modeling.
- Agent demographic and job attributes can be treated as explanatory variables because they are agent attributes rather than post-hoc diffusion outcomes.
- Content features from Stage 2 can be treated as explanatory variables because they describe article content rather than observed diffusion performance.
- Match variables can be used in Level 3 only, because they are designed to represent content-agent alignment. They should not be mixed into Level 1 content-only models.

Before any regression is run, each variable must be assigned one role:

```text
outcome
content predictor
agent attribute predictor
matching predictor
diffusion-pattern descriptor
control
validation-only field
```

The Stage 4 findings must state these roles clearly to avoid treating post-hoc diffusion calculations as if they were independent predictors.

Stage 4 must generate:

```text
analysis(S4)/tables/variable_role_map.xlsx
```

Required columns:

- `variable`
- `level`
- `source_file`
- `role`
- `allowed_as_predictor`
- `allowed_as_outcome`
- `leakage_note`
- `thesis_interpretation_note`

## Source Readiness Precheck

Before generating any of the three level-specific master files, the pipeline must inspect the S3 source files and the supporting S2/attribute files needed for joins, then write:

```text
analysis(S4)/tables/source_readiness_report.xlsx
```

The precheck must answer:

- Does the source file exist?
- Does it have the expected row count?
- Does it contain required keys?
- Does it contain required outcome inputs?
- Which variables must be merged from other sources?
- Are there duplicate keys or role/category conflicts?
- Which missing values need to be reported?
- Are S2 title joins exact, complete, and conflict-free?
- Are topic labels standardized to English before modeling?
- Are old mixed Stage 4 outputs present and therefore at risk of being accidentally reused?

Files to inspect:

```text
diffusion(S3)/final_results.xlsx
diffusion(S3)/agent_level_results.xlsx
diffusion(S3)/agent_topic_level_results.xlsx
diffusion(S3)/diffusion_corrected_layers.xlsx
batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx
batch_outputs(S2)/filtered_results_all_cleaned.xlsx
diffusion(S3)/unique_agentsgender.xlsx
diffusion(S3)/agent_dep_job.csv
```

### Current Precheck Findings

Read-only inspection of the current S3 files produced the following findings.

#### `diffusion(S3)/final_results.xlsx`

Shape:

```text
6,557 rows x 29 columns
```

It satisfies Level 1 article-agent keys:

- `agent_name`
- `article_title`
- `Title`

It satisfies Level 1 outcome inputs:

- `first_layer_width`
- `second_layer_width`
- `depth`
- `reshare_pct`
- `duration_mean_s`
- `structural_virality`
- `wiener_index`

It satisfies Level 3 matching inputs:

- `MatchScore`
- `ProfessionContentMatch`
- `JobCategory`
- `agent_job`

Current limitations:

- It does **not** contain `TopContentCluster`, `CosineSim`, `EuclideanDist`, `ManhattanDist`, `WordCount`, `HasImage`, or `NumImages`; these must be merged from S2 content and article metadata files for Level 1.
- It contains Chinese content topic-score columns. These should be renamed to English canonical topic-score columns before Stage 4 modeling.
- `agent_job` is missing in 29 rows.
- Exact `agent_name + article_title` duplicate rows: 0.
- Normalized `agent_name + article_title` duplicate rows: 1. This must be reported but should not automatically collapse rows.
- No agents currently have multiple `JobCategory` values in `final_results.xlsx`.
- No agents currently have multiple `agent_job` values in `final_results.xlsx`.

#### `diffusion(S3)/agent_level_results.xlsx`

Shape:

```text
592 rows x 27 columns
```

It satisfies Level 2 keys:

- `agent_name`

It satisfies Level 2 outcome and network descriptor inputs:

- `cascade_size_mean`
- `first_layer_width_avg`
- `second_layer_width_avg`
- `depth_mean`
- `reshare_mean`
- `structural_virality_mean`
- `duration_mean_of_means`
- `agent_deg_centrality_mean`
- `avg_out_degree_centrality_mean`
- `centrality_mean`
- `wiener_index_mean`
- `gender_assortativity_mean`
- `repeat_exposure_1st_nodes_pct`
- `repeat_exposure_2nd_nodes_pct`

Current limitations:

- It does not contain `agent_gender`, `agent_dep`, `agent_job`, or `JobCategory`; these must be merged from the cleaned agent attribute sources and the existing S3-assigned `JobCategory`.
- It does not contain `article_count_per_agent` or `log_article_count_per_agent`; these must be calculated from `final_results.xlsx`.
- It already contains `matchscore_mean` and `profession_content_match_mean`, but these are content-agent matching variables. They should not be used in the Level 2 agent-characteristic core model and should be excluded from the Level 2 modeling table or marked as validation-only.
- Unique agents: 592.
- Duplicate `agent_name` rows: 0.

#### `diffusion(S3)/agent_topic_level_results.xlsx`

Shape:

```text
1,142 rows x 26 columns
```

It satisfies Level 3 keys:

- `agent_name`
- `TopContentCluster`

It satisfies Level 3 outcome and network descriptor inputs:

- `cascade_size_mean`
- `first_layer_width_avg`
- `second_layer_width_avg`
- `depth_mean`
- `reshare_mean`
- `structural_virality_mean`
- `duration_mean_of_means`
- `agent_deg_centrality_mean`
- `avg_out_degree_centrality_mean`
- `centrality_mean`

Current limitations:

- It does not contain `MatchScore_mean`, `MatchScore_median`, `ProfessionContentMatch_mean`, `agent_topic_article_n`, `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, `CosineSim_mean`, `JobCategory`, or `agent_job`.
- Its current `TopContentCluster` values are Chinese labels. They must be mapped to English canonical topic labels before being merged with Stage 4 matching variables.
- Matching variables must be generated by merging `final_results.xlsx` with S2 English topic labels, then aggregating by `agent_name + TopContentCluster`.
- `JobCategory` should be carried forward from the existing S3 assignment in `final_results.xlsx` using `agent_name`. If an agent has multiple categories in future data, this must be written to a conflict sheet rather than silently merged.
- Unique agent-topic pairs: 1,142.
- Duplicate `agent_name + TopContentCluster` rows: 0.
- Unique agents: 592.
- Unique topics: 6.

Cross-source alignment:

- Agents in `final_results.xlsx` but not `agent_level_results.xlsx`: 0.
- Agents in `agent_level_results.xlsx` but not `final_results.xlsx`: 0.
- Agents in `agent_topic_level_results.xlsx` but not `agent_level_results.xlsx`: 0.
- Agents in `agent_level_results.xlsx` but not `agent_topic_level_results.xlsx`: 0.

Supporting source checks:

- `final_results.xlsx` has 811 exact unique `Title` values, all of which are present in the S2 translated content file.
- Normalized S2 title keys contain four duplicate groups with conflicting `CosineSim`, distance, or article metadata values. Therefore, Stage 4 joins should use exact `Title` matches first; normalized-title fallback should be used only for unmatched titles and only when the fallback key is unique and conflict-free.
- `diffusion_corrected_layers.xlsx` uses Chinese topic labels and must be mapped to English if its topic labels are used for validation.
- `agent_dep_job.csv` has duplicate agent rows and several department/job conflicts. These should be reported in `source_readiness_report.xlsx` and `join_quality_report.xlsx`; Stage 4 should not silently overwrite conflicting agent attributes.
- Current topic distribution is highly imbalanced at the article-agent level: `Home Design & Decoration` dominates the observations, while `Brand & Marketing` and `Customer Service & Management` have small cell counts. This imbalance must be reported before interpreting topic coefficients.

## Data Architecture

### Level 1: Content-Level / Article-Agent Diffusion Cases

**Purpose:** answer whether content factors affect diffusion effectiveness and identify which content factors matter.

**Input files:**

```text
diffusion(S3)/final_results.xlsx
batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx
batch_outputs(S2)/filtered_results_all_cleaned.xlsx
diffusion(S3)/diffusion_corrected_layers.xlsx
```

**Unit of analysis:**

```text
one row = one article-agent diffusion case
```

**Expected row count:** 6,557 rows, matching `final_results.xlsx`.

**Variables to include:**

Content variables:

- `TopContentCluster`, using English canonical labels only
- six English canonical topic-score columns
- `CosineSim`
- `EuclideanDist`
- `ManhattanDist`
- `WordCount`
- `HasImage`
- `NumImages`

Content join rule:

- Join `final_results.xlsx` to S2 content and article metadata by exact `Title` first, because the current exact-title coverage is complete.
- Use normalized-title fallback only for future unmatched titles, and only when the normalized key is unique and has no conflicting content or metadata values.
- Write exact-match coverage, normalized fallback usage, duplicate-title conflicts, and unmatched titles to `join_quality_report.xlsx`.
- After the join, `TopContentCluster` must be English. Source Chinese topic labels should be retained only as optional validation/provenance fields.

Topic representation rule:

- The main Level 1 regression should use `TopContentCluster` as a categorical predictor, with one reference category omitted.
- The six topic-score columns should not all be entered into the same regression because they are compositional scores whose row sums are approximately 100, which creates perfect or near-perfect multicollinearity.
- Topic-score robustness can use either five topic-score columns after dropping the reference topic score, or PCA components from the six topic-score columns.
- Do not include `TopContentCluster` dummies and all topic-score columns in the same main model.

CosineSim interpretation:

- Higher `CosineSim` means stronger title-content semantic consistency.
- Lower `CosineSim` means weaker title-content consistency and may indicate title-content mismatch or a "clickbait-like" pattern.

Diffusion outcomes:

- `cascade_size`
- `log_reach`
- `depth`
- `second_layer_width`
- `reshare_pct`
- `any_reshare`
- `duration_mean_s`
- `duration_mean_s_winsorized`
- `log_duration`
- `structural_virality`
- `structural_virality_winsorized`

Precise `cascade_size` definition:

```text
cascade_size = diffusion_corrected_layers.groupby(["agent_name", "article_title"]).size()
```

This definition intentionally matches the current S3 agent-level `cascade_size_mean`, which is based on total corrected-layer rows for an article-agent pair. It is not the same as `first_layer_width + second_layer_width`. Stage 4 should also calculate and report diagnostic alternatives:

```text
direct_width_reach = first_layer_width + second_layer_width
cascade_size_excl_layer0 = count of corrected-layer rows where correct_layer > 0
unique_reader_count = number of unique reader_wechat_nn values
layer_0_count = count of corrected-layer rows where correct_layer == 0
```

Do not silently redefine `cascade_size` after Level 2 and Level 3 have already been generated from S3. If an alternative reach definition is used, label it as a robustness or diagnostic outcome.

Corrected-layer checks:

- `corrected_depth`
- `layer_1_count`
- `layer_2_count`
- consistency checks between S3 summary metrics and corrected-layer aggregation

**Variables not to use as Level 1 core predictors:**

- `MatchScore`
- `ProfessionContentMatch`
- agent-topic opportunity variables
- agent-level aggregate variables such as `cascade_size_mean`, `depth_mean`, `repeat_exposure_1st_nodes_pct`

These belong to Level 2 or Level 3. Level 1 should remain a clean content-effect analysis. `MatchScore` and `ProfessionContentMatch` should not be included in `level1_content_master.xlsx`; if needed for validation, place them in a separate validation sheet rather than in the Level 1 modeling table.

### Level 2: Agent-Characteristic Level

**Purpose:** answer whether agent characteristics are associated with observed average diffusion patterns. In this level, agent features are interpreted as characteristics of embedded sharers and as proxies for local audience/sharing context, not as direct measures of post-hoc network structure.

**Input files:**

```text
diffusion(S3)/agent_level_results.xlsx
diffusion(S3)/final_results.xlsx
diffusion(S3)/agent_dep_job.csv
diffusion(S3)/unique_agentsgender.xlsx
```

**Unit of analysis:**

```text
one row = one agent
```

**Expected row count:** 592 rows, matching unique agents.

**Variables to include:**

Agent-characteristic predictors:

- `JobCategory`
- `agent_gender`

Agent activity / estimation-stability control:

- `article_count_per_agent`, calculated from `final_results.xlsx` as the number of article-agent cases per agent
- `log_article_count_per_agent = log1p(article_count_per_agent)`

`article_count_per_agent` is not a diffusion-success outcome. It captures how much article-level evidence is available for each agent and how stable the agent-level averages are likely to be. Include `log_article_count_per_agent` in the Level 2 core model and report a no-article-count version as robustness.

Descriptive agent attributes:

- `agent_dep`
- `agent_job`

`JobCategory` is the main categorical role variable for Level 2 regression. `agent_dep` and `agent_job` should be used for descriptive statistics, category interpretation, and appendix tables only. They should not be entered into the same core regression with `JobCategory` because they are fine-grained sources of the role category and can create collinearity or over-fragmentation.

Diffusion-pattern descriptors reconstructed from observed diffusion:

- `agent_deg_centrality_mean`
- `avg_out_degree_centrality_mean`
- `centrality_mean`
- `wiener_index_mean`
- `gender_assortativity_mean`
- `repeat_exposure_1st_nodes_pct`
- `repeat_exposure_2nd_nodes_pct`

These descriptors are useful for describing diffusion-pattern heterogeneity and profiling how agents appear within reconstructed diffusion records. They must not be presented as leakage-free ex-ante predictors of mechanically related diffusion outcomes.

Agent-level diffusion outcomes:

- `cascade_size_mean`
- `log_agent_cascade_size_mean = log1p(cascade_size_mean)`, the primary Level 2 diffusion-capability outcome
- `first_layer_width_avg`
- `second_layer_width_avg`
- `depth_mean`
- `reshare_mean`
- `structural_virality_mean`
- `duration_mean_of_means`

Primary versus secondary Level 2 outcomes:

- Primary DV: `log_agent_cascade_size_mean`
- Secondary / robustness DVs: `reshare_mean`, `depth_mean`, `second_layer_width_avg`, `structural_virality_mean`, and `duration_mean_of_means`

Supporting variability measures:

- `cascade_size_var`
- `depth_var`
- `reshare_var`
- `duration_var_of_means`
- `duration_mean_of_vars`
- `duration_var_of_vars`

**Variables not to use as Level 2 core predictors:**

- `TopContentCluster` as an analytical key
- agent-topic match variables
- `matchscore_mean`
- `profession_content_match_mean`
- opportunity matrix variables

Level 2 should focus on agent-characteristic heterogeneity, not topic-specific fit.

Although `agent_level_results.xlsx` already contains `matchscore_mean` and `profession_content_match_mean`, these variables summarize content-agent matching across the agent's articles. They belong conceptually to Level 3 or to a clearly labeled bridge/validation appendix. They should not be included in the Level 2 agent-characteristic modeling table or Level 2 core regressions.

### Level 3: Content-Agent Matching / Agent-Topic Level

**Purpose:** answer whether content-agent matching affects diffusion effectiveness and identify which agent-topic combinations perform better.

**Input files:**

```text
diffusion(S3)/agent_topic_level_results.xlsx
diffusion(S3)/final_results.xlsx
diffusion(S3)/agent_dep_job.csv
diffusion(S3)/unique_agentsgender.xlsx
```

**Unit of analysis:**

```text
one row = one agent + one TopContentCluster
```

**Expected row count:** 1,142 rows, matching `agent_topic_level_results.xlsx`.

**Variables to include:**

Agent-topic keys:

- `agent_name`
- `TopContentCluster`, using English canonical labels only

Matching variables, aggregated from `final_results.xlsx` if needed:

- article count per agent-topic pair
- `MatchScore_mean`
- `MatchScore_median`
- `ProfessionContentMatch_mean`
- matched-case count

Content controls aggregated to the agent-topic level:

- `WordCount_mean`
- `HasImage_share`
- `NumImages_mean`
- `CosineSim_mean`
- `log_agent_topic_article_n = log1p(agent_topic_article_n)`

Aggregation path:

1. Merge `final_results.xlsx` with S2 article topic labels by exact `Title`.
2. Use normalized-title fallback only for unmatched titles and only when the fallback key is unique and conflict-free.
3. Map any Chinese source topic labels to English canonical `TopContentCluster`.
4. Confirm the merge produces `agent_name + TopContentCluster` for every row used in matching aggregation.
5. Group by `agent_name + TopContentCluster`.
6. Calculate `agent_topic_article_n`, `MatchScore_mean`, `MatchScore_median`, `ProfessionContentMatch_mean`, matched-case count, and the aggregated content controls listed above.
7. Merge these aggregated fields into `agent_topic_level_results.xlsx` by `agent_name + TopContentCluster`.

`ProfessionContentMatch_mean` is a proportion of matched article-agent cases within an agent-topic pair. It should not be interpreted as the original binary `ProfessionContentMatch` variable.

Agent-topic diffusion outcomes:

- `cascade_size_mean`
- `log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)`, the primary Level 3 matching outcome
- `first_layer_width_avg`
- `second_layer_width_avg`
- `depth_mean`
- `reshare_mean`
- `structural_virality_mean`
- `duration_mean_of_means`

Agent/network controls for regression:

- `JobCategory`
- `agent_gender`

Descriptive agent attributes:

- `agent_dep`
- `agent_job`

`JobCategory` source rule:

- Carry forward the existing S3-assigned `JobCategory` from `final_results.xlsx` by `agent_name`.
- If an agent has multiple `JobCategory` values, write that agent to the source readiness conflict sheet.
- Do not silently choose among conflicting categories without reporting the conflict.
- In Level 3 core regression, use `JobCategory` as the main agent role category. Use `agent_dep` and `agent_job` for interpretation and appendix summaries, not as simultaneous core categorical predictors.

Diffusion-pattern descriptors:

- `agent_deg_centrality_mean`
- `avg_out_degree_centrality_mean`
- `centrality_mean`

These may be used for mechanism or robustness analysis only when the model text clearly states that they are derived from observed diffusion/network structure and therefore should not be interpreted as leakage-free causal predictors.

Sparse-cell diagnostics:

- `agent_topic_article_n`
- `job_topic_cell_n`
- `is_sparse_cell_10`, using `n < 10` as too sparse for interpretation
- `is_sparse_cell_30`, using `n < 30` as weak evidence for main-text claims

Report two evidence tiers:

- `n >= 10`: exploratory/reportable in appendix or annotated tables.
- `n >= 30`: stronger evidence for main heatmap and thesis discussion.

Current data are sparse at the agent-topic level: the median agent-topic pair has only two articles, about 11% of pairs have `n >= 10`, and about 4% have `n >= 30`. Therefore, individual agent-topic rankings should be treated as illustrative unless they pass the sample-size threshold. Main claims should rely on model estimates, job-topic patterns, and sensitivity checks rather than on isolated small cells.

Level 3 is the formal home of the opportunity matrix and the thesis's "One Size Does Not Fit All" contribution.

## Analysis Design

### Regression Reporting Standards

All core regression result tables should include:

- raw coefficient
- robust standard error
- p-value
- confidence interval
- model sample size
- model family
- standardized beta for continuous predictors

Continuous predictors should be z-score standardized for comparability in the reported standardized beta column. Categorical predictors should be interpreted through their dummy coefficients against a declared reference group rather than through standardized beta.

For logistic and count models, standardized continuous predictors help compare predictor scaling, but coefficients should still be interpreted in the model's natural scale:

- Logistic models should report odds ratios or marginal effects.
- Negative Binomial and Poisson models should report incidence-rate ratios or clearly state that coefficients are on the log-count scale.
- Standardized coefficients should not be compared mechanically across OLS, logistic, and count models.

Model diagnostics to report:

- variance inflation factor or condition-number checks for models with multiple continuous predictors
- overdispersion diagnostics before relying on Poisson models
- sample size after missing-value drops
- reference categories for all categorical predictors
- multiple-comparison control, such as FDR correction, for large sets of pairwise group tests

### Part 1: Does Content Affect Diffusion?

Use `level1_content_master.xlsx`.

Main question:

```text
Do article topic, semantic consistency, article length, and image richness affect diffusion outcomes?
```

Analyses:

- Sample overview and outcome distributions.
- Topic distribution and content metadata distribution, reported at both the unique-article level and the article-agent observation level.
- Topic group comparisons for reach, depth, reshare, duration, and virality.
- `CosineSim` decile and quartile trend analysis.
- Correlations between topic scores, content metadata, and diffusion outcomes.
- Content-only regression models.
- Robustness checks using `EuclideanDist` and `ManhattanDist`.
- Optional cascade-shape classification as a supplemental analysis.

Model families:

- OLS for `log_reach`, `log_duration`, and `structural_virality_winsorized`.
- Logistic regression for `any_reshare`.
- Negative Binomial for `cascade_size` and `second_layer_width`.
- Poisson only as a robustness reference, with overdispersion diagnostics reported.
- Report robust standard errors.
- Because article-level content variables repeat across multiple agents and agents also repeat across multiple articles, include article-clustered and agent-clustered standard error robustness where feasible. Use article-clustered standard errors as the main content-level robustness check, agent-clustered standard errors as an additional robustness check, and two-way clustered standard errors only if the implementation is stable.

Topic imbalance caveat:

- `Home Design & Decoration` is the dominant topic in the observed article-agent data.
- Rare topics such as `Brand & Marketing` and `Customer Service & Management` should be interpreted cautiously in dummy-variable regressions.
- For sparse topics, emphasize descriptive evidence, confidence intervals, and robustness checks rather than treating a single coefficient as definitive.

Core model:

```text
diffusion_outcome
= C(TopContentCluster)
+ CosineSim
+ WordCount
+ HasImage
+ NumImages
+ error
```

Topic-score robustness:

```text
diffusion_outcome
= five topic-score columns, dropping the reference topic score
+ CosineSim
+ WordCount
+ HasImage
+ NumImages
+ error
```

Alternative topic-score robustness:

```text
diffusion_outcome
= first 2-3 PCA components of the six topic-score columns
+ CosineSim
+ WordCount
+ HasImage
+ NumImages
+ error
```

The main model should use `TopContentCluster` because it is easier to interpret in the thesis. Topic-score and PCA models are robustness checks only.

Alternative distance robustness:

```text
replace CosineSim with EuclideanDist or ManhattanDist
```

Expected output files:

```text
analysis(S4)/tables/level1_content_analysis.xlsx
analysis(S4)/figures/level1_content_outcome_distributions.png
analysis(S4)/figures/level1_topic_outcome_boxplots.png
analysis(S4)/figures/level1_cosinesim_decile_trends.png
analysis(S4)/figures/level1_content_regression_summary.png
analysis(S4)/figures/level1_cascade_shape_clusters.png
```

Supplemental cascade-shape analysis:

- Use `log_reach`, `depth`, `reshare_pct`, and `structural_virality_winsorized`.
- Run a simple k-means classification with k = 3 or k = 4.
- Label clusters descriptively, such as low diffusion, broad-shallow, deep cascade, or active resharing.
- Treat this as a visual/interpretive supplement, not as the main causal or explanatory model.

Thesis interpretation:

```text
Content factors are associated with diffusion, but different content features affect different diffusion dimensions.
```

### Part 2: Are Agent Characteristics Associated With Observed Diffusion Patterns?

Use `level2_agent_network_master.xlsx`.

Main question:

```text
Are agent characteristics associated with observed average diffusion patterns?
```

Analyses:

- Agent-level performance distribution.
- Diffusion-pattern descriptor distributions.
- Agent job and department group comparisons.
- Centrality-performance associations interpreted as diffusion-pattern description.
- Repeat-exposure analysis.
- Agent-level explanatory regressions using `JobCategory`, `agent_gender`, and `log_article_count_per_agent` as primary predictors.
- Descriptive association analysis for diffusion-pattern descriptors, with leakage caveats.
- Optional top/bottom agent performance profile for descriptive interpretation.

Model families:

- OLS or robust OLS for continuous agent-level outcomes.
- If outcome distributions are highly skewed, report log-transformed versions as robustness.

Primary Level 2 outcome:

```text
log_agent_cascade_size_mean = log1p(cascade_size_mean)
```

Secondary Level 2 outcomes:

```text
reshare_mean
depth_mean
second_layer_width_avg
structural_virality_mean
duration_mean_of_means
```

Core model:

```text
log_agent_cascade_size_mean
= JobCategory
+ agent_gender
+ log_article_count_per_agent
+ error
```

Report a robustness version without `log_article_count_per_agent` to show whether role/gender patterns depend on the article-count adjustment. If using weighted regression, use `article_count_per_agent` only as a clearly labeled precision-weighted robustness specification.

`agent_dep` and `agent_job` should be reported in descriptive and appendix tables only, unless a separate robustness model is explicitly labeled as exploratory.

Descriptor association model:

```text
log_agent_cascade_size_mean
= mechanism block
+ JobCategory
+ agent_gender
+ log_article_count_per_agent
+ error
```

Descriptor blocks should be specified explicitly rather than selected ad hoc:

- Centrality block: `agent_deg_centrality_mean`, `avg_out_degree_centrality_mean`
- Repeat-exposure block: `repeat_exposure_1st_nodes_pct`, `repeat_exposure_2nd_nodes_pct`
- Network-composition block: `gender_assortativity_mean`

Run these blocks separately before considering a combined model, because the descriptors can be correlated and are often derived from the observed diffusion process. These models should be labeled as descriptive diffusion-pattern associations, not as causal or leakage-free prediction. Do not use an outcome as a predictor of itself; for example, do not use `structural_virality_mean` as a descriptor predictor when the dependent variable is `structural_virality_mean`.

Expected output files:

```text
analysis(S4)/tables/level2_agent_network_analysis.xlsx
analysis(S4)/figures/level2_agent_performance_distribution.png
analysis(S4)/figures/level2_network_metric_correlations.png
analysis(S4)/figures/level2_job_agent_performance.png
analysis(S4)/figures/level2_repeat_exposure_patterns.png
```

Thesis interpretation:

```text
Agent-characteristic heterogeneity matters: some agents systematically generate stronger observed diffusion, while reconstructed network metrics describe the diffusion patterns associated with those agents rather than ex-ante network causes.
```

### Part 3: Does Content-Agent Matching Affect Diffusion?

Use `level3_agent_topic_match_master.xlsx`.

Main question:

```text
Do agent-topic combinations and matching measures explain diffusion differences beyond content-only and agent-only patterns?
```

Analyses:

- Agent-topic performance distribution.
- `MatchScore_mean` and `ProfessionContentMatch_mean` trends.
- Job-topic opportunity matrix.
- Sparse-cell diagnostics.
- Agent-topic regression models.
- Correlation and collinearity diagnostics between `MatchScore_mean` and `ProfessionContentMatch_mean`.
- Sensitivity checks using different minimum cell-size thresholds.
- Best observed agent-topic combinations, reported only when sample size is sufficient.

Model families:

- OLS or robust OLS for agent-topic mean outcomes.
- Unweighted regression as the main specification when the interpretation target is the average agent-topic combination.
- Weighted regression using `agent_topic_article_n` as the exposure-weighted specification when the interpretation target is the average observed article-agent evidence.
- Report unweighted and weighted results side by side when the substantive conclusion changes.
- Sensitivity checks excluding sparse cells.

Primary Level 3 outcome:

```text
log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)
```

Secondary Level 3 outcomes:

```text
reshare_mean
depth_mean
second_layer_width_avg
structural_virality_mean
duration_mean_of_means
```

Core matching models:

Do not include `MatchScore_mean` and `ProfessionContentMatch_mean` in the same core regression. They are generated from the same matching logic and are expected to be highly correlated. Report them as two alternative matching specifications.

Model A, continuous matching intensity, is the primary matching model:

```text
log_agent_topic_cascade_size_mean
= MatchScore_mean
+ TopContentCluster
+ JobCategory
+ agent_gender
+ log_agent_topic_article_n
+ WordCount_mean
+ HasImage_share
+ NumImages_mean
+ CosineSim_mean
+ error
```

Model B, binary/proportion matching robustness, is the alternative matching model:

```text
log_agent_topic_cascade_size_mean
= ProfessionContentMatch_mean
+ TopContentCluster
+ JobCategory
+ agent_gender
+ log_agent_topic_article_n
+ WordCount_mean
+ HasImage_share
+ NumImages_mean
+ CosineSim_mean
+ error
```

Leakage-safe controls are therefore explicitly defined as `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, and `CosineSim_mean`. They describe content volume or content features, not realized diffusion outcomes. Do not use diffusion-derived variables such as `depth_mean`, `centrality_mean`, `wiener_index_mean`, `structural_virality_mean`, or `reshare_mean` as ordinary controls in the core matching model.

Conditional mechanism moderation model:

```text
log_agent_topic_cascade_size_mean
= MatchScore_mean
+ agent_deg_centrality_mean
+ MatchScore_mean x agent_deg_centrality_mean
+ TopContentCluster
+ JobCategory
+ agent_gender
+ log_agent_topic_article_n
+ error
```

Run this moderation model only as a supplementary descriptive analysis. It answers whether the matching-diffusion association differs across reconstructed centrality levels; it is not a replacement for the Level 2 agent-characteristic analysis. Report it separately from the main matching model and interpret it as descriptive heterogeneity only.

Opportunity matrix:

```text
JobCategory x TopContentCluster
```

Metrics to report:

- mean reach
- mean depth
- mean reshare
- mean structural virality
- mean MatchScore
- cell count
- sparse-cell flag

Expected output files:

```text
analysis(S4)/tables/level3_agent_topic_matching_analysis.xlsx
analysis(S4)/figures/level3_job_topic_opportunity_heatmap.png
analysis(S4)/figures/level3_agent_topic_matchscore_trends.png
analysis(S4)/figures/level3_matchscore_centrality_moderation.png
analysis(S4)/figures/level3_sparse_cell_diagnostics.png
analysis(S4)/figures/level3_top_agent_topic_profiles.png
```

Thesis interpretation:

```text
Matching should be evaluated at the agent-topic level. This level directly supports the "One Size Does Not Fit All" argument by identifying which agent roles appear better suited to which content topics.
```

## Integrated Thesis Structure

Recommended Results chapter structure:

1. **Data construction and three-level framework**
   - Explain why S4 uses three separate datasets.
   - Define Level 1, Level 2, and Level 3.
   - Explain why the old mixed `analysis_master.xlsx` is removed.

2. **Level 1: Content effects**
   - Topic differences.
   - Title-content consistency.
   - Article length and image richness.
   - Content-only regressions.

3. **Level 2: Agent-characteristic effects**
   - Agent heterogeneity.
   - Formal role and gender attributes.
   - Reconstructed centrality as a diffusion-pattern descriptor.
   - Repeat exposure as a diffusion-pattern descriptor.
   - Job and department differences.

4. **Level 3: Content-agent matching effects**
   - MatchScore and ProfessionContentMatch at the agent-topic level, reported as separate model specifications.
   - Conditional MatchScore-by-centrality moderation as supplementary descriptive heterogeneity.
   - Opportunity matrix.
   - Sparse-cell caution.
   - Personalized content assignment implication.

5. **Integrated interpretation**
   - Compare content-only, agent-only, and matching-layer findings.
   - Explain why matching adds insight beyond content and agent effects alone.

6. **Managerial implications**
   - Personalized assignment of article topics to agent roles.
   - Avoid uniform broadcasting.
   - Use opportunity matrix as decision support, not causal prescription.

## Thesis-Level Highlights

The Stage 4 contribution should be more than a list of regressions. The distinctive features are:

- A three-level empirical framework derived from the interim report.
- Real WeChat marketing diffusion data.
- LLM-generated content-topic and semantic-consistency variables.
- Corrected cascade/network metrics from S3.
- Multi-dimensional diffusion outcomes: reach, depth, reshare, duration, and structural virality.
- Separation of content effects, agent-characteristic effects, and matching effects.
- Agent-topic opportunity matrix as the practical "One Size Does Not Fit All" output.
- Conditional moderation analysis describing whether the matching-diffusion association varies across reconstructed centrality groups.
- Supplemental cascade-shape classification to translate diffusion outcomes into intuitive propagation patterns.

## Implementation Changes

Update `analysis(S4)/stage4_pipeline.py`:

- Add paths for:

```text
diffusion(S3)/agent_level_results.xlsx
diffusion(S3)/agent_topic_level_results.xlsx
```

- Keep paths for the supporting files required by Stage 4 joins:

```text
diffusion(S3)/diffusion_corrected_layers.xlsx
batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx
batch_outputs(S2)/filtered_results_all_cleaned.xlsx
diffusion(S3)/unique_agentsgender.xlsx
diffusion(S3)/agent_dep_job.csv
```

- Add a pre-run cleanup step:

```text
analysis(S4)/analysis_master.xlsx
```

- If this legacy file exists, delete it before writing new outputs.
- Do not regenerate it later in the pipeline.

- Add a source readiness gate before master generation:

```text
check_source_readiness()
```

- This gate should inspect `final_results.xlsx`, `agent_level_results.xlsx`, `agent_topic_level_results.xlsx`, `diffusion_corrected_layers.xlsx`, S2 content files, `unique_agentsgender.xlsx`, and `agent_dep_job.csv`.
- It should write `source_readiness_report.xlsx`.
- It should raise an error only for fatal problems such as missing source files, missing required keys, missing required outcomes, failed exact S2 title coverage, unmapped topic labels, or duplicate primary keys in Level 2/3.
- It should report but not fail on known nonfatal issues such as 29 missing `agent_job` rows, the single normalized duplicate in `final_results.xlsx`, S2 normalized-title conflicts that are not needed for exact joins, or duplicated/conflicting rows in `agent_dep_job.csv`.

- Add topic-label and topic-score standardization helpers:

```text
standardize_topic_labels_to_english()
rename_topic_score_columns_to_english()
```

- Add exact-title join helpers:

```text
join_s2_content_by_exact_title()
join_article_metadata_by_exact_title()
```

- Normalized-title fallback should be implemented only as a guarded fallback and must write every fallback decision to `join_quality_report.xlsx`.

- Add three master-building workflows:

```text
build_level1_content_master()
build_level2_agent_network_master()
build_level3_agent_topic_match_master()
```

- `build_level2_agent_network_master()` must calculate `article_count_per_agent` from `final_results.xlsx`, create `log_article_count_per_agent`, and create `log_agent_cascade_size_mean`.
- `build_level3_agent_topic_match_master()` must calculate `log_agent_topic_article_n`, create `log_agent_topic_cascade_size_mean`, and aggregate `WordCount`, `HasImage`, `NumImages`, and `CosineSim` to the agent-topic level.

- Add three analysis workflows:

```text
run_level1_content_analysis()
run_level2_agent_network_analysis()
run_level3_agent_topic_matching_analysis()
```

- `run_level2_agent_network_analysis()` must treat `log_agent_cascade_size_mean` as the primary Level 2 dependent variable and report the secondary outcomes separately.
- `run_level2_agent_network_analysis()` must run descriptor diagnostics in explicit blocks: centrality, repeat exposure, and network composition.
- `run_level3_agent_topic_matching_analysis()` must report two separate core matching specifications:
  - Model A with `MatchScore_mean`.
  - Model B with `ProfessionContentMatch_mean`.
- `run_level3_agent_topic_matching_analysis()` must not put `MatchScore_mean` and `ProfessionContentMatch_mean` in the same core regression.
- `run_level3_agent_topic_matching_analysis()` must write correlation and VIF/condition diagnostics for the matching variables and continuous controls.

- Add variable role-map generation:

```text
write_variable_role_map()
```

- Update notebook so it displays results in this order:

```text
Level 1 Content
Level 2 Agent Characteristics
Level 3 Agent-Topic Matching
Integrated Findings
```

- Rewrite `Stage4_Findings_Summary.md` after rerunning the new pipeline.

- Remove or overwrite old mixed-output tables and figures that could be mistaken for current Stage 4 results. At minimum, delete or regenerate:

```text
analysis(S4)/analysis_master.xlsx
analysis(S4)/tables/validation_report.json
analysis(S4)/tables/join_quality_report.xlsx
analysis(S4)/Stage4_Findings_Summary.md
```

The final findings summary must describe the new three-level analysis only.

## Test Plan

Add or update tests in:

```text
analysis(S4)/tests/test_stage4_pipeline.py
```

Required tests:

- `test_no_analysis_master_is_generated`
  - If `analysis(S4)/analysis_master.xlsx` exists before a run, the pipeline should remove it.
  - Pipeline should not write `analysis(S4)/analysis_master.xlsx` after the run.

- `test_source_readiness_report_is_generated_before_masters`
  - The source readiness report exists.
  - It reports all three S3 files and all supporting S2/attribute files.
  - It marks `final_results.xlsx` as requiring S2 content joins.
  - It marks `agent_level_results.xlsx` as requiring agent attribute merges.
  - It marks `agent_topic_level_results.xlsx` as requiring matching aggregation.
  - It reports exact S2 title coverage and normalized-title duplicate conflicts.
  - It reports topic-label standardization from Chinese source labels to English canonical labels.

- `test_variable_role_map_prevents_leakage_confusion`
  - The role map exists.
  - Each variable has exactly one primary role per level.
  - Diffusion-derived descriptors have leakage notes.
  - `MatchScore` and `ProfessionContentMatch` are not allowed as Level 1 predictors.

- `test_level1_content_master_scope`
  - Level 1 has 6,557 rows.
  - Level 1 includes content variables.
  - Level 1 excludes Level 2 aggregation columns such as `cascade_size_mean`, `depth_mean`, and `repeat_exposure_1st_nodes_pct`.
  - Level 1 excludes Level 3 matching variables as core predictors.

- `test_level2_agent_master_scope`
  - Level 2 has one row per agent.
  - Level 2 contains `agent_deg_centrality_mean`, `cascade_size_mean`, `depth_mean`, and `reshare_mean`.
  - Level 2 contains `article_count_per_agent`, `log_article_count_per_agent`, and `log_agent_cascade_size_mean`.
  - Level 2 does not use `TopContentCluster` as a key.
  - Level 2 modeling table excludes or marks as validation-only `matchscore_mean` and `profession_content_match_mean`.

- `test_level3_agent_topic_master_scope`
  - Level 3 key is `agent_name + TopContentCluster`.
  - `TopContentCluster` values are English canonical labels.
  - Level 3 contains agent-topic outcomes.
  - Level 3 contains aggregated matching variables.
  - Level 3 contains `log_agent_topic_cascade_size_mean`.
  - Level 3 contains explicit leakage-safe controls: `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, and `CosineSim_mean`.
  - Level 3 contains sparse-cell flags.

- `test_level3_matching_models_are_separate`
  - The Model A formula contains `MatchScore_mean`.
  - The Model A formula does not contain `ProfessionContentMatch_mean`.
  - The Model B formula contains `ProfessionContentMatch_mean`.
  - The Model B formula does not contain `MatchScore_mean`.

- `test_topic_labels_are_english_canonical`
  - All three master files use English canonical `TopContentCluster` values where a topic column is present.
  - Chinese topic labels do not appear in the modeling `TopContentCluster` column.
  - The topic mapping report contains all six Chinese-to-English mappings.

- `test_exact_title_join_is_primary`
  - S2 content and metadata joins use exact `Title` matches when available.
  - Normalized-title fallback is used only for unmatched titles and only when the fallback key is unique and conflict-free.

- `test_three_level_outputs_exist`
  - Three master files exist.
  - Three analysis workbooks exist.
  - Three-level validation report exists.

- `test_findings_summary_uses_three_level_structure`
  - Findings summary explicitly contains Level 1 Content, Level 2 Agent Characteristics, and Level 3 Agent-Topic Matching.

Keep pytest focused on pipeline safety rather than exhaustive statistical proof. The minimum required pytest scope is:

- legacy `analysis_master.xlsx` deletion and non-regeneration
- source readiness gate
- English canonical topic labels
- exact-title join safety
- level separation and key uniqueness
- Level 2 article-count control and primary DV derivation
- Level 3 separate matching model specifications
- variable role map and leakage flags

Add a notebook validation block at the end of `factor_analysis_stage4.ipynb` for thesis-facing reproducibility:

```python
assert len(df_level1) == 6557
assert set(df_level1["TopContentCluster"].dropna()).issubset({
    "Home Design & Decoration",
    "Real Estate & Architecture",
    "Events & Promotions",
    "Brand & Marketing",
    "Lifestyle & Culture",
    "Customer Service & Management",
})
assert "MatchScore" not in df_level1.columns
assert "ProfessionContentMatch" not in df_level1.columns
assert df_level2["agent_name"].nunique() == 592
assert "article_count_per_agent" in df_level2.columns
assert "log_article_count_per_agent" in df_level2.columns
assert "log_agent_cascade_size_mean" in df_level2.columns
assert "matchscore_mean" not in df_level2.columns
assert "profession_content_match_mean" not in df_level2.columns
assert df_level3[["agent_name", "TopContentCluster"]].duplicated().sum() == 0
assert "log_agent_topic_cascade_size_mean" in df_level3.columns
for col in ["log_agent_topic_article_n", "WordCount_mean", "HasImage_share", "NumImages_mean", "CosineSim_mean"]:
    assert col in df_level3.columns
assert "MatchScore_mean + ProfessionContentMatch_mean" not in " ".join(level3_regression_results["formula"].dropna().astype(str))
assert "standardized_beta" in level1_regression_results.columns
print("All Stage 4 validation checks passed.")
```

Verification commands:

```powershell
.\.venv\Scripts\python.exe -m pytest analysis(S4)\tests -q
.\.venv\Scripts\python.exe analysis(S4)\stage4_pipeline.py
```

## Final Outputs

Expected master files:

```text
analysis(S4)/level1_content_master.xlsx
analysis(S4)/level2_agent_network_master.xlsx
analysis(S4)/level3_agent_topic_match_master.xlsx
```

Expected table files:

```text
analysis(S4)/tables/level1_content_analysis.xlsx
analysis(S4)/tables/level2_agent_network_analysis.xlsx
analysis(S4)/tables/level3_agent_topic_matching_analysis.xlsx
analysis(S4)/tables/three_level_validation_report.json
analysis(S4)/tables/source_readiness_report.xlsx
analysis(S4)/tables/variable_role_map.xlsx
analysis(S4)/tables/join_quality_report.xlsx
analysis(S4)/tables/topic_label_mapping_report.xlsx
```

Expected documentation:

```text
analysis(S4)/Stage4_Findings_Summary.md
analysis(S4)/factor_analysis_stage4.ipynb
```

Expected figure groups:

```text
analysis(S4)/figures/level1_*.png
analysis(S4)/figures/level2_*.png
analysis(S4)/figures/level3_*.png
```

## Assumptions

- Stage 4 is explanatory empirical analysis for a master's thesis, not a formal predictive modeling stage.
- The interim report's three-level framework has priority over the previous mixed-master implementation.
- Agent gender and job variables are already prepared before Stage 4 and should be treated as cleaned agent attributes.
- Level 1 answers content effects only.
- Level 2 answers agent-characteristic associations only; diffusion-derived network metrics are descriptors or supplementary diagnostics.
- Level 3 answers content-agent matching effects.
- English canonical topic labels are the only thesis-facing topic labels in Stage 4 outputs.
- Opportunity matrix belongs to Level 3 only.
- `analysis_master.xlsx` should be deleted and not regenerated.
- Variables derived from the observed diffusion process must not be used as predictors for mechanically related diffusion outcomes without explicit leakage caveats.
- Every finding must state what data were used, how variables were calculated, why the method was used, and what limitations apply.
