# GraalNN

## What did the authors predict?

Lazar Milikic, Milan Cugurovic and Vojin Jovanovic published *GraalNN: Context-Sensitive Static Profiling with Graph Neural Networks* at CGO 2025, pp. 123–136. Section numbers below refer to the Oracle Labs full text. [Publisher DOI](https://doi.org/10.1145/3696443.3708958) · [Crossref publication record](https://api.crossref.org/works/10.1145/3696443.3708958)

**Author claims.** GraalNN estimates the probability of the true successor at a Graal IR `If` node. GraphSAGE encodes basic blocks using IR node histograms, compiler cost estimates and structural features. A feedforward head uses the branch block and its two successors. Separate models operate at parsing time and on caller–callee graphs during inlining. Loop and dead-end heuristics refine predictions. [§§2.1–2.4, Table 1](https://labs.oracle.com/pls/apex/f?p=LABS%3A0%3A3704797645286%3AAPPLICATION_PROCESS%3DGETDOC_INLINE%3A%3A%3ADOC_ID%3A4980)

## How did the authors measure performance?

**Author claims.** Instrumented PGO runs supply edge counts. The true-edge fraction supplies the label. Normalized execution counts weight the binary cross-entropy loss. The authors split graphs from GraalVM Reachability Metadata libraries 90/10 for training and validation. For evaluation they report 29 benchmarks across Renaissance, DaCapo and DaCapo con Scala, plus a separate cloud microservice experiment. Their best guarded configuration delivered a 10.13% geometric-mean runtime speedup against uniform branch probabilities, with a 2.94% binary size increase and 20.85% compile-time increase. The reported setup is GraalVM Enterprise Edition 24, Serial GC and Oracle Linux Server 7.4. [§§3.1, 4.1–4.4, Table 2](https://labs.oracle.com/pls/apex/f?p=LABS%3A0%3A3704797645286%3AAPPLICATION_PROCESS%3DGETDOC_INLINE%3A%3A%3ADOC_ID%3A4980)

## Which comparisons can this project make?

**Our interpretation.** A close structural comparator would use method-local CFG information, matching the parsing stage. A branch-level comparison requires mapping IR successors to original bytecode jump edges, accounting for transformed or unmapped nodes, then scoring aligned branch/workload pairs. An identifier-masking experiment on these same pairs would test whether names add signal. Table 2 measures compiler outcomes and supplies no baseline value for branch-level MAE. [§§2.2–2.3, 4.1.3, Table 2](https://labs.oracle.com/pls/apex/f?p=LABS%3A0%3A3704797645286%3AAPPLICATION_PROCESS%3DGETDOC_INLINE%3A%3A%3ADOC_ID%3A4980)

**UNVERIFIED.** Exact JDK patch/build for the experiment, public access to its trained weights and labeled CFGs, and an original-BCI prediction export remain unconfirmed. Oracle documents deployed GraalNN support for JDK 24, which establishes product availability. Reproducing the paper or comparing predictions would require checking the model version and export path. [Oracle JDK 24 Native Image documentation](https://docs.oracle.com/en/graalvm/jdk/24/docs/reference-manual/native-image/optimizations-and-performance/)
