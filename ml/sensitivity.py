"""Exploratory paired contrasts, support sensitivity and seen-project persistence comparator."""
from collections import defaultdict
import argparse
import csv
import json
from pathlib import Path
import numpy as np

from summarize import write_rows


def analyze(table, out, config):
    per_site = defaultdict(dict)
    by_key = {}
    with table.open() as f:
        for r in csv.DictReader(f):
            if r["setting"] != "unseen":
                continue
            project,key,w=r["project"],r["branch_id"],r["workload"]
            t,f=int(r["taken"]),int(r["fallthrough"])
            by_key[project,key,w]=(t,f)
            per_site[project,key,w][r["model"]]=float(r["q"])
    contrasts=[("embedding_full","embedding_masked"),("zero_full","zero_masked"),
               ("embedding_full","lexical_ridge"),("zero_full","lexical_ridge")]
    draws=np.random.default_rng(config["seed"]).integers(len(config["projects"]),size=(config["bootstrap_draws"],len(config["projects"])))
    rows=[]
    for support in (1,20):
        for a,b in contrasts:
            per_project = defaultdict(list)
            for (p,k,w),pred in per_site.items():
                t,f=by_key[p,k,w]
                if w=="normal" and t+f>=support:
                    y=t/(t+f)
                    per_project[p].append(abs(pred[a]-y)-abs(pred[b]-y))
            delta=np.array([np.mean(per_project[p]) for p in sorted(per_project)])
            if len(delta)!=len(config["projects"]):
                raise ValueError("Insufficient project coverage for support sensitivity")
            lo,hi=np.quantile(delta[draws].mean(axis=1),[.025,.975])
            rows.append(dict(minimum_support=support,model=a,reference=b,projects=len(delta),
                             sites=sum(map(len,per_project.values())),macro_delta=delta.mean(),ci_low=lo,ci_high=hi))
    write_rows(out/"sensitivity.csv",rows)
    persistence=[]
    for p in config["projects"]:
        error=[]
        for project,k,w in per_site:
            if project!=p or w!="normal": continue
            t0,f0=by_key[p,k,"normal"]
            t1,f1=by_key[p,k,"shift"]
            if (t0+f0) and (t1+f1):
                error.append(abs(t0/(t0+f0)-t1/(t1+f1)))
        persistence.append(dict(project=p,paired_sites=len(error),normal_label_persistence_mae=np.mean(error),
                                equal_workload_mae_floor=np.mean(error)/2))
    write_rows(out/"persistence.csv",persistence)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--config",type=Path,default=Path(__file__).resolve().parents[1]/"experiments/study/config.json")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    analyze(args.predictions,args.output,json.loads(args.config.read_text()))
