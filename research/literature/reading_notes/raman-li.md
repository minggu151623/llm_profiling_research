# Learning Branch Probabilities in Compiler from Datacenter Workloads

## What did the authors measure?

For each side of a branch, the authors encode calls in control-dependent blocks and embed callee-name features. SamplePGO supplies the target t/(t+nt). Table 1 reports more than seven million unique examples, and §5 compares profile estimates and compiled performance. [§§4.3.1–4.4.1, Table 1, §5](https://arxiv.org/html/2202.06728)

## Decision for this study

There is a direct precedent for using names to estimate branch probability. Our experiment asks what a frozen code SLM adds over a lexical model on the same original JVM sites. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The labels use sampled profiles from a shared C/C++ codebase. The paper does not give a matched score for the public Java classes and workloads in this repository. [Primary source](https://arxiv.org/html/2202.06728) · [Publication record](https://doi.org/10.48550/arXiv.2202.06728)
