"""Exploratory, not preregistered: score Qwen2.5-Coder-1.5B outputs with the registered folds.

The registered evaluation runs unchanged except that the embedding loader accepts the 1.5B width. The script
compares each SLM readout with lexical ridge from the same run and with the registered 0.5B readout, using the
registered project bootstrap, and records the diagnostics the manuscript reports for the 0.5B model.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import tempfile

import numpy as np
from scipy.stats import spearmanr

import evaluate
import study_data
from summarize import write_rows

VIEWS = ("full", "masked")
SLM_MODELS = ("zero_full", "zero_masked", "embedding_full", "embedding_masked")


def read_any_width(path, sites):
    """study_data.read_model without the fixed 896-component check; both views must share one width."""
    predictions = study_data.read_index(path / "predictions.jsonl")
    selected = {s.key: s.project for s in sites if s.selected}
    with np.load(path / "embeddings.npz", allow_pickle=False) as data:
        keys = data["branch_id"].astype(str).tolist()
        projects = data["project_id"].astype(str).tolist()
        if len(keys) != len(set(keys)) or set(keys) != selected.keys() or predictions.keys() != selected.keys():
            raise ValueError("Expected every preselected site to have its predictions and representations")
        if projects != [selected[key] for key in keys]:
            raise ValueError("Embedding project IDs do not match the site inventory")
        widths = {data[v].shape for v in VIEWS}
        if len(widths) != 1 or next(iter(widths))[0] != len(keys):
            raise ValueError(f"Inconsistent embedding shapes {widths}")
        vectors = {v: dict(zip(keys, data[v].astype(np.float32), strict=True)) for v in VIEWS}
    for key, row in predictions.items():
        if row["project_id"] != selected[key] or not all(
                0 <= row[f"q_{v}"] <= 1 and np.isfinite(vectors[v][key]).all() for v in VIEWS):
            raise ValueError(f"Invalid SLM output at {key}")
    return predictions, vectors


def load_predictions(path):
    rows = defaultdict(dict)
    labels = {}
    with path.open() as stream:
        for r in csv.DictReader(stream):
            t, f = int(r["taken"]), int(r["fallthrough"])
            key = r["setting"], r["workload"], r["project"], r["branch_id"]
            rows[key][r["model"]] = float(r["q"])
            labels[key] = (t, f)
    return rows, labels


def project_mae(rows, labels, setting, workload, model):
    errors = defaultdict(list)
    for key, preds in rows.items():
        t, f = labels[key]
        if key[0] == setting and key[1] == workload and t + f:
            errors[key[2]].append(abs(preds[model] - t / (t + f)))
    return {p: float(np.mean(e)) for p, e in errors.items()}


def mean_cosine(vectors):
    x = np.stack(list(vectors.values()))
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    n = len(x)
    return float((x @ x.T).sum() - n) / (n * (n - 1))


def main(corpus, slm, registered, out, config):
    evaluate.read_model = read_any_width
    with tempfile.TemporaryDirectory() as tmp:
        evaluate.evaluate(corpus, slm, Path(tmp), config)
        new_rows, labels = load_predictions(Path(tmp) / "predictions.csv")
        folds = json.loads((Path(tmp) / "folds.json").read_text())
    old_rows, old_labels = load_predictions(registered / "predictions.csv")
    if old_labels != labels:
        raise ValueError("The 1.5B evaluation scored different sites or counts from the registered run")
    projects = config["projects"]
    draws = np.random.default_rng(config["seed"]).integers(len(projects), size=(config["bootstrap_draws"], len(projects)))

    def contrast(a, b):
        a, b = np.array([a[p] for p in projects]), np.array([b[p] for p in projects])
        delta = a - b
        lo, hi = np.quantile(delta[draws].mean(axis=1), [.025, .975])
        return dict(macro_mae=a.mean(), reference_mae=b.mean(), mean_delta=delta.mean(), ci_low=lo, ci_high=hi,
                    projects_lower_mae=int((delta < 0).sum()))

    table = []
    for setting, workload in (("unseen", "normal"), ("unseen", "shift"), ("seen", "shift")):
        lexical = project_mae(new_rows, labels, setting, workload, "lexical_ridge")
        for model in SLM_MODELS:
            if setting == "seen" and model.startswith("zero"):
                continue
            new = project_mae(new_rows, labels, setting, workload, model)
            old = project_mae(old_rows, labels, setting, workload, model)
            table.append(dict(setting=setting, workload=workload, model=f"qwen1.5b_{model}", reference="lexical_ridge",
                              **contrast(new, lexical)))
            table.append(dict(setting=setting, workload=workload, model=f"qwen1.5b_{model}", reference=f"qwen0.5b_{model}",
                              **contrast(new, old)))
    write_rows(out / "scale.csv", table)

    inference = study_data.read_index(slm / "predictions.jsonl")
    manifest = json.loads((slm / "manifest.json").read_text())
    _, vectors = read_any_width(slm, study_data.load_corpus(corpus, config))
    normal = {k[3]: t / (t + f) for k, (t, f) in labels.items() if k[:2] == ("unseen", "normal") and t + f}
    unseen = {k[3]: v for k, v in new_rows.items() if k[:2] == ("unseen", "normal")}
    summary = dict(
        model=manifest["model"], revision=manifest["revision"], embedding_width=len(next(iter(vectors["full"].values()))),
        forward_seconds=manifest["forward_seconds"], prompt_tokens=manifest["prompt_tokens"],
        truncated_instruction_contexts=manifest["truncated_instruction_contexts"],
        platform=manifest["platform"], packages=manifest["packages"],
        unseen_choices={f["test"]: {m: f["choices"][m] for m in ("embedding_full", "embedding_masked")}
                        for f in folds["unseen"]})
    for v in VIEWS:
        q = np.array([r[f"q_{v}"] for r in inference.values()])
        keys = sorted(normal)
        summary[f"zero_{v}"] = dict(
            min=float(q.min()), max=float(q.max()), sd=float(q.std()),
            mean_digit_mass=float(np.mean([r[f"digit_mass_{v}"] for r in inference.values()])),
            spearman_normal=float(spearmanr([inference[k][f"q_{v}"] for k in keys], [normal[k] for k in keys])[0]),
            mean_pairwise_cosine=mean_cosine(vectors[v]))
    gaps = [abs(r["embedding_full"] - r["structural_ridge"]) for r in unseen.values()]
    summary["embedding_full_vs_structural_ridge"] = dict(median=float(np.median(gaps)), max=float(np.max(gaps)))
    (out / "scale_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("slm", type=Path, help="Output directory of ml/slm/scale.py")
    parser.add_argument("registered", type=Path, help="Registered evaluation directory with predictions.csv")
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, default=evaluate.ROOT / "experiments/study/config.json")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    main(args.corpus, args.slm, args.registered, args.output, json.loads(args.config.read_text()))
