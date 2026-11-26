"""Score the frozen DaCapo transfer protocol using fits on the eight-library corpus."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize

from evaluate import Inputs, estimate, fit_regressor, observed, targets
from study_data import ROOT, load_corpus, prune, read_model
from summarize import write_rows
from validate import load_examples

STUDY = ROOT / "experiments/study"
APPS = ("luindex", "pmd", "xalan", "sunflow")
SIZES = ("small", "default")


def matrices(inputs, sites):
    x = inputs.transform(sites)
    vectors = normalize(np.stack([inputs.vectors["full"][s.key] for s in sites]))
    x["lexical_plus_embedding"] = sparse.hstack([x["lexical_ridge"], vectors], format="csr")
    return x


def score(corpus, slm_path, out):
    cfg = json.loads((STUDY/"config.json").read_text())
    training = load_corpus(STUDY/"corpus", cfg)
    test = load_corpus(corpus, {**cfg, "projects": APPS}, SIZES, single_class=False)
    _, train_vec = read_model(STUDY/"slm", training)
    slm, test_vec = read_model(slm_path, test)
    manifest = json.loads((slm_path/"manifest.json").read_text())
    if manifest["revision"] != json.loads((STUDY/"slm/manifest.json").read_text())["revision"]:
        raise ValueError("Checkpoint does not match the registered model")
    for path, digest in manifest["input_sha256"].items():
        if hashlib.sha256((corpus/path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Inference input mismatch for {path}")
    train, removed = prune(observed(training), test, cfg["near_duplicate_jaccard"])
    class_overlap = {s.static["artifact_sha256"] for s in training} & {s.static["artifact_sha256"] for s in test}
    if class_overlap:
        raise ValueError("External branch class overlaps training")
    input_data = Inputs(train, {view: {**train_vec[view], **test_vec[view]} for view in train_vec})
    train_x, test_x = matrices(input_data, train), matrices(input_data, test)
    y = targets(train)
    choices = json.loads((STUDY/"evaluation/folds.json").read_text())["seen_choices"]
    choices = {k: choices[k] for k in ("structural_ridge","structural_xgb","lexical_ridge","embedding_full")}
    choices["lexical_plus_embedding"] = choices["lexical_ridge"]
    opcode_y = {}
    for site, value in zip(train, y, strict=True):
        opcode_y.setdefault(site.static["branch_opcode"], []).append(value)
    medians = {k: np.median(v) for k, v in opcode_y.items()}
    fallback = np.median(y)
    predictions = {"uniform": np.full(len(test), 0.5),
                   "opcode_median": np.array([medians.get(s.static["branch_opcode"], fallback) for s in test]),
                   "zero_full": np.array([slm[s.key]["q_full"] for s in test])}
    for model, alpha in choices.items():
        reg = fit_regressor(model, alpha, cfg, train_x[model], y)
        predictions[model] = estimate(reg, test_x[model], model)
    out.mkdir()
    write_rows(out/"predictions.csv", [dict(application=s.project, branch_id=s.key,
               **{m: float(q[i]) for m,q in predictions.items()}) for i,s in enumerate(test)])
    coverage, metrics, floors = [], [], []
    for app in APPS:
        app_ids = [i for i,s in enumerate(test) if s.project == app]
        pop = json.loads((corpus/app/"population.json").read_text())
        if len(app_ids) != min(96, pop["eligible_sites"]):
            raise ValueError(f"Unexpected sample size in {app}")
        repeated = {(k,w): label for k,_,w,label in load_examples(corpus/app/"static.jsonl",
                       {w: corpus/app/f"{w}-repeat.jsonl" for w in SIZES}, single_class=False)}
        for w in SIZES:
            obs = [i for i in app_ids if test[i].labels[w]["p_taken"] is not None]
            changed = sum(test[i].labels[w] != repeated[test[i].key, w] for i in app_ids)
            support = dict(eligible=pop["eligible_sites"], sampled=len(app_ids), observed=len(obs),
                           covered_classes=len({test[i].static["class_name"] for i in obs}),
                           covered_methods=len({(test[i].static["class_name"],test[i].static["method_index"]) for i in obs}),
                           sampled_backward=sum(test[i].static["target_bci"] < test[i].static["original_bci"] for i in app_ids),
                           observed_backward=sum(test[i].static["target_bci"] < test[i].static["original_bci"] for i in obs),
                           repeat_count_differences=changed)
            coverage.append(dict(application=app, workload=w, **support))
            if obs:
                actual = np.array([test[i].labels[w]["p_taken"] for i in obs])
                metrics.extend(dict(application=app, workload=w, model=m, sites=len(obs),
                                    mae=float(np.mean(abs(q[obs]-actual)))) for m,q in predictions.items())
        gaps = [abs(s.labels["default"]["p_taken"] - s.labels["small"]["p_taken"]) / 2
                for s in (test[i] for i in app_ids) if all(s.labels[w]["p_taken"] is not None for w in SIZES)]
        floors.append(dict(application=app, common_sites=len(gaps), floor=np.mean(gaps) if gaps else None))
    totals = []
    for w in SIZES:
        lookup = {(r["model"],r["application"]): r["mae"] for r in metrics if r["workload"] == w}
        apps = [a for a in APPS if ("lexical_ridge",a) in lookup]
        if not apps:
            continue
        for model in predictions:
            errors = np.array([lookup[model,a] for a in apps])
            delta = errors - [lookup["lexical_ridge",a] for a in apps]
            omit_one = [np.delete(delta,i).mean() for i in range(len(apps))] if len(apps)>1 else []
            totals.append(dict(workload=w, model=model, applications=len(apps), macro_mae=errors.mean(),
                               delta_vs_lexical=delta.mean(), omit_one_min=min(omit_one,default=None),
                               omit_one_max=max(omit_one,default=None)))
    write_rows(out/"project_metrics.csv", metrics)
    write_rows(out/"coverage.csv", coverage)
    write_rows(out/"macro.csv", totals)
    write_rows(out/"floor.csv", floors)
    (out/"fit.json").write_text(json.dumps(dict(choices=choices, training_sites=len(train),
        shared_class_hashes=sorted(class_overlap), removed_train=removed, reasons=Counter(removed.values())),indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("corpus", "slm", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        staged = Path(tmp)/"evaluation"
        score(args.corpus, args.slm, staged)
        staged.rename(args.output)
