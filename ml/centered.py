"""Exploratory, not preregistered: refit the embedding ridges after removing the training-mean hidden state.

The released final-prompt states share one dominant direction (mean pairwise cosine above 0.99), so the
registered readout leaves the ridge almost no site-to-site variation to use. This script reruns the
registered folds, grids, pruning and seen-project setting with one change: each fold subtracts the mean
embedding of its own training sites before row normalisation. All other models are unchanged.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import tempfile

import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize

import evaluate
from summarize import write_rows

VIEWS = ("full", "masked")


class CenteredInputs(evaluate.Inputs):
    def __init__(self, train, vectors):
        super().__init__(train, vectors)
        self.means = {v: np.mean([vectors[v][s.key] for s in train], axis=0) for v in VIEWS}

    def transform(self, sites):
        x = super().transform(sites)
        structural = normalize(self.structure.transform([s.structure() for s in sites]))
        for v in VIEWS:
            centered = np.stack([self.vectors[v][s.key] for s in sites]) - self.means[v]
            x[f"embedding_{v}"] = sparse.hstack([structural, normalize(centered)], format="csr")
        return x


def per_project(path):
    errors = defaultdict(list)
    with path.open() as stream:
        for r in csv.DictReader(stream):
            t, f = int(r["taken"]), int(r["fallthrough"])
            if t + f:
                errors[r["setting"], r["workload"], r["model"], r["project"]].append(abs(float(r["q"]) - t / (t + f)))
    return {k: float(np.mean(v)) for k, v in errors.items()}


def main(corpus, slm, out, config):
    evaluate.Inputs = CenteredInputs
    with tempfile.TemporaryDirectory() as tmp:
        evaluate.evaluate(corpus, slm, Path(tmp), config)
        mae = per_project(Path(tmp) / "predictions.csv")
        folds = json.loads((Path(tmp) / "folds.json").read_text())
    projects = config["projects"]
    draws = np.random.default_rng(config["seed"]).integers(len(projects), size=(config["bootstrap_draws"], len(projects)))
    rows = []
    for setting, workload in (("unseen", "normal"), ("unseen", "shift"), ("seen", "shift")):
        for model, reference in (("embedding_full", "lexical_ridge"), ("embedding_masked", "lexical_ridge"),
                                 ("embedding_full", "structural_ridge"), ("embedding_full", "embedding_masked")):
            a = np.array([mae[setting, workload, model, p] for p in projects])
            b = np.array([mae[setting, workload, reference, p] for p in projects])
            delta = a - b
            lo, hi = np.quantile(delta[draws].mean(axis=1), [.025, .975])
            rows.append(dict(setting=setting, workload=workload, model=f"centered_{model}", reference=reference,
                             macro_mae=a.mean(), reference_mae=b.mean(), mean_delta=delta.mean(), ci_low=lo, ci_high=hi,
                             projects_lower_mae=int((delta < 0).sum())))
    write_rows(out / "centered.csv", rows)
    choices = [dict(test=f["test"], embedding_full=f["choices"]["embedding_full"],
                    embedding_masked=f["choices"]["embedding_masked"]) for f in folds["unseen"]]
    write_rows(out / "centered_choices.csv", choices + [dict(test="seen", **{
        m: folds["seen_choices"][m] for m in ("embedding_full", "embedding_masked")})])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("slm", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, default=evaluate.ROOT / "experiments/study/config.json")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    main(args.corpus, args.slm, args.output, json.loads(args.config.read_text()))
