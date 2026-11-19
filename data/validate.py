"""Validate one original class and its complete set of workload profiles."""
import argparse
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).parent / "schema"


def read_rows(path, kind):
    schema = json.loads((SCHEMA / f"{kind}.schema.json").read_text())
    validator = Draft202012Validator(schema)
    with path.open() as src:
        for line_number, line in enumerate(src, 1):
            row = json.loads(line)
            error = next(validator.iter_errors(row), None)
            if error:
                raise ValueError(f"{path}:{line_number}: {error.message}")
            yield row


def load_examples(static_path, profiles):
    """Yield (site ID, static features, workload, label) after validating every join."""
    sites = {}
    for site in read_rows(static_path, "static"):
        key = site["branch_id"]
        expected = f'{site["artifact_sha256"]}:{site["method_index"]}:{site["original_bci"]}'
        if key != expected or key in sites:
            raise ValueError(f"Invalid or repeated site {key}")
        if site["fallthrough_bci"] != site["original_bci"] + 3:
            raise ValueError(f"Invalid conditional instruction length at {key}")
        sites[key] = site
    if len({s["artifact_sha256"] for s in sites.values()}) > 1:
        raise ValueError("Pilot inventory must describe a single original class")
    examples = []
    for workload, path in profiles.items():
        seen = set()
        for label in read_rows(path, "label"):
            key = label["branch_id"]
            if key not in sites or key in seen or label["workload_id"] != workload:
                raise ValueError(f"Invalid site/workload join {key} in {path}")
            seen.add(key)
            t, f, p = (label[k] for k in ("taken_count", "fallthrough_count", "p_taken"))
            if type(t) is not int or type(f) is not int:
                raise ValueError(f"Counts must be encoded as integer tokens at {key}")
            if t + f == 0:
                if p is not None:
                    raise ValueError(f"Unobserved site has probability at {key}")
            elif p is None or not math.isclose(p, t / (t + f), rel_tol=1e-15, abs_tol=0):
                raise ValueError(f"Probability disagrees with counts at {key}")
            site = sites[key]
            features = {k: site[k] for k in ("class_name", "method_name", "method_descriptor",
                                               "branch_opcode", "original_bci", "target_bci", "fallthrough_bci")}
            examples.append((key, features, workload, label))
        if seen != sites.keys():
            raise ValueError(f"Missing {len(sites.keys() - seen)} site(s) in {path}")
    return examples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    workloads = json.loads(args.config.read_text())["workloads"]
    profiles = {w: args.directory / f"{w}.jsonl" for w in workloads}
    rows = load_examples(args.directory / "static.jsonl", profiles)
    observed = sum(row[3]["p_taken"] is not None for row in rows)
    print(f"{len(rows)} site/workload pairs, {observed} observed, {len(rows)-observed} unobserved")
