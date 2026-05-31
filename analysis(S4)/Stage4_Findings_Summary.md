# Stage 4 Findings Summary

Generated: 2026-05-31T16:23:06

## Research question

Stage 4 answers two linked questions. First, do content factors, agent/network factors, and content-agent matching factors relate to diffusion performance? Second, if they do, which specific factors matter most after keeping the three analytical levels separate?

## Data Construction

Stage 4 follows the three-level framework from the interim report.

- Level 1 content master: 6,557 article-agent diffusion cases. Data used: `final_results.xlsx`, S2 content features, S2 article metadata, and corrected diffusion layers. Primary DV: `log_reach = log1p(cascade_size)`, with duration, reshare, virality, and count outcomes used as additional outcomes.
- Level 2 agent/network master: 592 agents. Data used: `agent_level_results.xlsx`, existing S3 `JobCategory`, prepared gender, job, and department attributes. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`.
- Level 3 agent-topic matching master: 1,142 agent-topic rows. Data used: `agent_topic_level_results.xlsx`, article-agent matching scores from `final_results.xlsx`, S2 content controls, and agent attributes. Primary DV: `log_agent_topic_cascade_size_mean = log1p(cascade_size_mean)`.

All topic labels are standardized to English canonical labels. `analysis_master.xlsx` is not used. Complete-case model samples may be smaller than master row counts when a model variable is missing; main model n ranges are reported below.

## Leakage control

Diffusion-derived variables are treated as outcomes or mechanism descriptors, not ordinary leakage-free predictors. Level 1 excludes matching and agent/network variables. Level 2 excludes content-agent matching aggregates. Level 3 uses matching variables plus leakage-safe content/exposure controls, and does not use realized diffusion descriptors as ordinary controls.

## Level 1 Content

Why calculated: Level 1 tests whether content characteristics are associated with diffusion outcomes without adding matching variables.

Method: content topic, topic scores, `CosineSim`, `WordCount`, `HasImage`, and `NumImages` are joined by exact article `Title`. Main models use `TopContentCluster` as a categorical predictor and content metadata as controls. Controls: `CosineSim`, `WordCount`, `HasImage`, and `NumImages`; alternative distance controls are used only in robustness checks. The six topic-score columns are not entered together with topic dummies in the main model; they are used only in robustness specifications. Main complete-case n: 6,556.

Key model signal: `z_CosineSim` on `log_reach`: coef=0.146, standardized beta=0.146, p=3.67e-22.

Interpretation: a positive `z_CosineSim` coefficient means title-content semantic consistency is associated with higher diffusion; a negative coefficient would indicate that more semantic distance is associated with weaker diffusion. Standardized beta values are used to compare continuous predictors measured on different scales.

Robustness added: 6 five-topic-score models, 6 topic-PCA models, and 12 alternative-distance models.

## Level 2 Agent / Network

Why calculated: Level 2 tests whether agent roles and network position are associated with overall diffusion capability.

Method: one row per agent. Primary DV: `log_agent_cascade_size_mean = log1p(cascade_size_mean)`. Controls: `JobCategory`, `agent_gender`, and `log_article_count_per_agent` in the core model. `article_count_per_agent` is calculated from `final_results.xlsx` and used as a stability/opportunity control. Main complete-case n: 592.

Role/gender model signal: No coefficient in this block is below p<0.05; strongest observed term is `C(JobCategory)[T.1]` on `log_agent_cascade_size_mean`: coef=1.436, p=0.767.

Interpretation of role category: JobCategory is not statistically significant in the current Level 2 core model, so the thesis should report this as evidence that formal role category alone does not explain average diffusion capability. This is substantively useful because it shifts the Level 2 explanation toward network position and exposure rather than job labels.

Centrality mechanism signal: `z_agent_deg_centrality_mean` on `log_agent_cascade_size_mean`: coef=0.375, standardized beta=0.375, p=2.09e-09.

Interpretation: role/gender coefficients describe group differences in average agent diffusion capability, while centrality and repeat-exposure blocks are mechanism associations. They are not interpreted as causal effects because they are derived from observed diffusion/network structure.

Robustness added: 6 core models without the article-count control.

## Level 3 Content-Agent Matching

Why calculated: Level 3 directly tests the thesis claim that one content strategy does not fit all agents or roles.

Method: one row per agent and English `TopContentCluster`. `MatchScore_mean` and `ProfessionContentMatch_mean` are aggregated from article-agent rows, but they are estimated in separate core models to avoid collinearity and interpretation problems. Controls: `TopContentCluster`, `JobCategory`, `agent_gender`, `log_agent_topic_article_n`, `WordCount_mean`, `HasImage_share`, `NumImages_mean`, and `CosineSim_mean`. Main complete-case n: 1,142.

Key continuous matching signal: `z_MatchScore_mean` on `log_agent_topic_cascade_size_mean`: coef=0.260, standardized beta=0.260, p=3.9e-07.

Key binary/proportion matching signal: `z_ProfessionContentMatch_mean` on `log_agent_topic_cascade_size_mean`: coef=0.085, standardized beta=0.085, p=0.0468.

Moderation signal: `z_MatchScore_mean:z_agent_deg_centrality_mean` on `log_agent_topic_cascade_size_mean`: coef=-0.331, standardized beta=-0.331, p=2.88e-14.

Interpretation: a positive matching coefficient means better content-agent fit is associated with stronger diffusion for that agent-topic combination. The moderation model asks whether agent network centrality changes the value of matching; it is reported only after Level 2 supports centrality relevance. In the current run the moderation coefficient is negative, which means high-centrality agents gain less from matching while lower-centrality agents rely more on fit to compensate for weaker network position.

Sparse-cell note: weighted models use `agent_topic_article_n` as precision/exposure weights, and sensitivity models exclude very sparse cells. 126 of 1142 agent-topic pairs have n>=10; 46 have n>=30.

## Limitations

The analysis is explanatory and associational. Standardized beta is useful for comparing continuous predictors, but categorical coefficients should be interpreted relative to their reference groups. Diffusion-derived descriptors are treated as outcomes or mechanism descriptors, not leakage-free causal predictors. Sparse-cell Level 3 evidence should be interpreted cautiously, especially for individual agent-topic pairs.
