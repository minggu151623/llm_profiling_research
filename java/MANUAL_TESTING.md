# Manual Java checks

These checks do not rely on the project's runner or test code. You read bytecode with `javap`, work out by hand which way each jump goes for each input, and compare your count with the recorded label. Run the automated checks in [TESTING.md](TESTING.md) first, because M2 to M5 read the JARs that run downloads.

You need the Temurin 25 JDK on `PATH` (`javap` and `jshell`), Python 3 and a terminal at the repository root. Each check takes a few minutes. Record pass or fail for M1 to M7 in the report block at the end of TESTING.md.

## Conventions you need

- A branch ID is `<class SHA-256>:<method index>:<BCI>`. BCI is the bytecode index that `javap -c` prints at the start of each instruction.
- "Taken" means the JVM jumps to the instruction's target. "Fall-through" means it continues with the next instruction. This follows the bytecode, not the Java source. Javac often inverts a source condition: `if (n < 0) return -1;` becomes `ifge`, which jumps when `n >= 0`.
- Each workload runs 100 iterations in blocks of 20. Within each block, iterations 0 to 16 use family A under `normal` and iterations 0 to 2 use family A under `shift`. The rest use family B. Each iteration picks input index `random.nextInt(6)` from `new Random(1516)`. [Driver](corpus/Workloads.java)

## M1. Count a pilot label from the input list

Goal: confirm the jump direction convention on a case small enough to count on paper.

1. Read [Decisions.java](fixtures/Decisions.java). `guard(int n)` contains `if (n < 0) return -1;`.
2. Open [javap.txt](../experiments/results/decisions-v0.1/javap.txt) and find `guard`. BCI 1 is `ifge 6`, which jumps when `n >= 0`.
3. Read the two input arrays in [pilot.json](../experiments/configs/pilot.json). Count the values that are `>= 0` in each array. Each value calls `guard` once.
4. Compare with the recorded labels:

```sh
grep -h ':1:1"' experiments/results/decisions-v0.1/mostly-*.jsonl
```

Expected: `mostly-positive` is taken 9 times and falls through once, and `mostly-negative` is taken 2 times and falls through 8 times. Pass if your paper count gives the same numbers.

## M2. Match a recorded site to the original bytecode

Goal: confirm that a static row describes the instruction that exists in the released JAR.

```sh
javap -c -p -classpath ~/.cache/branch-study/jars/joda-time-2.12.7.jar org.joda.time.field.FieldUtils \
  | grep -A16 'public static int safeMultiply(int, int)'
grep '"safeMultiply","method_descriptor":"(II)I"' experiments/study/corpus/joda-time/static.jsonl
```

In the `javap` output, find these two instructions:

```text
11: iflt          22
19: ifle          58
```

Expected: the two static rows have `original_bci` 11 and 19, `branch_opcode` `IFLT` and `IFLE`, `target_bci` 22 and 58, and `fallthrough_bci` 14 and 22. The fall-through BCI is the next instruction in the listing. Pass if all four fields agree for both rows.

## M3. Derive the Joda-Time labels by hand

Goal: predict the counts at both sites from the inputs and the bytecode alone.

The bytecode computes `long total = (long) n * n`. BCI 11 jumps when `total < Integer.MIN_VALUE`, and BCI 19 jumps when `total <= Integer.MAX_VALUE`. The driver calls `safeMultiply(n, n)` once per iteration with these inputs:

| Index | Family A `n` | Family B `n` |
| ---: | ---: | ---: |
| 0 | 1 | -93 |
| 1 | 2 | -1 |
| 2 | 3 | 0 |
| 3 | 4 | 31 |
| 4 | 5 | 99999 |
| 5 | 6 | 100000 |

1. A square is never negative, so BCI 11 is never taken. Expect 0 taken and 100 fall-through under both workloads.
2. Check each square against 2,147,483,647. Only family B indices 4 and 5 exceed it (9,999,800,001 and 10,000,000,000). Those iterations fall through at BCI 19 and throw `ArithmeticException`. Every other iteration jumps.
3. Count how many iterations draw family B with index 4 or 5. Run this in `jshell`. It replays the driver's random draws and does not use any project code:

```java
for (int limit : new int[]{17, 3}) {
    var r = new java.util.Random(1516);
    int big = 0;
    for (int i = 0; i < 100; i++) {
        int k = r.nextInt(6);
        if (i % 20 >= limit && k >= 4) big++;
    }
    System.out.println(limit + " -> " + big);
}
```

