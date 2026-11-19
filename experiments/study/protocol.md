# Protocol registered before study outcomes

## Population and estimand

Study eight independent public Java library repositories through targeted serial API calls. Each project contributes a selected class, original method bytecode and two deterministic stimulus distributions. Distinct upstream repositories define the grouping unit. Normal and shift are names for constructed input families, not estimates of production traffic. The class/method inventory and stimuli are fixed independently of any coverage measurements. The toy Decisions fixture is excluded. Publish inventories, workload definitions, dependency hashes, JDK, observations including zero-support sites, and failure logs.

The same static branch receives exactly one prediction per predictor/fold across workloads. Normalize execution counts within each branch and retain their denominator. Primary endpoint is branch-equal MAE within each test project, followed by the equal-weight mean across held-out projects. Labels never enter a prompt, vocabulary, static representation or sampling rule. SLM inference is local and frozen. No target workload profile is used as a prediction input.

## Models fixed before evaluation

Uniform 0.5, and a backward-taken/forward-not-taken direction heuristic predict benchmarks for basic comparison. Use 1 for a backward jump and 0 for a forward jump in the hard direction rule; these are directional decisions interpreted as endpoints. This is a restricted comparator, not a reproduction of the full Ball–Larus algorithm. Fit structural ridge and XGBoost models to opcode, surrounding opcode counts and relative positions/distances. Test a lexical character n-gram TF–IDF ridge with the same structural features. Class, method, descriptor and original instruction context are available at inference.

For Qwen2.5-Coder-0.5B-Instruct, freeze checkpoint ea3f2471cf1b1f0db85067f1ef93848e38e88c25. Conditional next-token probabilities on digits 0–9 yield the expected digit divided by 9. Compare original identifiers and a deterministic masked representation. Regress measured probability on final prompt hidden-state features plus the same structural features, with and without identifiers. Save per-branch scores and embeddings. All methods use identical sampled, observed sites within each paired evaluation. Select at most 96 static sites per project by ascending SHA-256 of UTF-8 "42:" plus branch ID before checking workload coverage. Report counts before and after sampling, missing representations and zero-support rows.

## Splits, selection and leakage controls

For unseen projects, rotate the test family through all eight projects. Use the next family in the ordered roster as validation and the other six as training. Fit on normal-workload labels only. Score both the normal and shifted workload on the test family. Fit feature transforms on training rows only. Compare ridge alpha in {0.1, 1, 10} and XGBoost maximum depth in {2, 4} at fixed 100 trees, learning rate 0.05. Minimize validation-site MAE; break ties by candidate order. Freeze each fold at the chosen training fit. Clip regressor probabilities to [0, 1]. On the training side, drop matching opcode-sequence method hashes and highly similar local opcode contexts across split boundaries; apply the same rule to validation vs test. Log exclusions including any empty split.

For seen-project/new-workload, fit on the normal workload across all projects and predict the unseen shifted workload. Use the median selected hyperparameter from the normal-workload unseen-project folds (snap to a candidate, ties by candidate order). Quantify the paired label shift for the same compiled site, coverage changes and the lower bound |p_normal - p_shift|/2 on average absolute error of any workload-blind prediction for that site. This bound uses equal workload weights. The seen-project setting can benefit from labels at the same code sites during training and is reported separately.

## Inference and reporting

Report macro MAE, per-execution Brier via counts, execution-weighted MAE, calibration bins, opcode strata, coverage, project-wise paired deltas, and conditional project bootstrap percentile intervals with seed 42 and 10,000 draws. The interval resamples paired test project summaries with models fixed; eight convenience projects do not identify a production population. Give example cases and run logs for computational cost. Primary contrasts compare full zero-shot and full fitted SLM representations against lexical regression. Identify positive and negative cases and report unfavorable model results. No native-image or program-speedup experiment is planned. Model choice, library subset, corpora and workload design limit external validity.

## Responsibility and outputs

The project owner delegated research implementation, experiments, and the draft to Codex; the second team member independently tests Java. Human test results and any publication decision are reported only if actually supplied. Artifacts live under experiments/study; the final manuscript lives under paper. No author list or public preprint submission is inferred from the delegation.
