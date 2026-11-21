# arXiv submission sheet

Fields to paste into the arXiv submission form. Upload `paper/build/arxiv.tar.gz` after running `./paper/build.sh`; it contains `main.tex`, `main.bbl` and `project-results.png`, and CI confirms it compiles with pdfLaTeX. Regenerate this sheet if the abstract changes: the abstract below is the Markdown abstract with dashes converted to ASCII (1,672 of 1,920 characters).

## Decisions for the project owner

- **Authors.** Decided on 21 November 2026: the Java test collaborator is the second author. Their name and affiliation are still needed. `paper/main.tex` carries the placeholder `[COAUTHOR NAME AND AFFILIATION]`, and `paper/build.sh` refuses to pack the upload until it is replaced. Neither author has an affiliation yet.
- **AI disclosure.** The Limitations section states that OpenAI Codex and Anthropic Claude Code assisted with design, implementation, analysis and drafting. Confirm the wording. arXiv holds the listed authors responsible for the whole submission.
- **License.** Decided on 21 November 2026: CC BY 4.0, which lets others reuse the text with attribution.
- **Endorsement.** A first submission to a category may need an endorsement from an existing arXiv author in that category.

## Metadata

**Title**

Can a small code model predict JVM branch probabilities?

**Primary category:** cs.PL (Programming Languages). The closest prior work, GraalNN and VESPA, appeared at CGO and OOPSLA.

**Cross-lists:** cs.SE, cs.LG

**Comments**

11 pages, 2 tables, 1 figure. Code, data and reproduction scripts: https://github.com/minggu151623/llm_profiling_research

**Abstract**

```text
We ask whether a frozen 0.49B-parameter code model, Qwen2.5-Coder-0.5B-Instruct, can estimate how often a Java bytecode conditional jump is taken from static information alone. Labels come from instrumented execution of 193 original conditional sites in eight upstream Maven libraries, 138 of which ran under each of two constructed workloads. Models, folds and primary contrasts were registered before collection, and each library is held out in turn. Prompted for a 0-9 rating, the model returned a near-constant value between 0.34 and 0.49 whose rank correlation with the measured probability was -0.04. Its macro mean absolute error (MAE) on held-out libraries was 0.424, against 0.429 for a constant 0.5 and 0.325 for a lexical ridge regressor; the paired difference from the lexical model was +0.099 (95% project-bootstrap interval 0.050 to 0.152). A ridge readout of the model's final hidden state reached 0.327, a difference of +0.002 (-0.022 to 0.024) from the lexical model. Its predictions differed from those of the structural ridge that shares its other features by a median of 0.003. Masking identifiers changed the macro MAE of either readout by at most 0.003. Reversing the workload mixture changed the measured probability of 42 sites by more than 0.10, which imposes an error floor of 0.044 on any workload-blind predictor scored on both workloads. On this corpus the evidence does not support using the model's prompted rating or its pooled final state as a branch-probability estimator. Workload identity remains a necessary input for any per-workload claim. An exploratory rerun with the 1.5B checkpoint of the same model family gave the same pattern.
```