It prints `17 -> 5` for `normal` and `3 -> 27` for `shift`.

4. Compare with the recorded labels:

```sh
grep -h ':5:1[19]"' experiments/study/corpus/joda-time/normal.jsonl experiments/study/corpus/joda-time/shift.jsonl
```

Expected: BCI 11 is 0 / 100 in both files. BCI 19 is 95 / 5 under `normal` and 73 / 27 under `shift`. Pass if all four rows match your derivation.

## M4. Derive a second project's labels

Goal: repeat M3 on a different library, using string inputs.

```sh
javap -c -p -classpath ~/.cache/branch-study/jars/jsoup-1.18.3.jar org.jsoup.internal.StringUtil \
  | grep -A8 'public static boolean isBlank'
```

`isBlank(String)` starts with `1: ifnull 11`, which jumps when the string is null, and `8: ifne 13`, which jumps when `length()` is not zero. The driver calls `isBlank` once per iteration. Family A is six non-empty words. Family B is in `WHITESPACE` in [Workloads.java](corpus/Workloads.java), and index 3 is the empty string `""`.

1. No input is null, so BCI 1 is never taken: 0 / 100 under both workloads.
2. BCI 8 falls through only for the empty string. In the M3 `jshell` loop, change the condition to `k == 3`. It prints `17 -> 5` and `3 -> 18`.
3. Compare:

```sh
grep -h ':6:[18]"' experiments/study/corpus/jsoup/normal.jsonl experiments/study/corpus/jsoup/shift.jsonl
```

Expected: BCI 1 is 0 / 100 in both files. BCI 8 is 95 / 5 under `normal` and 82 / 18 under `shift`. Pass if all four rows match.

Also check the model input for this site. The named context shows the call as `java/lang/String.length()I`. The masked context replaces the class and method name with `TYPE.member()I`, keeps the opcodes, and has no count or probability field:

```sh
grep ':6:8"' experiments/study/corpus/jsoup/context.jsonl
```

## M5. Explain the sites that never ran

Goal: confirm that unexecuted sites are kept and have a reason.

```sh
python3 - <<'EOF'
import json
from collections import Counter
base = "experiments/study/corpus/joda-time/"
static = [json.loads(l) for l in open(base + "static.jsonl")]
for w in ("normal", "shift"):
    labels = {json.loads(l)["branch_id"]: json.loads(l) for l in open(base + w + ".jsonl")}
    empty = Counter((s["method_name"], s["method_descriptor"]) for s in static
                    if labels[s["branch_id"]]["p_taken"] is None)
    print(w, dict(empty))
EOF
```

Expected under both workloads: `safeAdd (JJ)J` 2 sites, `safeMultiply (JI)J` 2 sites and `safeMultiply (JJ)J` 9 sites, 13 in total. Each of these rows has 0 taken, 0 fall-through and `p_taken` null. The driver passes `int` values, so Java selects the `int` overloads and never calls the `long` versions. Pass if the list matches and you agree with that explanation after reading the `joda-time` case in [Workloads.java](corpus/Workloads.java).

## M6. Confirm instrumentation did not change program output

Goal: confirm that the original and probed runs computed the same results.

```sh
python3 -c "
import json
m = json.load(open('experiments/study/corpus/manifest.json'))['projects']
for p, v in m.items():
    for w, c in v['checks'].items():
        print(p, w, c['reference_sha256'] == c['instrumented_sha256'])
"
```

Expected: 16 lines, every one ending in `True`. Repeat with `$scratch/corpus/manifest.json` from your own run in TESTING.md. Pass if both show 16 of 16.

## M7. Make sure a corrupted count is rejected

Goal: confirm that the verifier catches a changed label rather than passing it silently.

```sh
tmp=$(mktemp -d)
cp -R experiments/study/corpus "$tmp/corpus"
python3 - "$tmp/corpus/joda-time/normal.jsonl" <<'EOF'
import sys
path = sys.argv[1]
text = open(path).read()
old = '"taken_count":95,"fallthrough_count":5,"p_taken":0.95'
assert text.count(old) == 1
open(path, "w").write(text.replace(old, '"taken_count":94,"fallthrough_count":6,"p_taken":0.94'))
EOF
python3 scripts/verify_study.py "$tmp/corpus" experiments/study/slm experiments/study/evaluation
rm -rf "$tmp"
```

Expected: the verifier stops with `ValueError: Corpus digest mismatch for joda-time/normal.jsonl`. Pass if it fails with that message. If it prints `Verified ...`, record a fail.
