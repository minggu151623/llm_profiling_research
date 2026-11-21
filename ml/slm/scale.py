"""Exploratory, not preregistered: the registered prompts and readouts on Qwen2.5-Coder-1.5B-Instruct.

Everything except the checkpoint comes from predict.py: site selection, prompt text, digit readout, final-token
pooling, batching and output format. The 1.5B tokenizer files have the same SHA-256 digests as the pinned 0.5B
files, so both models receive identical token sequences. The final hidden state has 1,536 components.
"""
import argparse
from pathlib import Path

import predict

predict.MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
predict.REV = "2e1fd397ee46e1388853d2af2c993145b0f1098a"
predict.HASHES = {
    "model.safetensors": "c1b9b30e907950516ba3c646bdf570d8084c25a6410a0cdca80cf04b11bc13a8",
    "config.json": "88f9a17863c05fb313515d2ff74b1098e0c35579f99068e32beda00618508ae0",
    "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    "tokenizer_config.json": "959e7f1d9a1b7641a6d6ce05ca97b75c7894fcb66cbe5a040406458fb1128ee4",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-dir", type=Path, help="Local copy of the six pinned files")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=4)
    predict.main(parser.parse_args())
