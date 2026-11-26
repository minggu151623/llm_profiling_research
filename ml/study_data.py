"""Join site labels by immutable original bytecode ID, and expose only static model features."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
from validate import load_examples


@dataclass
class Site:
    project: str
    key: str
    context: dict
    static: dict
    labels: dict
    selected: bool
    window: frozenset

    def structure(self):
        site = self.static
        ops = self.context["opcodes"]
        center = next(i for i, line in enumerate(self.context["context"].splitlines())
                      if line.lstrip().startswith(">>"))
        if ops[center].upper() != site["branch_opcode"]:
            raise ValueError(f"Focal opcode mismatch for {self.key}")
        counts = Counter(op.upper() for op in ops)
        delta = site["target_bci"] - site["original_bci"]
        values = {"site": site["branch_opcode"], "backwards": float(delta < 0),
                  "log_distance": math.log1p(abs(delta)), "log_bci": math.log1p(site["original_bci"])}
        values.update({f"count_{op}": n for op, n in counts.items()})
        values.update({f"offset_{i-center}": op for i, op in enumerate(ops)})
        return values

    def text(self):
        return " ".join([self.static[k] for k in ("class_name", "method_name", "method_descriptor")]
                        + [self.context["context"]])


def read_index(path):
    records = {}
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            key = row["branch_id"]
            if key in records:
                raise ValueError(f"Duplicate ID in {path}: {key}")
            records[key] = row
    return records


def load_corpus(corpus, config, workloads=("normal", "shift"), *, single_class=True):
    sites = []
    for project in config["projects"]:
        directory = corpus / project
        inventory = read_index(directory / "static.jsonl")
        contexts = read_index(directory / "context.jsonl")
        if inventory.keys() != contexts.keys():
            raise ValueError(f"{project}: context inventory mismatch")
        selected = set(sorted(inventory, key=lambda k: hashlib.sha256(
            (str(config["seed"]) + ":" + k).encode()).digest())[:config["max_sites_per_project"]])
        profiles = {w: directory / f"{w}.jsonl" for w in workloads}
        labels = {key: {} for key in inventory}
        for key, _, workload, label in load_examples(directory / "static.jsonl", profiles, single_class=single_class):
            labels[key][workload] = label
        for key, static in inventory.items():
            ops = tuple(contexts[key]["opcodes"])
            if not ops:
                raise ValueError(f"Empty context for {key}")
            window = frozenset(zip(ops, ops[1:], ops[2:])) if len(ops) >= 3 else frozenset([ops])
            sites.append(Site(project, key, contexts[key], static, labels[key], key in selected, window))
    if len(sites) != len({s.key for s in sites}):
        raise ValueError("Identical artifact and branch IDs occur in multiple project families")
    return sites


def read_model(path, sites):
    predictions = read_index(path / "predictions.jsonl")
    selected = {s.key: s.project for s in sites if s.selected}
    with np.load(path / "embeddings.npz", allow_pickle=False) as data:
        keys = data["branch_id"].astype(str).tolist()
        projects = data["project_id"].astype(str).tolist()
        if len(keys) != len(set(keys)) or set(keys) != selected.keys() or predictions.keys() != selected.keys():
            raise ValueError("Expected every preselected site to have its predictions and representations")
        if projects != [selected[key] for key in keys]:
            raise ValueError("Embedding project IDs do not match the site inventory")
        vectors = {}
        for name in ("full", "masked"):
            matrix = data[name]
            if matrix.shape != (len(keys), 896):
                raise ValueError(f"Invalid {name} embedding shape {matrix.shape}; expected a 896-vector per site")
            vectors[name] = dict(zip(keys, matrix.astype(np.float32), strict=True))
    for key, row in predictions.items():
        if row["project_id"] != selected[key] or not all(
                0 <= row[f"q_{name}"] <= 1 and np.isfinite(vectors[name][key]).all() for name in vectors):
            raise ValueError(f"Invalid SLM output at {key}")
    return predictions, vectors


def prune(candidates, held_out, threshold):
    hashes = {s.context["method_hash"] for s in held_out}
    windows = {s.window for s in held_out}
    kept, rejected = [], {}
    for site in candidates:
        if site.context["method_hash"] in hashes:
            rejected[site.key] = "method_opcodes"
        elif any(len(site.window & w) >= threshold * len(site.window | w) for w in windows):
            rejected[site.key] = "local_opcode_trigrams"
        else:
            kept.append(site)
    return kept, rejected
