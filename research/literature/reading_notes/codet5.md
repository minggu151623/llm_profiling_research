# CodeT5: Identifier-aware Unified Pre-trained Encoder-Decoder Models for Code Understanding and Generation

## What did the authors measure?

The model learns to tag and recover identifiers along with other pretraining objectives. Table 7 isolates masked-span and masked-identifier prediction on a Java source subset. [Identifier-aware objectives; Table 7](https://aclanthology.org/2021.emnlp-main.685.pdf)

## Decision for this study

Compare the same predictor with identifiers present and masked. Measure the change against branch labels rather than using language-model task accuracy as a surrogate. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

Source-level identifier recovery supplies no numeric estimate of a JVM branch probability. The study here uses a different checkpoint and representation. [Primary source](https://aclanthology.org/2021.emnlp-main.685.pdf) · [Publication record](https://doi.org/10.18653/v1/2021.emnlp-main.685)
