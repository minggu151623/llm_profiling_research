# Static Branch Frequency and Program Profile Analysis

## What did the authors measure?

Section 3 distinguishes a conditional direction, an edge probability and a block or edge frequency. Observed heuristic hit rates supply probabilistic evidence. The method combines multiple applicable heuristics, then estimates how frequently program regions execute. [Abstract and §3, Branch Prediction and Probability](https://klasses.cs.uchicago.edu/archive/2017/fall/32001-1/papers/wu-larus-profiling.pdf)

## Decision for this study

Document precisely which heuristic and probability assignment were implemented. Record the runtime taken denominator at each JVM site. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The registered baseline omits multi-heuristic combination and frequency propagation. [Primary source](https://klasses.cs.uchicago.edu/archive/2017/fall/32001-1/papers/wu-larus-profiling.pdf) · [Publication record](https://doi.org/10.1145/192724.192725)
