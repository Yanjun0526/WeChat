# Stage 4 Findings Summary

Generated: 2026-05-31T22:31:36

## Research question

Stage 4 answers two linked questions. First, do content factors, agent/network factors, and content-agent matching factors relate to diffusion performance? Second, if they do, which specific factors matter most after keeping the three analytical levels separate?

The empirical logic is deliberately sequential. Level 1 asks whether the article itself matters. Level 2 asks whether the agent and network position matter. Level 3 then asks whether the fit between a specific agent and a specific content topic matters after the first two layers are understood. This sequence supports the thesis claim that marketing diffusion is not a one-size-fits-all problem.

## Step-by-step workflow

### Step 1 - Source readiness precheck

What this step does: before any modeling, the pipeline checks whether the required source files exist and whether they contain the keys and variables needed for Stage 4. The checked sources are `diffusion(S3)/final_results.xlsx`, `diffusion(S3)/agent_level_results.xlsx`, `diffusion(S3)/agent_topic_level_results.xlsx`, `diffusion(S3)/diffusion_corrected_layers.xlsx`, `batch_outputs(S2)/filtered2_results_clustered_all(translated).xlsx`, `batch_outputs(S2)/filtered_results_all_cleaned.xlsx`, `diffusion(S3)/unique_agentsgender.xlsx`, and `diffusion(S3)/agent_dep_job.csv`.

Why this step matters: Stage 4 combines outputs from S2 and S3. If titles, agent names, topic labels, or diffusion metrics are missing or duplicated, the later regressions may look clean but be built on broken joins. This precheck forces the analysis to report missingness, duplicate keys, role/category conflicts, and topic-label standardization issues before results are interpreted.

Output: `analysis(S4)/tables/source_readiness_report.xlsx`.

How to read the output: use this file as a data audit trail. A source file should have the expected row count, required keys, and required outcome inputs. Warnings in this report should be described as data limitations, not hidden.

### Step 2 - Build separate level-specific master files

What this step does: Stage 4 creates three separate master files rather than one mixed `analysis_master.xlsx`.

