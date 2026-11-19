# Proposed contract v0

Each line of `static.jsonl` describes one conditional jump in one original class. Each workload has its own label file with precisely one row per static site, including zero-count sites. Each complete run has a manifest carrying the project ID, dataset version, compiler and VM, SHA-256 of the original class, inputs and output file hashes. The proposed v0 artifact unit is one class file. JAR provenance and classes loaded under multiple loaders require a joint design decision. [Static schema](static.schema.json) · [Label schema](label.schema.json)

## Identity and edge direction

`branch_id = artifact_sha256 + ":" + method_index + ":" + original_bci`. The index is zero-based in the classfile method table and counts constructors and methods without code. The offset is in the original method's Code attribute. A different class hash starts a new ID namespace, including changes to debug attributes. Use the class name, JVM method name and descriptor for human lookup. Cross-build deduplication needs its own mapping.

The extractor recognizes the sixteen JVM binary conditional opcodes. Their instruction length is three bytes. `target_bci` is the original jump destination and `fallthrough_bci` is the next instruction. ASM's instruction-offset hook and original label offsets provide both values. A method visitor inserts a private path for each decision outcome, so other incoming edges at a shared target do not increment the site's count. The pilot recomputes verifier frames and verifies the class on loading. Switches, unconditional jumps and exception-handler edges have different semantics and are outside the binary inventory. [JVM instruction definitions](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-6.html) · [ASM 9.11.1 source](https://repo.maven.apache.org/maven2/org/ow2/asm/asm/9.11.1/)

Counts are nonnegative signed 64-bit integers, incremented atomically with checked overflow. Each workload gets a fresh JVM. The trusted fixture finishes synchronously before snapshotting. With positive support, `p_taken = taken_count / (taken_count + fallthrough_count)`; otherwise the label is JSON `null`. Preserve both counts for likelihood metrics. An observed zero has positive fall-through support. An unsuccessful run produces no published result directory.

## ML input boundary

The loader returns `(branch_id, features, workload_id, label)`. Only `features` goes into a zero-run predictor. The pilot whitelist includes class and method identifiers, descriptor, opcode and original offsets. ID and artifact hash support joins. Project and workload identify evaluation groups. Run-level provenance, counts and probabilities belong to the evaluation side. Mask descriptor type names too when designing identifier ablations. The pilot exports local edges and names. Wider instruction context, referenced fields/methods and full basic blocks require a later extractor extension. [Loader and validator](../validate.py)

## Trace an example

In the committed `static.jsonl`, find method `guard`, descriptor `(I)I`, offset 1. Its branch ID ends in `:1:1`. In the original disassembly, `1: ifge 6` has fall-through BCI 4. Follow that same ID into each workload file. Nine of the ten mostly-positive inputs are nonnegative, compared with two of the ten mostly-negative inputs. The unused `dormant(I)Z` method is present in both files with counts 0/0. [Measured files](../../experiments/results/decisions-v0.1/) · [Configured inputs](../../experiments/configs/pilot.json)
