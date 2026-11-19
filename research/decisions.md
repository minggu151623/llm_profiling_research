# Audit and review decisions

## Starting state on 2026-11-19

The local directory contained only the Vietnamese research brief and had no Git history. The requested GitHub repository had no refs, README, build, tests, schema, dataset or literature notes. The initial main commit preserves that brief. The first pull request introduced the pilot. The host provided Azul Zulu 25, 21 and 17. The recorded run used a checksum-verified, isolated Eclipse Temurin download and Maven 3.9.11. ASM 9.11.1 was available on Maven Central and read and rewrote the fixture's major-version-69 class. [Temurin release](https://github.com/adoptium/temurin25-binaries/releases/tag/jdk-25.0.5.1%2B2) · [ASM artifact](https://repo.maven.apache.org/maven2/org/ow2/asm/asm/9.11.1/) · [Manifest](../experiments/results/decisions-v0.1/manifest.json)

## Scope and acceptance

| Step | Files | Acceptance evidence |
| --- | --- | --- |
| Check the three closest publications | `research/literature/` | Bibliography IDs join to the evidence matrix, each note links primary sources, access limits and unresolved claims are explicit |
| Freeze pilot v0 | `data/schema/`, `data/validate.py` | Static-only input whitelist, workload-separated labels, unique original IDs and explicit unobserved rows |
| Compile and extract | `java/fixtures/`, `Branches.java` | JUnit compares method, descriptor, opcode, offset and target for every conditional in the fixture against original javap |
| Count and reconcile | `Counters.java`, `Pilot.java`, `BranchesTest.java` | Known guard counts, matching return values, handled division by zero, unchanged exception type on null input, verification at class load |
| Reproduce the slice | `scripts/pilot.py`, `experiments/`, `data/tests/` | Two workloads, complete joins, hand-checkable outcomes, config and environment manifest with hashes |

The profile driver is intentionally limited to a trusted, self-contained class exposing `public static int score(int[])`. The extractor's class-level inventory is independent of that driver. Setup measures one synchronous invocation with zero warmup after checking output in a separate class loader. Scores verify this fixture's observable return value. Support for external class hierarchies, multiple loaders, asynchronous workers, shared application state, general side effects, instrumentation overhead and large methods requires further validation. Labels from the toy fixture are suitable for testing code and schema.

## Decisions frozen for the pilot

The repository owner confirmed the pilot contract and evaluation split rules. Schema v0 identifies a branch by original class SHA-256, method-table index and original BCI. Counts stay separate for each workload. Zero support yields a null probability. The unseen-project protocol groups entire project families, while the workload-shift protocol holds out workloads within a seen project. The sample fixture is reserved for checking the pipeline. [Data contract](../data/schema/README.md) · [Split rules](questions.md#frozen-split-rules)

## Joint decisions before expanding

1. Both contributors review whether the frozen one-class pilot contract covers the selected benchmark artifacts. Record any extension and version changes to ID or label semantics.
2. Select independent projects, workload licenses, JDK 25 compatibility probes, minimum coverage and fixed Linux environment. Document forks and near-duplicate removal before freezing splits.
3. Freeze RQ, baselines and uncertainty protocol. A direct Graal comparison needs defensible IR-to-bytecode alignment and matching edge orientation. Recheck ongoing method-signature work before any novelty claim.
4. Agree on compute, models and licenses before running large benchmarks or training. The two human contributors decide manuscript claims, authorship and submission.

The Java/JVM engineer owns extraction and provenance, and the AI/ML researcher owns modeling and evaluation. Both review interfaces and interpretation. This handoff assigns roles without assigning identities or author order.
