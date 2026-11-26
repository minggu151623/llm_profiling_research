"""Post-hoc comparison of opcode medians and lexical ridge with frozen 0.49B embeddings.

Run from the repository root: python ml/review_baselines.py. Use the evaluation environment.
"""
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np
from scipy import sparse

from evaluate import Inputs, estimate, fit_regressor, observed, targets
from study_data import load_corpus, prune, read_model

def main():
    study = Path("experiments/study")
    config = json.loads((study / "config.json").read_text())
    sites = load_corpus(study / "corpus", config)
    _, vectors = read_model(study / "slm", sites)
    with (study / "evaluation/predictions.csv").open() as stream:
        reference = {
            row["branch_id"]: float(row["q"])
            for row in csv.DictReader(stream)
            if (row["setting"], row["workload"], row["model"]) == ("unseen", "normal", "lexical_ridge")
        }

    scores = {"normal": [], "shift": []}
    max_error = 0.0
    for fold in config["folds"]:
        test = [site for site in sites if site.project == fold["test"]]
        val = [site for site in sites if site.project == fold["validation"]]
        train = [site for site in sites if site.project in fold["train"]]
        threshold = config["near_duplicate_jaccard"]
        train = observed(prune(train, val + test, threshold)[0])
        val = observed(prune(val, test, threshold)[0])
        test = observed(test)
        features = Inputs(train, vectors)
        matrices = []
        for group in (train, val, test):
            blocks = features.transform(group)
            lexical = blocks["lexical_ridge"]
            embeddings = blocks["embedding_full"][:, blocks["structural_ridge"].shape[1]:]
            matrices.append((lexical, sparse.hstack([lexical, embeddings], format="csr")))
        predictions = []
        for train_x, val_x, test_x in zip(*matrices):
            candidates = []
            for alpha in config["ridge_alpha"]:
                model = fit_regressor("lexical_ridge", alpha, config, train_x, targets(train))
                val_q = estimate(model, val_x, "lexical_ridge")
                candidates.append((np.mean(np.abs(val_q - targets(val))), model))
            selected = min(candidates, key=lambda candidate: candidate[0])[1]
            predictions.append(estimate(selected, test_x, "lexical_ridge"))
        max_error = max(max_error, max(abs(predictions[0][i] - reference[site.key]) for i, site in enumerate(test)))
        train_by_opcode = defaultdict(list)
        for site in train:
            train_by_opcode[site.static["branch_opcode"]].append(site.labels["normal"]["p_taken"])
        medians = {opcode: np.median(values) for opcode, values in train_by_opcode.items()}
        fallback = np.median(targets(train))
        predictions.append(np.array([medians.get(site.static["branch_opcode"], fallback) for site in test]))
        for workload in scores:
            labels = np.array([site.labels[workload]["p_taken"] for site in test])
            assert np.isfinite(labels).all()
            scores[workload].append([np.mean(np.abs(q - labels)) for q in predictions])
    print("Maximum deviation from published lexical predictions", max_error)
    assert max_error < 1e-4
    for workload, rows in scores.items():
        matrix = np.array(rows)
        n = len(rows)
        draws = np.random.default_rng(config["seed"]).integers(n, size=(config["bootstrap_draws"], n))
        print(workload, "macro MAE (lexical, lexical+embedding, opcode median):", matrix.mean(axis=0))
        for column, name in ((1, "lexical+embedding"), (2, "opcode median")):
            delta = matrix[:, column] - matrix[:, 0]
            interval = np.quantile(delta[draws].mean(axis=1), [0.025, 0.975])
            print(name, "minus lexical:", delta.mean(), "paired interval:", interval,
                  "projects with lower MAE:", (delta < 0).sum(), "of", n)


if __name__ == "__main__":
    main()
