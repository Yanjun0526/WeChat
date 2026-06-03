# Writing Log

## 2026-06-01

Today's target:
- Draft the section headings for Chapter 1.
- Confirm the thesis structure.
- Set up LaTeX compilation.

Questions:
- Is the research gap clear?
- Does the introduction connect to the model and data?

## Writing Style Requirement

Future thesis writing should use the Dissertation Proposal and Interim Report as style references. The writing should preserve the author's existing tone: clear, direct, explanatory, moderately formal, and problem-driven. Revisions may improve grammar, coherence, academic precision, and final-paper maturity, but should not over-polish the text into an overly native-speaker or journal-style voice. The dissertation should keep the sentence rhythm, cautious wording, and practical motivation already established in the proposal and interim report. Empirical claims should remain measured and associational unless a causal identification strategy is explicitly provided.

## Data And Modeling Notes

Level 2 should be framed as an agent-characteristic level, not as a clean network-structure predictor model. Agents are embedded sharers and origin points in the social marketing network, so their observable features can proxy local audience and sharing context. Reconstructed network metrics such as centrality, Wiener index, structural virality, repeat exposure, width, and depth are diffusion-pattern descriptors or secondary diffusion outcomes. They help describe observed diffusion heterogeneity, but should not be written as ex-ante causal predictors. When discussing Level 2, use phrases such as "agent characteristics are associated with observed average diffusion patterns" and "reconstructed network metrics describe diffusion-pattern heterogeneity."

The thesis should explicitly mention the Level 1 sample-size difference between the master file and the main regression. The Level 1 content master contains 6,557 article-agent cases, while the main Level 1 regression uses 6,556 complete cases. The one excluded observation is the article-agent case for agent `谢巧` and article title `噢噢噢`. It is excluded because `CosineSim` is missing, while the other main-model variables (`log_reach`, `TopContentCluster`, `WordCount`, `HasImage`, and `NumImages`) are complete. The article has only 16 words, no image, and no image count, so the missing `CosineSim` should be described as a case where title-content semantic similarity could not be computed. Use "complete-case deletion" or "listwise deletion", not "column deletion".
