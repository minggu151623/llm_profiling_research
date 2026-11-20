# Java test handoff

This file is for the team member who tests the Java side independently. It covers the bytecode instrumentation, the jump direction of each recorded edge, the execution counts and whether the corpus can be rebuilt from scratch.

Status: the maintainer ran every check below on macOS arm64 on 19 November 2026 and again on 21 November 2026 at commit 18a4f3b, including M1 to M7, and GitHub Actions reproduced the corpus on Ubuntu 24.04. These are not independent runs. Your own run has not been recorded yet. For checks you perform by reading bytecode and counting inputs yourself, see [MANUAL_TESTING.md](MANUAL_TESTING.md).

## Requirements

- Eclipse Temurin HotSpot 25.0.5.1+2. [Downloads by platform](https://github.com/adoptium/temurin25-binaries/releases/tag/jdk-25.0.5.1%2B2)
- Apache Maven 3.9.11
- Python 3.11 or newer. The scripts use only the standard library.
- Network access to Maven Central on the first run. The runner downloads eight pinned JARs into `~/.cache/branch-study/jars` and checks each SHA-256 against [corpus.json](../experiments/configs/corpus.json).

Set `JAVA_HOME` to the Temurin JDK and put its `bin` directory and Maven on `PATH`. The Linux setup used in CI is in [study.yml](../.github/workflows/study.yml).

## Run the automated checks

Run these from the repository root:

```sh
mvn -v
mvn -B -ntp -f java/pom.xml clean test
scratch=$(mktemp -d)
python3 scripts/corpus.py "$scratch/corpus"
for expected in experiments/study/corpus/*/*.jsonl; do
    cmp "$expected" "$scratch/corpus/${expected#experiments/study/corpus/}" || exit 1
done
echo "all 32 files match"
python3 scripts/verify_study.py experiments/study/corpus experiments/study/slm experiments/study/evaluation
```

What each step should print:

| Step | Expected result |
| --- | --- |
| `mvn -v` | Maven 3.9.11 with Java version 25.0.5.1, vendor Eclipse Adoptium. If it shows another JDK, fix `JAVA_HOME` first. |
| `mvn ... clean test` | 5 tests, 0 failures: 3 in `CorpusVerificationTest`, 2 in `BranchesTest`. |
| `corpus.py` | One `Profiling <project>` line per project, then `Wrote verified corpus to ...`. It took about 20 s on the development Mac once the JARs were cached. |
| `cmp` loop | No output from `cmp`, then `all 32 files match`. That is 8 projects times 4 files: `static`, `context`, `normal` and `shift`. |
| `verify_study.py` | `Verified 8 projects, 193 static predictions per model, 5211 joined evaluation rows and 27 aggregate rows.` |

`corpus.py` fails on its own if any of its internal checks fail. For every project it:

1. checks the JAR's SHA-256,
2. runs `javap` on the original class and requires each recorded conditional jump to match its opcode, bytecode index (BCI) and target,
3. runs the original class and the instrumented class in separate JVMs with `-Xverify:all` under both workloads,
4. requires the SHA-256 of the program output to be identical for the original and instrumented runs.

The new `manifest.json` in your output directory records your JDK, OS and architecture. Those fields will differ from the committed manifest. Only the 32 JSONL files need to match. [Runner](../scripts/corpus.py)

## What the JUnit tests cover

| Test | What it checks |
| --- | --- |
| `BranchesTest.inventoryMatchesOriginalJavap` | Compiles [Decisions.java](fixtures/Decisions.java) and requires the instrumenter's list of conditional jumps to equal the list `javap -c` prints, method by method. |
| `BranchesTest.rewrittenClassRetainsBehaviorAndCountsJumpDirection` | The instrumented class returns the same values and throws the same exception type as the original. In `guard`, `ifge` is taken 4 times and falls through 2 times on the input `{-2, -2, 0, 1, 4, 8}`. The never-called method `dormant` records zero on both edges. |
| `CorpusVerificationTest.sharedTargetCountsEachSourceEdgeExactlyOnce` | A generated method where `iflt` at BCI 1 and `ifeq` at BCI 5 both jump to BCI 17, and a `goto` also lands there. Over six input pairs the counts are 2 taken / 4 fall-through at BCI 1, 1 / 3 at BCI 5 and 2 / 1 at BCI 11. Each probe counts the edge it leaves from, not the label it reaches. |
| `CorpusVerificationTest.aWidenedProductOracleMatchesBothRecordedJodaWorkloads` | Recomputes Joda-Time `safeMultiply(II)I` BCI 19 from the driver's input schedule using `long` arithmetic: 95 / 5 under `normal`, 73 / 27 under `shift`. |
| `CorpusVerificationTest.corpusContextsHaveAlignedFocalInstructionsAndDisjointLabelFields` | For all eight projects: the static and context files list the same branch IDs, the named and masked contexts have the same opcodes, exactly one line carries the `>>` marker on the conditional jump, and no static or context row contains a label field. |

[Corpus tests](src/test/java/org/branchpilot/CorpusVerificationTest.java) · [Fixture tests](src/test/java/org/branchpilot/BranchesTest.java)

## Report your result

Copy this block into the pull request or send it to the project owner:

```text
Commit tested:
OS and architecture:
java -version:
mvn -v (first line):
JUnit: __ tests, __ failures
cmp: __ of 32 files identical
verify_study.py: pass / fail
Manual checks (MANUAL_TESTING.md): M1 __ M2 __ M3 __ M4 __ M5 __ M6 __ M7 __
Notes:
```

If `cmp` reports a difference, keep the scratch directory. Report the project, the workload and the first branch ID whose line differs, for example with `diff <(sort expected) <(sort actual) | head`.
