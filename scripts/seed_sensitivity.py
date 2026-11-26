"""Summarize the five matched seed pairs described by the external protocol."""
import argparse
import csv
import itertools
import json
from pathlib import Path
from statistics import mean
import tempfile

from corpus import ROOT, read_rows, sha


def write(path, rows):
    with path.open("w", newline="") as stream:
        table = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        table.writeheader()
        table.writerows(rows)


def summarize(reruns, out):
    original = ROOT / "experiments/study/corpus"
    cfg = json.loads((ROOT / "experiments/configs/corpus.json").read_text())
    projects = [p["project"] for p in cfg["projects"]]
    counts, summaries, provenance = [], [], {}
    values = {}
    seeds = range(1516, 1521)
    for seed in seeds:
        directory = original if seed == 1516 else reruns / str(seed)
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest["seed"] != seed:
            raise ValueError("Wrong seed in trace manifest")
        provenance[seed] = dict(runtime=manifest["java_runtime"], vendor=manifest["java_vendor"],
                                sources=manifest["sources"], projects={})
        for project in projects:
            record = manifest["projects"][project]
            for name in ("static.jsonl", "context.jsonl"):
                if sha(directory/project/name) != sha(original/project/name):
                    raise ValueError(f"Static inventory changed for {project}")
            provenance[seed]["projects"][project] = dict(checks=record["checks"], files=record["files"])
            for size in ("normal","shift"):
                path = directory/project/f"{size}.jsonl"
                checks = record["checks"][size]
                if checks["reference_sha256"] != checks["instrumented_sha256"] or sha(path) != record["files"][path.name]:
                    raise ValueError(f"Trace verification failed for {seed}/{project}/{size}")
                for row in read_rows(path):
                    key = row["branch_id"]
                    values[project, key, size, seed] = row["p_taken"]
                    counts.append(dict(project=project, branch_id=key, workload=size, seed=seed,
                                       taken=row["taken_count"], fallthrough=row["fallthrough_count"]))
    for project in projects:
        inventory = read_rows(original/project/"static.jsonl")
        keys = [row["branch_id"] for row in inventory if all(values[project,row["branch_id"],w,s] is not None
                for w in ("normal","shift") for s in seeds)]
        mix = mean(abs(values[project,k,"normal",s]-values[project,k,"shift",s]) for k in keys for s in seeds)
        same = [mean(abs(values[project,k,w,s]-values[project,k,w,t]) for k in keys
                     for s,t in itertools.combinations(seeds,2)) for w in ("normal","shift")]
        summaries.append(dict(project=project, sites=len(inventory), common_sites=len(keys),
                              matched_mixture_gap=mix, normal_seed_gap=same[0], shift_seed_gap=same[1],
                              within_mixture_seed_gap=mean(same)))
    out.mkdir()
    write(out/"counts.csv", counts)
    write(out/"project_metrics.csv", summaries)
    (out/"manifest.json").write_text(json.dumps(provenance,indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reruns", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        staged = Path(tmp)/"result"
        summarize(args.reruns, staged)
        staged.rename(args.output)
