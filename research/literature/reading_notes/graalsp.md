# GraalSP

## Author claims and evidence

Milan Čugurović, Milena Vujošević Janičić, Vojin Jovanović and Thomas Würthinger published *GraalSP: Polyglot, efficient, and robust machine learning-based static profiler* in the *Journal of Systems and Software*, volume 213, article 112058 (2024). [Publisher](https://doi.org/10.1016/j.jss.2024.112058) · [University record](https://research.matf.bg.ac.rs/handle/123456789/1585)

- **Target and method.** Section 3 predicts the probability of the first successor of a binary Graal IR control split. The second receives its complement. Multiway splits receive uniform probabilities. An XGBoost regressor uses graph-derived features including control flow and estimated code costs. Heuristics adjust predictions. Section 4 identifies the integration as Graal compiler 23.0. [Article, §§3–4](https://www.sciencedirect.com/science/article/pii/S0164121224001031)
- **Evaluation.** Section 5 examines model quality and the compiled program's runtime, binary size and compilation time. The authors report a 7.46% geometric-mean runtime speedup over a uniform-branch-probability build on 28 benchmarks. The suites were Renaissance, DaCapo and DaCapo con Scala. The first author also describes the extra binary size arising from compiler optimizations. [Article, introduction and §5](https://doi.org/10.1016/j.jss.2024.112058) · [First author's explanation, Fig. 5](https://medium.com/graalvm/machine-learning-driven-static-profiling-for-native-image-d7fc13bb04e2)

## Interpretation for this project

GraalSP establishes a direct precedent for predicting branch probabilities with structural features. A paired comparison needs an explicit mapping from the Graal IR successor to the original bytecode jump target, including whether to complement the probability. Its published runtime result belongs to an end-to-end compiler experiment. Our branch-level MAE or Brier measurements answer a different question. [Article, §§3–5](https://doi.org/10.1016/j.jss.2024.112058)

## Verification limits

We inspected the publisher's public article excerpts for §§3–5 and corroborated the evaluation with first-author material. Access to the complete journal text and its tables was unavailable during this review. The exact benchmark JDK vendor/build, independent downloadable training rows and reproduction package remain **UNVERIFIED**. Version 23.0 identifies the compiler integration. The release supporting JDK 17 and 20 does not identify which build ran the paper's experiments. [First author's deployment description](https://medium.com/graalvm/machine-learning-driven-static-profiling-for-native-image-d7fc13bb04e2) · [Publisher](https://doi.org/10.1016/j.jss.2024.112058)

The first author's later dissertation corroborates the 28-benchmark evaluation and XGBoost design. Section 6.2, printed p. 62 (PDF p. 74), specifies Enterprise GraalVM Native Image 23.0 based on Java 17, Oracle Linux Server 7.4 and Serial GC for the thesis evaluation. We could verify this later account in full. The exact journal-run JDK patch/build and whether every configuration matched the thesis are **UNVERIFIED**. [Dissertation, §6.2](https://uvidok.rcub.bg.ac.rs/bitstream/handle/123456789/6474/Doktorat.pdf?isAllowed=y&sequence=2#page=74)

## Model-level error reported in the dissertation

The journal article was not accessible in full on 21 November 2026: ScienceDirect returned HTTP 403 and the university record holds only the abstract. The first author's dissertation is openly available and was read in full text. It reports the following for the GraalSP regressor. These are the dissertation's numbers, not a confirmed copy of the journal tables. [Dissertation PDF](https://uvidok.rcub.bg.ac.rs/bitstream/handle/123456789/6474/Doktorat.pdf?isAllowed=y&sequence=2) · [Repository record](https://uvidok.rcub.bg.ac.rs/handle/123456789/6474)

- **Training data.** 323,350 branch instructions from the newest version of each of 44 Java libraries in the GraalVM Reachability Metadata repository. Each instruction is labelled with the probability of its first successor. Branches that correspond to bytecode exceptions are excluded. Hyperparameters were chosen by cross-validation for the tree models and on a random 10% split for the neural network. (§5.1 and Table 5.1, printed pp. 53–55)
- **Labels.** Training labels have mean 0.473 and standard deviation 0.458. For 18.39% of branches the first-successor frequency is not close to 0 or 1, which the author gives as the reason for using regression. (Table 5.2 and Fig. 5.2, pp. 55–56)
- **Weights.** Each branch is weighted by its share of all branch executions in its program, so the weights in one program sum to one. (§4.2, printed p. 49)
- **Held-out error.** The test set is the Native Image benchmark programs (Renaissance, DaCapo 9.12, DaCapo con Scala), which the footnote to §5.1 states is fully separate from the training and validation data. Table 6.2 (p. 70) reports test RMSE 0.2989 and R² 0.5512 for XGBoost, against 0.3510 / 0.3812 for a decision tree and 0.3230 / 0.4758 for a deep neural network. The table does not say whether RMSE is weighted. By suite, XGBoost error is 0.2950 on DaCapo and 0.3038 on DaCapo con Scala (§6.4, p. 68).
- **Setup.** Enterprise GraalVM Native Image 23.0 on Java 17, Oracle Linux Server 7.4, Serial GC, two Intel E5-2699 CPUs per node (§6.2, p. 62).

## Bearing on our comparison

The dissertation does supply a branch-level held-out error, so our related-work text should not say that GraalSP reports only compiler speedups. The figure still does not serve as a reference error for our sites. It is measured on Graal IR splits after parsing, on different programs and workloads, with a training set roughly 2,300 times larger than ours, and possibly with execution weighting. For scale only: on our 138 observed normal-workload sites, the pooled unweighted RMSE is 0.381 for our structural XGBoost and 0.442 for the constant 0.5 (`experiments/study/evaluation/predictions.csv`, unseen setting).
