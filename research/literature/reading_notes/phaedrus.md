# Phaedrus: Predicting Dynamic Application Behavior with Lightweight Generative Models and LLMs

## What did the authors measure?

The Dynamis component predicts frequently executed and runtime-dominant functions using an LLM and compiler analysis. Morpheus generalizes from whole-program path profiles. The paper evaluates profile-guided compiler outcomes. [OOPSLA 2026 abstract; author manuscript §§3, 5](https://arxiv.org/abs/2412.06994)

## Decision for this study

Situate zero-run language-model inference among existing compiler uses of LLMs. Specify target and workload inputs when drawing the comparison. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The function-level predictions and available input information differ from a workload-blind probability for an original JVM jump. [Primary source](https://arxiv.org/abs/2412.06994) · [Publication record](https://doi.org/10.1145/3798225)
