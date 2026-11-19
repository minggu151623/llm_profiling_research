# VESPA: Static Profiling for Binary Optimization

## What did the authors measure?

VESPA adapts compiler features to features recoverable in native binaries. It regresses branch probabilities and uses frequency propagation to supply BOLT. Its end-to-end evaluation covers four large executables. [§§3.2, 3.5, 5; software availability](https://homepages.dcc.ufmg.br/~fernando/publications/papers/AngelicaOOPSLA21.pdf)

## Decision for this study

Judge supervised structural regression on our bytecode representation and report representational limits when discussing binary profilers. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The binary optimizer, native program representations and workload distribution differ from original JVM bytecode. The paper’s executable runtime comparison measures a separate outcome. [Primary source](https://homepages.dcc.ufmg.br/~fernando/publications/papers/AngelicaOOPSLA21.pdf) · [Publication record](https://doi.org/10.1145/3485521)
