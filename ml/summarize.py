"""Summaries derived from paired predictions and measured counts."""
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


def write_rows(path, rows):
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def groups(rows, keys):
    result = defaultdict(list)
    for r in rows:
        result[tuple(r[k] for k in keys)].append(r)
    return result


def metrics(rows):
    t = np.array([r["taken"] for r in rows])
    f = np.array([r["fallthrough"] for r in rows])
    q = np.array([r["q"] for r in rows])
    n = t + f
    p = t / n
    return dict(sites=len(n), executions=int(n.sum()), mae=np.mean(abs(p-q)),
                weighted_mae=np.average(abs(p-q), weights=n),
                brier=np.sum(t*(1-q)**2 + f*q**2)/n.sum())


def summarize(out: Path, config):
    with (out / "predictions.csv").open() as src:
        data = [{**r,"taken":int(r["taken"]),"fallthrough":int(r["fallthrough"]),"q":float(r["q"])}
                for r in csv.DictReader(src)]
    observed = [r for r in data if r["taken"] + r["fallthrough"] > 0]
    keys = ["setting","workload","model","project"]
    projects = [dict(zip(keys, group), **metrics(rows)) for group, rows in groups(observed,keys).items()]
    write_rows(out/"project_metrics.csv",projects)
    draws = np.random.default_rng(config["seed"]).integers(len(config["projects"]),
                            size=(config["bootstrap_draws"],len(config["projects"])))
    totals, contrasts, reliability = [], [], []
    for group, rows in groups(projects,keys[:3]).items():
        row = dict(zip(keys,group))
        basis = sorted(rows,key=lambda r:r["project"])
        if [r["project"] for r in basis]!=sorted(config["projects"]):
            raise ValueError("Missing project for macro aggregation")
        scores = np.array([r["mae"] for r in basis])
        lo,hi = np.quantile(scores[draws].mean(axis=1),[.025,.975])
        totals.append({**row,"projects":len(basis),"sites":sum(r["sites"] for r in basis),
                       "macro_mae":scores.mean(),"ci_low":lo,"ci_high":hi,
                       "macro_weighted_mae":np.mean([r["weighted_mae"] for r in basis]),
                       "macro_execution_brier":np.mean([r["brier"] for r in basis])})
        others = {r["project"]:r["mae"] for r in projects if r["setting"]==row["setting"] and
                  r["workload"]==row["workload"] and r["model"]=="lexical_ridge"}
        diff = scores - [others[r["project"]] for r in basis]
        lo,hi = np.quantile(diff[draws].mean(axis=1),[.025,.975])
        contrasts.append({**row,"reference":"lexical_ridge","mean_delta":diff.mean(),"ci_low":lo,"ci_high":hi,
                          "projects_lower_mae":int((diff<0).sum())})
    write_rows(out/"metrics.csv",totals)
    write_rows(out/"paired_deltas.csv",contrasts)
    for r in observed:
        r["bin"] = min(9,int(10*r["q"]))
    for group,rows in groups(observed,keys[:3]+["bin"]).items():
        reliability.append(dict(zip(keys[:3]+["bin"],group),sites=len(rows),
                                mean_q=np.mean([r["q"] for r in rows]),
                                measured=np.mean([r["taken"]/(r["taken"]+r["fallthrough"]) for r in rows])))
    write_rows(out/"calibration.csv",reliability)
    strata=keys[:3]+["opcode"]
    write_rows(out/"opcode_metrics.csv",[dict(zip(strata,g),**metrics(rs)) for g,rs in groups(observed,strata).items()])
    common=defaultdict(dict)
    for r in observed:
        if r["setting"]=="unseen" and r["model"]=="uniform":
            common[(r["project"],r["branch_id"])][r["workload"]]=r["taken"]/(r["taken"]+r["fallthrough"])
    shifts=[dict(project=p,branch_id=k,**pair,absolute_shift=abs(pair["normal"]-pair["shift"]),
                 equal_weight_mae_floor=abs(pair["normal"]-pair["shift"])/2)
            for (p,k),pair in common.items() if len(pair)==2]
    write_rows(out/"workload_shift.csv",shifts)
