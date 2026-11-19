"""Zero-shot digit probabilities and final-token embeddings for a static branch inventory."""
import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import tempfile
import time

import numpy as np
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
REV = "ea3f2471cf1b1f0db85067f1ef93848e38e88c25"
HASHES = {
    "model.safetensors": "f9523886352217ded3aeeef552b381af79d568c6d49a4b9e423288cea56b0a44",
    "config.json": "b1e58593cd31852f7da5c2fc31ddf6135b9c066c0fd9177a4bbe95717083adff",
    "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    "tokenizer_config.json": "959e7f1d9a1b7641a6d6ce05ca97b75c7894fcb66cbe5a040406458fb1128ee4",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
}
SYSTEM = ("Estimate a conditional branch's taken frequency from its static Java bytecode. "
          "Taken means jumping to the target, rather than continuing at fall-through. "
          "Assume a typical unknown workload. Give exactly one digit from 0 (never taken) "
          "to 9 (always taken), with equal probability intervals between adjacent digits.")
MAX_CONTEXT_TOKENS = 384
CAP = 96


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def index_jsonl(path):
    rows = {}
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["branch_id"] in rows:
                raise ValueError(f"Duplicate branch in {path}")
            rows[row["branch_id"]] = row
    return rows


def collect(root):
    records = []
    counts = {}
    digests = {}
    for static_path in sorted(root.glob("*/static.jsonl")):
        project = static_path.parent.name
        context_path = static_path.with_name("context.jsonl")
        sites = index_jsonl(static_path)
        contexts = index_jsonl(context_path)
        if sites.keys() != contexts.keys():
            raise ValueError(f"{project}: incomplete context join")
        selected = sorted(sites, key=lambda k: hashlib.sha256(("42:" + k).encode()).digest())[:CAP]
        for key in selected:
            records.append((project, sites[key], contexts[key]))
        counts[project] = {"inventoried": len(sites), "selected": len(selected)}
        for path in [static_path, context_path]:
            digests[str(path.relative_to(root))] = sha(path)
    if not records:
        raise ValueError("No static branches found in CORPUS/PROJECT/{static,context}.jsonl")
    return records, counts, digests


def prompt_ids(tokenizer, site, sidecar, masked):
    owner = "<class>" if masked else site["class_name"]
    method = "<method>" if masked else site["method_name"]
    descriptor = site["method_descriptor"]
    if masked:
        descriptor = re.sub(r"L[^;]+;", "LType;", descriptor)
    context = sidecar["masked_context" if masked else "context"]
    context_ids = tokenizer.encode(context, add_special_tokens=False)
    truncated = len(context_ids) > MAX_CONTEXT_TOKENS
    if truncated:
        middle = MAX_CONTEXT_TOKENS // 2
        context = (tokenizer.decode(context_ids[:middle]) + "\n[...]\n"
                   + tokenizer.decode(context_ids[-middle:]))
    code = (f"Class {owner}\nMethod {method}{descriptor}\n"
            f"Branch at bytecode offset {site['original_bci']}: {site['branch_opcode']}\n"
            f"Jump target: {site['target_bci']}; fall-through: {site['fallthrough_bci']}\n"
            f"Instructions:\n{context}\nTaken frequency (0 to 9):")
    text = tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": code}],
        tokenize=False, add_generation_prompt=True,
    )
    return tokenizer.encode(text, add_special_tokens=False), truncated


@torch.inference_mode()
def infer_batch(model, tokenizer, batch, digits, device):
    # Right padding leaves original token positions intact. Read each row at its final real token.
    lengths = torch.tensor([len(ids) for ids in batch], device=device)
    width = int(max(map(len, batch)))
    tokens = torch.tensor([ids + [tokenizer.pad_token_id] * (width - len(ids)) for ids in batch],
                          dtype=torch.long, device=device)
    mask = torch.arange(width, device=device).unsqueeze(0) < lengths.unsqueeze(1)
    base = model.model(input_ids=tokens, attention_mask=mask.long(), use_cache=False)
    last = base.last_hidden_state[torch.arange(len(batch), device=device), lengths - 1]
    logits = model.get_output_embeddings()(last).float()
    digit_logits = logits[:, digits]
    bin_probs = digit_logits.softmax(dim=-1)
    q = (bin_probs * torch.arange(10, device=device)).sum(dim=-1) / 9
    digit_mass = torch.exp(digit_logits.logsumexp(-1) - logits.logsumexp(-1))
    emb = torch.nn.functional.normalize(last.float(), dim=-1)
    if not torch.isfinite(q).all() or not torch.isfinite(emb).all() or not torch.isfinite(digit_mass).all():
        raise ValueError("Nonfinite model output")
    return q.cpu().numpy(), digit_mass.cpu().numpy(), emb.half().cpu().numpy()


