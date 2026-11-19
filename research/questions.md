# Research questions and measurement protocol

The observable for one workload is the measured probability of the original bytecode jump. At inference time the same bytecode and static metadata yield the same inputs under every workload. Both researchers should agree on the target workload population and aggregation weights before using this protocol for a paper. [Original brief](../CODEX_RESEARCH_BRIEF_SLM_JVM_BRANCH_PROFILING.md)

| Question | Planned comparison | Unit and split |
| --- | --- | --- |
| RQ1. Does an SLM improve branch probability estimates? | Compare zero/few-shot SLM predictions to a uniform reference, documented control-flow heuristics and structural regression. Verify original heuristic sources before implementation. | Same observed branch/workload pairs for every predictor |
| RQ2. How much do static names contribute? | Structural-only vs structural + lexical features, SLM with names vs masked/renamed names, and SLM representations + regression. Fix examples, masking rule and decoding parameters. | Paired comparisons within held-out projects, broken down by opcode and support |
| RQ3. Do gains transfer across projects? | Deduplicate shared dependencies and similar methods across folds before fitting a model, vocabulary or scaler. Select prompts and hyperparameters on validation projects. | Entire projects held out; record project and fork-family lists in a split manifest |
| RQ4. How much do probabilities shift when inputs change? | Hold the compiled artifact, BCI and static prediction fixed. Measure label and error changes, including coverage on each workload. | Seen project with a held-out workload. Report separately from unseen-project tests |

## Frozen split rules

For unseen-project evaluation, assign each project and its fork family to exactly one of train, validation or test. All branches and workloads of each member travel together. Resolve shared library and near-duplicate code before fitting any feature transform. For seen-project/new-workload evaluation, hold out entire workload IDs within a seen project and compare the same original branch across workloads. Reserve the held-out labels for final evaluation. Keep the two evaluations in separate reports.

The current single-project fixture is reserved for pipeline checks. Once benchmark projects and workloads are selected, record their actual assignments in a versioned manifest before model fitting.

## Metrics

Report per-site MAE on measured proportions. For Brier score on individual executions use `(taken*(1-q)^2 + fallthrough*q^2)/(taken+fallthrough)` for prediction `q`. Squared error against a measured proportion omits within-site outcome variance. Report macro and execution-weighted summaries with their denominators, reliability plots, unobserved counts and failures. Bootstrap projects for cross-project intervals and paired workload groups where supported. One pilot project cannot support project-level uncertainty intervals.

The working hypothesis is that static names help on some guards. Class frequency, label noise, workload shift, duplicate library code and inference cost could erase an apparent advantage. Keep negative results, document model revision/license, and distinguish label accuracy from program throughput. [Evidence matrix](literature/evidence_matrix.csv) · [Novelty map](literature/novelty_map.md)