- Level 1 content master: 6,557 article-agent diffusion cases. Data used: `final_results.xlsx`, S2 content features, S2 article metadata, and corrected diffusion layers. Primary DV: `log_reach = log1p(cascade_size)`, with duration, reshare, depth, and virality outcomes used as additional outcomes.
- Level 2 agent/network master: 592 agents. Data used: `agent_level_results.xlsx`, existing S3 `JobCategory`, prepared gender, job, and department attributes. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`.
- Level 3 agent-topic matching master: 1,142 agent-topic rows. Data used: `agent_topic_level_results.xlsx`, article-agent matching scores from `final_results.xlsx`, S2 content controls, and agent attributes. Primary DV: `log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)`.

Why this step matters: each analytical level has a different unit of observation. Level 1 is article-agent, Level 2 is agent, and Level 3 is agent-topic. Mixing them into one table would blur the meaning of a coefficient and increase leakage risk.

Output: `analysis(S4)/level1_content_master.xlsx`, `analysis(S4)/level2_agent_network_master.xlsx`, and `analysis(S4)/level3_agent_topic_match_master.xlsx`.

How to read the output: each master file should be interpreted only at its own level. A Level 1 row is not directly comparable with a Level 2 row, because the dependent variable and unit of analysis are different.

### Step 3 - Standardize topic labels

What this step does: topic labels from Stage 2 and Stage 3 are converted into the English canonical labels used throughout Stage 4: `Home Design & Decoration`, `Real Estate & Architecture`, `Events & Promotions`, `Brand & Marketing`, `Lifestyle & Culture`, and `Customer Service & Management`.

Why this step matters: some source files store Chinese topic labels and some store English translated topic labels. If the labels are not standardized before joining and modeling, the same topic can be treated as two different categories.

Output: `analysis(S4)/tables/topic_label_mapping_report.xlsx` and the topic-label sheets inside `analysis(S4)/tables/join_quality_report.xlsx`.

How to read the output: unmapped labels or mixed-language labels should be treated as data-cleaning problems. In the current Stage 4 outputs, modeling columns use English canonical topic labels.

### Step 4 - Assign variable roles before modeling

What this step does: every major variable is assigned a role such as outcome, content predictor, agent attribute predictor, matching predictor, mechanism descriptor, control, or validation-only field.

Why this step matters: diffusion-derived variables can be tempting to use as predictors, but many of them are calculated from the same diffusion process as the dependent variables. Treating them as ordinary predictors can create post-treatment leakage. The role map keeps the analysis honest by specifying which variables can be used as predictors, which can be outcomes, and which should only be descriptive or validation fields.

Output: `analysis(S4)/tables/variable_role_map.xlsx`.

How to read the output: this file explains why, for example, `MatchScore_mean` belongs in Level 3 rather than Level 1, and why centrality is interpreted as a mechanism descriptor rather than a clean causal treatment.

Thesis wording: describe these models as associational. Use words like "is associated with", "is related to", and "is consistent with" rather than causal wording such as "causes" or "affects" unless a causal identification strategy is added.

### Step 5 - Run Level 1 content analysis

What this step does: Level 1 tests whether article content characteristics are associated with diffusion outcomes without adding agent-network or matching variables. Content topic, topic scores, `CosineSim`, `WordCount`, `HasImage`, and `NumImages` are joined by exact article `Title`. Main models use `TopContentCluster` as a categorical predictor and content metadata as controls.

Why this step matters: this is the content-only baseline. It answers whether articles with different content characteristics diffuse differently before asking whether agents or matching explain additional variation.

Output: `analysis(S4)/tables/level1_content_analysis.xlsx` and Level 1 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is 6,556. Continuous predictors are standardized, so Standardized beta values can be compared across continuous predictors. Categorical topic coefficients are interpreted relative to the reference topic.

Key model signal: `z_CosineSim` on `log_reach`: coef=0.146, standardized beta=0.146, p=3.67e-22.

Interpretation: a positive `z_CosineSim` coefficient means title-content semantic consistency is associated with higher diffusion. A negative coefficient would mean semantic distance is associated with weaker diffusion. In thesis wording, this supports the idea that content quality/consistency matters, but it does not by itself prove causality.

Robustness: the pipeline adds 6 five-topic-score models, 6 topic-PCA models, and 12 alternative-distance models.

### Step 6 - Run Level 2 agent/network analysis

What this step does: Level 2 tests whether agent role, agent attributes, and network position are associated with average diffusion capability. The unit is one row per agent. The core model uses `JobCategory`, `agent_gender`, and `log_article_count_per_agent`; additional mechanism blocks examine centrality, repeat exposure, and network composition.

Why this step matters: even good content may diffuse differently depending on who shares it. Level 2 separates overall agent capability and network opportunity from the content-only story.

Output: `analysis(S4)/tables/level2_agent_network_analysis.xlsx` and Level 2 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is 592. Role/gender coefficients describe group differences in average diffusion capability. Centrality and repeat-exposure results are mechanism associations because they are derived from observed network/diffusion structure.

Role/gender model signal: No coefficient in this block is below p<0.05; strongest observed term is `C(JobCategory)[T.1]` on `log_agent_cascade_size_mean`: coef=1.436, p=0.767.

Interpretation of role category: JobCategory is not statistically significant in the current Level 2 core model, so the thesis should report this as evidence that formal role category alone does not explain average diffusion capability. This is substantively useful because it shifts the Level 2 explanation toward network position and exposure rather than job labels.

Centrality mechanism signal: `z_agent_deg_centrality_mean` on `log_agent_cascade_size_mean`: coef=0.375, standardized beta=0.375, p=2.09e-09.

Thesis wording: say that more central agents are associated with stronger average diffusion, while noting that centrality is not randomly assigned and should not be interpreted as a causal treatment.

Robustness: the pipeline adds 6 core models without the article-count control.

### Step 7 - Run Level 3 content-agent matching analysis

What this step does: Level 3 tests whether content-agent fit is associated with diffusion for each agent-topic combination. The unit is one row per agent and English `TopContentCluster`. `MatchScore_mean` and `ProfessionContentMatch_mean` are aggregated from article-agent rows, but they are estimated in separate core models to avoid collinearity and interpretation problems.

Why this step matters: this is the direct empirical test of the "one size does not fit all" thesis. It asks whether the same content category performs differently depending on the agent's topical/job fit and network position.

Output: `analysis(S4)/tables/level3_agent_topic_matching_analysis.xlsx` and Level 3 figures in `analysis(S4)/figures/`.

How to read the output: the main complete-case n is 1,142. `MatchScore_mean` captures continuous content-agent fit. `ProfessionContentMatch_mean` captures the share or intensity of profession-content match. Weighted models use `agent_topic_article_n` as precision/exposure weights, and sparse-cell sensitivity models check whether findings depend on very small agent-topic cells.

Key continuous matching signal: `z_MatchScore_mean` on `log_agent_topic_cascade_size_mean`: coef=0.260, standardized beta=0.260, p=3.9e-07.

Key binary/proportion matching signal: `z_ProfessionContentMatch_mean` on `log_agent_topic_cascade_size_mean`: coef=0.085, standardized beta=0.085, p=0.0468.

Moderation signal: `z_MatchScore_mean:z_agent_deg_centrality_mean` on `log_agent_topic_cascade_size_mean`: coef=-0.331, standardized beta=-0.331, p=2.88e-14.

Interpretation: a positive matching coefficient means better content-agent fit is associated with stronger diffusion for that agent-topic combination. The moderation model asks whether agent network centrality changes the value of matching; it is reported only after Level 2 supports centrality relevance. In the current run the moderation coefficient is negative, which means high-centrality agents gain less from matching while lower-centrality agents rely more on fit to compensate for weaker network position.

Sparse-cell note: 126 of 1142 agent-topic pairs have n>=10; 46 have n>=30.

Thesis wording: this level supports the managerial implication that personalized content assignment may matter. Lower-centrality agents may need better content-topic fit to compensate for weaker network position, while high-centrality agents may diffuse content more broadly even when fit is weaker.

### Step 8 - Generate tables, figures, validation files, and notebook

What this step does: after the three models are built, the pipeline writes master files, Excel model tables, join-quality reports, validation JSON, figures, this findings summary, and a notebook for inspection.

Why this step matters: the outputs are designed to make the analysis reproducible and readable. The Excel files preserve model details; the figures provide thesis-facing visual summaries; the notebook offers a quick way to reload and inspect results.

Output: `analysis(S4)/tables/*.xlsx`, `analysis(S4)/figures/*.png`, `analysis(S4)/tables/three_level_validation_report.json`, `analysis(S4)/Stage4_Findings_Summary.md`, and `analysis(S4)/factor_analysis_stage4.ipynb`.

How to read the output: start with this findings file, then inspect the three level-specific Excel analysis files for exact coefficients, sample sizes, and robustness checks. Use the figures for presentation and thesis narrative, but cite the tables for exact values.

## Data Construction

Stage 4 follows the three-level framework from the interim report. All topic labels are standardized to English canonical labels. `analysis_master.xlsx` is not used. Complete-case model samples may be smaller than master row counts when a model variable is missing; main model n ranges are reported above.

## Leakage control

Diffusion-derived variables are treated as outcomes or mechanism descriptors, not ordinary leakage-free predictors. Level 1 excludes matching and agent/network variables. Level 2 excludes content-agent matching aggregates. Level 3 uses matching variables plus leakage-safe content/exposure controls, and does not use realized diffusion descriptors as ordinary controls.

## Main interpretation by level

### Level 1 Content

Why calculated: Level 1 tests whether content characteristics are associated with diffusion outcomes without adding matching variables.

Method: content topic, topic scores, `CosineSim`, `WordCount`, `HasImage`, and `NumImages` are joined by exact article `Title`. Main models use `TopContentCluster` as a categorical predictor and content metadata as controls. Controls: `CosineSim`, `WordCount`, `HasImage`, and `NumImages`; alternative distance controls are used only in robustness checks. The six topic-score columns are not entered together with topic dummies in the main model; they are used only in robustness specifications. Main complete-case n: 6,556.

Key model signal: `z_CosineSim` on `log_reach`: coef=0.146, standardized beta=0.146, p=3.67e-22.

Interpretation: a positive `z_CosineSim` coefficient means title-content semantic consistency is associated with higher diffusion; a negative coefficient would indicate that more semantic distance is associated with weaker diffusion. Standardized beta values are used to compare continuous predictors measured on different scales.

### Level 2 Agent / Network

Why calculated: Level 2 tests whether agent roles and network position are associated with overall diffusion capability.

Method: one row per agent. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`. Controls: `JobCategory`, `agent_gender`, and `log_article_count_per_agent` in the core model. `article_count_per_agent` is calculated from `final_results.xlsx` and used as a stability/opportunity control. Main complete-case n: 592.

Role/gender model signal: No coefficient in this block is below p<0.05; strongest observed term is `C(JobCategory)[T.1]` on `log_agent_cascade_size_mean`: coef=1.436, p=0.767.

Centrality mechanism signal: `z_agent_deg_centrality_mean` on `log_agent_cascade_size_mean`: coef=0.375, standardized beta=0.375, p=2.09e-09.

Interpretation: role/gender coefficients describe group differences in average agent diffusion capability, while centrality and repeat-exposure blocks are mechanism associations. They are not interpreted as causal effects because they are derived from observed diffusion/network structure.

### Level 3 Content-Agent Matching

Why calculated: Level 3 directly tests the thesis claim that one content strategy does not fit all agents or roles.

Method: one row per agent and English `TopContentCluster`. `MatchScore_mean` and `ProfessionContentMatch_mean` are aggregated from article-agent rows, but they are estimated in separate core models to avoid collinearity and interpretation problems. Controls: `TopContentCluster`, `JobCategory`, `agent_gender`, `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, and `CosineSim_mean`. Main complete-case n: 1,142.

Key continuous matching signal: `z_MatchScore_mean` on `log_agent_topic_cascade_size_mean`: coef=0.260, standardized beta=0.260, p=3.9e-07.

Key binary/proportion matching signal: `z_ProfessionContentMatch_mean` on `log_agent_topic_cascade_size_mean`: coef=0.085, standardized beta=0.085, p=0.0468.

Moderation signal: `z_MatchScore_mean:z_agent_deg_centrality_mean` on `log_agent_topic_cascade_size_mean`: coef=-0.331, standardized beta=-0.331, p=2.88e-14.

Interpretation: a positive matching coefficient means better content-agent fit is associated with stronger diffusion for that agent-topic combination. In the current run the moderation coefficient is negative, which means high-centrality agents gain less from matching while lower-centrality agents rely more on fit to compensate for weaker network position.

## Limitations

The analysis is explanatory and associational. Standardized beta is useful for comparing continuous predictors, but categorical coefficients should be interpreted relative to their reference groups. Diffusion-derived descriptors are treated as outcomes or mechanism descriptors, not leakage-free causal predictors. Sparse-cell Level 3 evidence should be interpreted cautiously, especially for individual agent-topic pairs.
