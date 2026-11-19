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
