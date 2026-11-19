# Frozen code-model inference

## Which artifact and inputs produce the predictions?

The run uses Qwen2.5-Coder-0.5B-Instruct, an instruction-tuned 0.49B-parameter causal model from Qwen. Its repository identifies the license as Apache 2.0. The checkpoint at revision `ea3f2471cf1b1f0db85067f1ef93848e38e88c25` stores BF16 weights. The CLI checks the weights, tokenizer and model configuration against embedded SHA-256 digests. [Pinned model card](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct/blob/ea3f2471cf1b1f0db85067f1ef93848e38e88c25/README.md) · [License](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct/blob/ea3f2471cf1b1f0db85067f1ef93848e38e88c25/LICENSE)

Supply a corpus directory with one subdirectory per project containing `static.jsonl` and `context.jsonl`. The join checks for duplicate IDs and missing context. In each project select the 96 smallest SHA-256 digests of the UTF-8 string `42:` followed by branch ID, or all branches when there are fewer. Project and branch IDs provide joins. The prompt carries only the original class name, method, descriptor, bytecode branch position, opcode, successor offsets and local instruction neighborhood. The masked view replaces the declared class and method names, replaces descriptor object types with `Type`, and uses the corpus provider's masked instruction window. Both views retain the numerical offsets. [Study protocol](../../experiments/study/protocol.md) · [Prompt construction](predict.py)

## How do the logits become a branch probability?

The chat template requests one digit between zero (never jumps) and nine (always jumps). Apply the model once in evaluation mode, take the logits at the final real input token and restrict them to the ten digit tokens, IDs 15 through 24. For logit vector `z`, define `w[d] = exp(z[d]) / sum(exp(z[k]) for k in digits)` and `q = sum(d * w[d] for d in digits) / 9`. Temperature is one. `q` is the model's expected rating under this readout. Its statistical calibration requires empirical evaluation. The output also records the total probability mass of digit answers under the unrestricted next-token distribution. A small mass indicates that digit restriction discards much of what the model wanted to say. [Implementation](predict.py)

Both representations use the last prompt-position vector after the decoder's final normalization, L2-normalized in FP32 and saved as 896 FP16 components. The supervised regression stage can learn its own mapping using training labels. Each static site has one pair of model outputs across all workloads. [Model configuration](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct/blob/ea3f2471cf1b1f0db85067f1ef93848e38e88c25/config.json)

## How can the inference be reproduced?

From the repository root, run the following in a clean Python 3.11–3.13 environment. On Linux use the PyTorch CPU wheel index for the first install. The default model download retrieves the pinned snapshot. For a local copy use `--model-dir PATH`.

```sh
python -m pip install 'torch==2.10.0' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ml/slm/requirements.txt
python ml/slm/predict.py experiments/study/corpus /tmp/branch-predictions --device cpu
```

macOS with Apple Silicon also supports `--device mps` after installing the macOS torch wheel. CPU uses FP32, MPS uses FP16. Floating-point rounding and batch sizes can change numerical results. Inference makes no calls to a hosted model. The output directory must be new. `predictions.jsonl` and `embeddings.npz` use the same project and branch IDs. `manifest.json` records model, inputs, output hashes, prompt token counts, truncations, runtime, package versions, device and precision. Runtime metrics exclude label generation and downstream regression.