def main(args):
    if args.output.exists():
        raise FileExistsError(f"Choose a new output directory: {args.output}")
    if args.batch_size < 1 or args.threads < 1:
        raise ValueError("Batch size and CPU thread count must be positive")
    started = time.perf_counter()
    records, counts, digests = collect(args.corpus)
    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    torch.manual_seed(42)
    torch.set_num_threads(args.threads)
    model_dir = args.model_dir
    if model_dir is None:
        model_dir = Path(snapshot_download(MODEL, revision=REV, allow_patterns=list(HASHES)))
    for name, digest in HASHES.items():
        if sha(model_dir / name) != digest:
            raise ValueError(f"Unexpected SHA-256 for {name}")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    # Both platforms use the same FP32 outputs for scoring and L2 normalization. The stored
    # upstream tensors are BF16. On MPS use FP16 compute; the CPU reference uses FP32.
    dtype = torch.float16 if device == "mps" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True, dtype=dtype,
                                                attn_implementation="sdpa").to(device).eval()
    ids = [tokenizer.encode(str(i), add_special_tokens=False) for i in range(10)]
    if ids != [[n] for n in range(15, 25)]:
        raise ValueError(f"Digit token IDs differ from the pinned tokenizer: {ids}")
    digits = torch.tensor([v[0] for v in ids], device=device)
    rows = [{"project_id": p, "branch_id": s["branch_id"]} for p, s, _ in records]
    embeddings = {}
    lengths = Counter()
    truncated = Counter()
    token_minmax = {}
    forward_seconds = {}
    setup_seconds = time.perf_counter() - started
    for view in ("full", "masked"):
        vectors = np.empty((len(records), model.config.hidden_size), dtype=np.float16)
        prompts = []
        for i, (_, site, context) in enumerate(records):
            tokens, cut = prompt_ids(tokenizer, site, context, view == "masked")
            prompts.append((i, tokens))
            lengths[view] += len(tokens)
            truncated[view] += cut
        prompts.sort(key=lambda p: len(p[1]))
        token_minmax[view] = [len(prompts[0][1]), len(prompts[-1][1])]
        before = time.perf_counter()
        for start in range(0, len(prompts), args.batch_size):
            batch = prompts[start:start + args.batch_size]
            q, mass, vec = infer_batch(model, tokenizer, [x[1] for x in batch], digits, device)
            for j, (i, _) in enumerate(batch):
                rows[i]["q_" + view] = float(q[j])
                rows[i]["digit_mass_" + view] = float(mass[j])
                vectors[i] = vec[j]
        forward_seconds[view] = time.perf_counter() - before
        print(f"{view}: {len(rows)} branches in {forward_seconds[view]:.2f} forward seconds", flush=True)
        embeddings[view] = vectors
    metadata = {
        "model": MODEL, "revision": REV, "weights_license": "Apache-2.0", "model_sha256": HASHES,
        "input_sha256": digests, "script_sha256": sha(Path(__file__)), "seed": 42,
        "cap_per_project": CAP, "digit_token_ids": [v[0] for v in ids], "system_prompt": SYSTEM,
        "counts": counts, "successful_pairs": len(rows), "failed_pairs": 0,
        "device": device, "dtype": str(dtype), "platform": platform.platform(),
        "python": platform.python_version(), "packages": {p: version(p) for p in (
            "torch", "transformers", "tokenizers", "numpy", "safetensors", "huggingface_hub")},
        "batch_size": args.batch_size, "cpu_threads": args.threads,
        "setup_seconds": setup_seconds, "forward_seconds": forward_seconds,
        "elapsed_seconds_before_export": time.perf_counter() - started,
        "prompt_tokens": dict(lengths), "min_max_tokens": token_minmax,
        "truncated_instruction_contexts": dict(truncated), "remote_inference_calls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as staging:
        out = Path(staging) / "inference"
        out.mkdir()
        with (out / "predictions.jsonl").open("w") as output:
            for row in rows:
                output.write(json.dumps(row, allow_nan=False) + "\n")
        np.savez_compressed(out / "embeddings.npz", project_id=[row["project_id"] for row in rows],
                            branch_id=[row["branch_id"] for row in rows], **embeddings)
        metadata["outputs_sha256"] = {p.name: sha(p) for p in sorted(out.iterdir())}
        (out / "manifest.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
        out.rename(args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-dir", type=Path, help="Local copy of the six pinned files")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=4)
    main(parser.parse_args())
