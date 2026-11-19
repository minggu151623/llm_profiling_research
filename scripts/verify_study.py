"""Check published corpus, predictions, denominators, macro MAE and joined workload invariants."""
import argparse
import csv
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(corpus, slm, evaluation, config):
    projects=config["projects"]
    corpus_meta=json.loads((corpus/"manifest.json").read_text())
    inference=json.loads((slm/"manifest.json").read_text())
    expected, probabilities, label_data = set(), {}, {}
    for p in projects:
        manifest=corpus_meta["projects"][p]
        for w in ["normal","shift"]:
            behavior=manifest["checks"][w]
            require(behavior["reference_sha256"] == behavior["instrumented_sha256"], f"Behavior mismatch for {p}/{w}")
        for n,h in manifest["files"].items():
            require(digest(corpus/p/n)==h, f"Corpus digest mismatch for {p}/{n}")
        for n in ["static.jsonl","context.jsonl"]:
            require(inference["input_sha256"][f"{p}/{n}"]==digest(corpus/p/n),f"Inference provenance differs: {p}/{n}")
        ids=[json.loads(l)["branch_id"] for l in (corpus/p/"static.jsonl").read_text().splitlines()]
        selected=sorted(ids,key=lambda k:hashlib.sha256(f'{config["seed"]}:{k}'.encode()).digest())[:config["max_sites_per_project"]]
        expected.update((p,k) for k in selected)
        for w in ["normal","shift"]:
            for line in (corpus/p/f"{w}.jsonl").read_text().splitlines():
                r=json.loads(line)
                label_data[p,r["branch_id"],w]=r["taken_count"],r["fallthrough_count"]
    for n,h in inference["outputs_sha256"].items():
        require(digest(slm/n)==h,f"SLM digest mismatch for {n}")
    for line in (slm/"predictions.jsonl").read_text().splitlines():
        r=json.loads(line); probabilities[r["project_id"],r["branch_id"]]=r
    require(expected==probabilities.keys(), "SLM coverage mismatch")
    models={"uniform","backward_taken","structural_ridge","structural_xgb","lexical_ridge",
            "zero_full","zero_masked","embedding_full","embedding_masked"}
    aggregates=defaultdict(list)
    seen, values=set(),{}
    with (evaluation/"predictions.csv").open() as src:
        for r in csv.DictReader(src):
            p,k,w,m,setting=(r[n] for n in ["project","branch_id","workload","model","setting"])
            key=(p,k,w,m,setting)
            require(key not in seen and (p,k) in expected and m in models and (setting,w) in
                    {("unseen","normal"),("unseen","shift"),("seen","shift")},f"Unexpected prediction {key}")
            seen.add(key)
            t,f=(int(r[n]) for n in ["taken","fallthrough"])
            q=float(r["q"])
            require((t,f)==label_data[p,k,w] and 0<=q<=1,f"Label or prediction invalid for {key}")
            if m.startswith("zero_"):
                require(q==probabilities[p,k]["q_"+m.split("_")[1]],f"Zero-shot readout mismatch for {key}")
            if setting=="unseen":
                old=values.setdefault((p,k,m),q)
                require(old==q, f"Workload-sensitive static prediction {key}")
            if t+f:
                aggregates[setting,w,m,p].append(abs(t/(t+f)-q))
    require(len(seen)==len(expected)*len(models)*3,"Missing site/model/setting rows")
    with (evaluation/"metrics.csv").open() as src:
        summaries=list(csv.DictReader(src))
    require(len(summaries)==len(models)*3,"Missing model summaries")
    for r in summaries:
        grouped=[aggregates[r["setting"],r["workload"],r["model"],p] for p in projects]
        mae=sum(sum(g)/len(g) for g in grouped)/len(grouped)
        require(math.isclose(mae,float(r["macro_mae"]),abs_tol=1e-12) and
                sum(map(len,grouped))==int(r["sites"]),f"Metric mismatch for {r['model']}")
    print(f"Verified {len(projects)} projects, {len(expected)} static predictions per model, "
          f"{len(seen)} joined evaluation rows and {len(summaries)} aggregate rows.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ["corpus","slm","evaluation"]:
        parser.add_argument(name,type=Path)
    parser.add_argument("--config",type=Path,default=Path(__file__).resolve().parents[1]/"experiments/study/config.json")
    args=parser.parse_args()
    verify(args.corpus,args.slm,args.evaluation,json.loads(args.config.read_text()))
