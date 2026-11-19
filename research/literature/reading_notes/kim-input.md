# 2D-Profiling: Detecting Input-Dependent Branches with a Single Input Data Set

## What did the authors measure?

The authors study variation in branch-predictor accuracy across inputs and propose using within-run variation from one profile to detect sensitive branches. They distinguish this task from measuring taken bias. Section 4.3 varies the number of inputs used as reference. [§§1–3, 4.3](https://users.ece.cmu.edu/~omutlu/pub/kim_cgo06.pdf)

## Decision for this study

Pair the same static site across workloads. Quantify the change in empirical taken fraction and report how often a site is observed in only one workload. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

Our estimator sees only static features. Its per-site change in taken probability differs from a processor predictor’s change in accuracy. [Primary source](https://users.ece.cmu.edu/~omutlu/pub/kim_cgo06.pdf) · [Publication record](https://doi.org/10.1109/CGO.2006.1)
