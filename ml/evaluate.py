"""Evaluate the preregistered unseen-project folds and the separate seen-project shift setting."""
import argparse
import csv
import json
import platform
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path
import tempfile
import time

import numpy as np
from scipy import sparse
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import normalize
from xgboost import XGBRegressor

from study_data import ROOT, load_corpus, prune, read_model

MODELS = ["uniform", "backward_taken", "structural_ridge", "structural_xgb", "lexical_ridge",
          "zero_full", "zero_masked", "embedding_full", "embedding_masked"]
FITTED = MODELS[2:5] + MODELS[7:]


def dump_csv(path, rows):
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Inputs:
    """Fit numeric and textual coordinate systems on training sites only."""
    def __init__(self, train, vectors):
        self.structure = DictVectorizer().fit([s.structure() for s in train])
        self.vocab = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), sublinear_tf=True,
                                     lowercase=False).fit(s.text() for s in train)
        self.vectors = vectors

    def transform(self, sites):
        raw = self.structure.transform([s.structure() for s in sites])
        structural = normalize(raw)
        x = {"structural_ridge": structural, "structural_xgb": raw,
             "lexical_ridge": sparse.hstack([structural, self.vocab.transform(s.text() for s in sites)], format="csr")}
        for name in ("full", "masked"):
            embeddings = np.stack([self.vectors[name][s.key] for s in sites])
            x[f"embedding_{name}"] = sparse.hstack([structural, normalize(embeddings)], format="csr")
        return x


def fit_regressor(model, value, config, x, y):
    if model == "structural_xgb":
        # Dense zeros denote genuine feature absence for tree splits.
        reg = XGBRegressor(max_depth=value, n_estimators=config["xgb_trees"], learning_rate=config["xgb_rate"],
                           objective="reg:squarederror", random_state=config["seed"], n_jobs=1, tree_method="hist")
        return reg.fit(x.toarray(), y)
    return Ridge(alpha=value, solver="lsqr", tol=1e-6).fit(x, y)


def estimate(reg, x, name):
    return np.clip(reg.predict(x.toarray() if name == "structural_xgb" else x), 0., 1.)


def targets(sites):
    return np.array([s.labels["normal"]["p_taken"] for s in sites])


def observed(sites):
    return [s for s in sites if s.selected and s.labels["normal"]["p_taken"] is not None]


def score_fold(train, val, test, slm, vectors, config, selected=None):
    features = Inputs(train, vectors)
    xtrain, xtest = features.transform(train), features.transform(test)
    xval = features.transform(val) if val else {}
    ytrain, yval = targets(train), targets(val)
    scores = {"uniform": [0.5] * len(test),
              "backward_taken": [float(s.static["target_bci"] < s.static["original_bci"]) for s in test],
              "zero_full": [slm[s.key]["q_full"] for s in test],
              "zero_masked": [slm[s.key]["q_masked"] for s in test]}
    selections = {}
    for model in FITTED:
        candidates = config["xgb_depth" if model == "structural_xgb" else "ridge_alpha"]
        if selected is not None:
            candidates = [selected[model]]
        best_loss = float("inf")
        for parameter in candidates:
            reg = fit_regressor(model, parameter, config, xtrain[model], ytrain)
            loss = float(np.mean(np.abs(estimate(reg, xval[model], model) - yval))) if val else 0.
            if loss < best_loss:
                best_loss = loss
                scores[model] = estimate(reg, xtest[model], model)
                selections[model] = parameter
    return scores, selections


def predict_rows(test, scores, setting, workloads):
    for i, site in enumerate(test):
        for w in workloads:
            label = site.labels[w]
            for name in MODELS:
                yield dict(setting=setting, project=site.project, workload=w, branch_id=site.key,
                           opcode=site.static["branch_opcode"], model=name, q=float(scores[name][i]),
                           taken=label["taken_count"], fallthrough=label["fallthrough_count"])


def evaluate(corpus, slm_path, out, config):
    sites = load_corpus(corpus, config)
    slm, vectors = read_model(slm_path, sites)
    results, audits, exclusions, params = [], [], [], defaultdict(list)
    for fold in config["folds"]:
        test_inventory = [s for s in sites if s.project == fold["test"]]
        val_inventory = [s for s in sites if s.project == fold["validation"]]
        train = [s for s in sites if s.project in fold["train"]]
        train, rem_train = prune(train, test_inventory + val_inventory, config["near_duplicate_jaccard"])
        val, rem_val = prune(val_inventory, test_inventory, config["near_duplicate_jaccard"])
        train, val = observed(train), observed(val)
        test = [s for s in test_inventory if s.selected]
        if not train or not val or not test:
            raise ValueError(f"Empty fold after static deduplication and observation filtering: {fold}")
        scores, choices = score_fold(train, val, test, slm, vectors, config)
        for model, parameter in choices.items():
            params[model].append(parameter)
        audits.append(dict(test=fold["test"], validation=fold["validation"], train_sites=len(train),
                           validation_sites=len(val), test_static=len(test), choices=choices))
        for side, dropped in (("train", rem_train), ("validation", rem_val)):
            exclusions.extend(dict(test=fold["test"], partition=side, branch_id=k, reason=r) for k,r in dropped.items())
        results.extend(predict_rows(test, scores, "unseen", ("normal", "shift")))
    choices = {}
    for model, values in params.items():
        grid = config["xgb_depth" if model == "structural_xgb" else "ridge_alpha"]
        choices[model] = min(grid, key=lambda value: abs(value - np.median(values)))
    selected = [s for s in sites if s.selected]
    scores, _ = score_fold(observed(sites), [], selected, slm, vectors, config, choices)
    results.extend(predict_rows(selected, scores, "seen", ("shift",)))
    dump_csv(out / "predictions.csv", results)
    (out / "folds.json").write_text(json.dumps(dict(unseen=audits, seen_choices=choices, duplicate_exclusions=exclusions),indent=2)+"\n")
    coverage = []
    for project in config["projects"]:
        group = [s for s in sites if s.project == project]
        for sample, subgroup in (("inventory", group), ("preselected", [s for s in group if s.selected])):
            for workload in ("normal", "shift"):
                labels = [s.labels[workload] for s in subgroup]
                coverage.append(dict(project=project, population=sample, workload=workload, sites=len(labels),
                                     observed=sum(l["p_taken"] is not None for l in labels),
                                     executions=sum(l["taken_count"]+l["fallthrough_count"] for l in labels)))
    dump_csv(out / "coverage.csv",coverage)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corpus", type=Path)
    p.add_argument("slm", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--config", type=Path, default=ROOT / "experiments/study/config.json")
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a fresh output directory")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        out = Path(tmp) / "result"
        out.mkdir()
        start = time.perf_counter()
        evaluate(args.corpus, args.slm, out, json.loads(args.config.read_text()))
        from summarize import summarize
        summarize(out, json.loads(args.config.read_text()))
        from importlib.util import find_spec
        packages = ["numpy","scipy","scikit-learn"]
        packages.append("xgboost-cpu" if platform.system()=="Linux" else "xgboost")
        (out/"run.json").write_text(json.dumps({"system":platform.platform(),"python":platform.python_version(),
              "packages":{p:version(p) for p in packages},"wall_seconds":time.perf_counter()-start},indent=2)+"\n")
        out.rename(args.output)
