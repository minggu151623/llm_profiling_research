# Branch Prediction for Free

## What did the authors measure?

The paper uses natural-loop analysis and program-based rules for non-loop branches. Section 1 separately describes an address-direction convention that predicts backward jumps taken and forward jumps untaken. Sections 4–5 test individual rules and combine them. [University technical report §§1, 3–5](https://ftp.cs.wisc.edu/pub/techreports/1993/TR1137.pdf)

## Decision for this study

Use the name backward-taken/forward-not-taken for our offset rule. Turning each decision into q=0 or 1 is a choice in our protocol. [Study protocol](../../../experiments/study/protocol.md)

## Evidence limits

The full algorithm needs information such as loop structure. Its reported miss rate cannot be read as a probability MAE. [Primary source](https://ftp.cs.wisc.edu/pub/techreports/1993/TR1137.pdf) · [Publication record](https://doi.org/10.1145/155090.155119)
