"""Descriptive, not preregistered: pooled RMSE of the unseen-project predictions.

Related work on Graal IR static profiling reports held-out RMSE rather than project-macro MAE. This script
gives the same statistic for our sites so the scales can be read side by side. It pools the observed sites
of all eight held-out projects, once with equal site weights and once with each site weighted by its share
of its project's branch executions, so that every project carries the same total weight.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

from summarize import write_rows


def rmse(table):
    errors = defaultdict(list)
    with table.open() as f:
        for r in csv.DictReader(f):
            t, n = int(r["taken"]), int(r["taken"]) + int(r["fallthrough"])
            if r["setting"] == "unseen" and n:
                errors[r["workload"], r["model"]].append((r["project"], (float(r["q"]) - t / n) ** 2, n))
    rows = []
    for (workload, model), e in sorted(errors.items()):
        totals = defaultdict(int)
        for project, _, n in e:
            totals[project] += n
        weighted = sum(x * n / totals[p] for p, x, n in e) / len(totals)
        rows.append(dict(workload=workload, model=model, sites=len(e),
                         rmse=math.sqrt(sum(x for _, x, _ in e) / len(e)),
                         execution_share_rmse=math.sqrt(weighted)))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    write_rows(args.output / "rmse.csv", rmse(args.predictions))
