# Thesis Writing Instructions for Codex

This is a master's thesis LaTeX project.

## Main goals
- Maintain a formal academic writing style.
- Do not invent references, citations, data, tables, or results.
- Preserve the user's original meaning unless explicitly asked to rewrite.
- Keep LaTeX clean and compilable.
- Avoid unnecessary changes outside the requested file or section.

## Project-specific focus
- This thesis is connected to the user's local Stage 1-4 research analysis outputs.
- Current writing emphasis should be placed on the thesis's methodological and empirical core, wherever these materials ultimately appear in the final chapter structure.
- The priority materials are: methodology, implementation details, empirical results, discussion of results, and conclusions drawn from the analysis.
- The DASE 7099 final report guideline PDF is a formatting and presentation guide. Its sample chapter titles and table-of-contents entries are examples only; do not copy them into this thesis unless the user explicitly asks.
- Detailed final report requirements are summarized in `notes/final_report_requirements.md`.
- Chapter numbering and chapter boundaries are provisional; do not assume these materials must remain in Chapter 3 or Chapter 4.
- Treat interim findings as provisional unless the user explicitly says they are final.
- Do not convert exploratory notes or intermediate analysis outputs into thesis claims unless the user asks.
- If chapter numbering or filenames differ from the user's requested chapter structure, ask before moving content between chapters.
- For Stage 4, treat reconstructed cascade and diffusion-network measures such as centrality, depth, structural virality, and Wiener index as primary or supplementary dependent variables that represent diffusion effectiveness dimensions. Do not describe them as ordinary ex-ante predictors of reach.
- Explain that Level 1, Level 2, and Level 3 use different supplementary outcomes because their units of analysis differ: article-agent cases, agents, and agent-topic pairs.
- Do not write centrality-class network-position outcomes as Level 1 dependent variables. Use them only at Level 2 or Level 3, where the agent or agent-topic unit gives them a coherent interpretation.

## Writing style
- Use clear, formal, concise academic English.
- Avoid overusing the structure "not only ... but also ...".
- Avoid overly long sentences.
- Do not add unsupported claims.
- When improving paragraphs, focus on logic, coherence, and flow.
- Do not overbuild the literature review at the expense of the empirical core. Literature should motivate the study, define the research gap, and support the methodology, but the final report should place more weight on methodology, implementation, results, discussion, and conclusion.
- Results writing should separate: what was done, what was found, how to interpret it, what the limitations are, and what conclusion can be drawn.

## Final report format guide
- Use the DASE 7099 guideline as a format reference, not as a required thesis outline.
- Expected front matter sequence: title page, abstract, declaration, optional acknowledgements, table of contents, list of figures, and list of tables.
- The title page should include university/department, programme, dissertation/final report label, thesis title, student name and number if required, supervisor, and submission date.
- The declaration page should state that the report is the student's own work and has not been submitted elsewhere, with signature/name/date fields.
- Abstract target length: about 400-500 words. It should summarize the report accurately, including major results, conclusions or recommendations, and only the necessary method, scope, and purpose details.
- The abstract page should not show a page number. Front matter after the abstract should use roman numerals. Chapter 1 should restart at Arabic page 1.
- Page margins should follow the guideline's 25 mm margins on all sides unless the university template or user requests a different setting.
- Body text should use 12 pt font. Chapter headings may follow the template's 12-14 pt style.
- Use clear paragraph indentation and follow the final template's line-spacing convention; if no later template overrides it, use double or spacious line spacing.
- Keep subsection depth reasonable. Avoid very deep numbering such as 3.6.1.1.1.
- Number figures, tables, and equations by chapter, such as Figure 1.1, Table 3.1, and equation (3.14).
- Figure captions should be placed below figures. Table titles should be placed above tables.
- Treat table and figure captions as titles; avoid a final full stop unless the title is a complete sentence or a local style rule requires it.
- Add table notes or legends below tables when symbols, arrows, abbreviations, or special notation are used.
- Bibliography should follow the conclusion. Appendices should follow the bibliography.
- Add a publications page after appendices only if relevant; otherwise omit it.
- The conclusion chapter should include main achievements/findings, contributions or practical implications, limitations, and directions for future work.

## Terminology rules
- Preserve project terminology consistently.
- Preferred terms include: risk event, loss severity, aggregate loss, factor analysis, Stage 4.
- Do not introduce alternative terms unless requested.

## Data and results rules
- Do not invent datasets, coefficients, tables, figures, model outputs, statistical significance, robustness checks, or causal claims.
- Use analysis outputs only when explicitly provided or referenced by the user.
- If a result is missing, mark it as [result needed] instead of guessing.
- Distinguish clearly between observed results, interpretation, limitations, and future work.

## Citation rules
- Every empirical, factual, or theoretical claim should have a citation if it is not the user's own analysis.
- Do not create fake references.
- Use existing keys from references.bib when possible.
- If a citation is missing, mark it as [citation needed] instead of inventing one.

## LaTeX rules
- Main file: main.tex
- Chapter files are in chapters/
- Figures are in figures/
- Tables are in tables/
- References are in references.bib
- Do not change the document structure unless asked.
- After editing LaTeX, check for syntax errors.
- Preferred local build chain: pdflatex -> biber -> pdflatex -> pdflatex.
- Do not assume latexmk is available unless the user says the local TeX environment has changed.

## Preferred workflow
1. Read the relevant chapter file.
2. Make targeted edits only.
3. Explain what was changed.
4. If there are unresolved issues, list them clearly.
