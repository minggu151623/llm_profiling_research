# The Adverse Effects of Code Duplication in Machine Learning Models of Code

## What did the authors measure?

The author compares code-model evaluation on corpora containing duplicates with evaluation after deduplication and reports that duplication can inflate performance estimates. [Author publication page and ACM abstract](https://miltos.allamanis.com/publications/2019adverse/)

## Decision for this study

Keep project families together and inspect residual method or local-context overlap. Record the removal rule and exclusions per fold. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The study’s source-code duplicate detector and inflation magnitudes do not establish the correct JVM overlap threshold or effect size. [Primary source](https://miltos.allamanis.com/publications/2019adverse/) · [Publication record](https://doi.org/10.1145/3359591.3359735)
