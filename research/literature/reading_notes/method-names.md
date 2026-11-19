# Improving ML-Based Static Profiling Using Method Names

## What did the authors measure?

Stefan Milenković, Milan Čugurović and Milena Vujošević Janičić published a one-page contribution in the *Book of Abstracts*, XV Symposium “Mathematics and Applications,” University of Belgrade, 2025, p. 36. ISBN 978-86-7589-206-9. [Institutional record](https://research.matf.bg.ac.rs/handle/123456789/3037) · [Proceedings, p. 36](https://simpozijum.matf.bg.ac.rs/KNJIGA_APSTRAKATA_2025.pdf#page=36)

**Author claims.** The abstract describes a gradient-boosted binary classifier for method hotness in GraalVM Native Image. The authors add GloVe embeddings of method names to their existing features. Relative to a model without name features, they report 8% smaller binaries and a 2% runtime penalty. These are compiler outcome metrics. The opening discussion of branch probabilities describes earlier work. [Abstract, paragraphs 1–2](https://simpozijum.matf.bg.ac.rs/KNJIGA_APSTRAKATA_2025.pdf#page=36)

## What does this imply for our experiment?

**Our interpretation.** Identifier embeddings belong in the comparison set for RQ2. Use identical conditional-bytecode branches, target counts and project splits for the structural baseline, lexical model and SLM. This can test whether the SLM adds information beyond identifier tokens. The reported binary-size change supplies no estimate of the expected improvement in branch-probability error. [Abstract, paragraph 2](https://simpozijum.matf.bg.ac.rs/KNJIGA_APSTRAKATA_2025.pdf#page=36)

## What can we verify about the experiment?

**UNVERIFIED.** The contribution does not specify benchmark identities, workload selection, hotness threshold, train/test split, exact baseline feature list, JDK distribution/version, aggregation scheme or uncertainty intervals. It names no associated artifact and gives no classification accuracy or per-branch metric. A DOI is unverified. Use the proceedings URL and page when citing this abstract. [Complete published contribution](https://simpozijum.matf.bg.ac.rs/KNJIGA_APSTRAKATA_2025.pdf#page=36) · [Bibliographic record](https://research.matf.bg.ac.rs/handle/123456789/3037?mode=full)
