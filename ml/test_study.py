"""Independent checks on the study protocol, joins and estimators using invented observations."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from evaluate import MODELS, observed, predict_rows, validate_folds
from study_data import ROOT, Site, prune, read_model
from summarize import metrics, summarize, write_rows


def toy_site(project, key, method_hash, window):
    return Site(project=project, key=key, selected=True, context={"method_hash": method_hash},
                window=frozenset(window), static={"branch_opcode": "IFGE"}, labels={})


def label(t, f):
    return dict(taken_count=t, fallthrough_count=f, p_taken=t/(t+f) if t+f else None)


class SplitTest(unittest.TestCase):
    def test_registered_fold_partition_and_holdout_rotation(self):
        config = json.loads((ROOT / "experiments/study/config.json").read_text())
        validate_folds(config)
        duplicate_test = copy.deepcopy(config)
        duplicate_test["folds"][-1] = duplicate_test["folds"][0]
        overlaps = copy.deepcopy(config)
        overlaps["folds"][0]["train"][0] = overlaps["folds"][0]["test"]
        wrong_order = copy.deepcopy(config)
        fold = wrong_order["folds"][0]
        fold["validation"], fold["train"][0] = fold["train"][0], fold["validation"]
        for bad in (duplicate_test, overlaps, wrong_order):
            with self.subTest(config=bad), self.assertRaises(ValueError):
                validate_folds(bad)

    def test_method_hash_or_jaccard_threshold_removes_candidate_only(self):
        held_out = [toy_site("test", "held", "same", range(10))]
        exact = toy_site("train", "exact", "same", [999])
        at_threshold = toy_site("train", "same-window", "other", range(9))
        below_threshold = toy_site("train", "keep", "other2", range(8))
        kept, removed = prune([exact, at_threshold, below_threshold], held_out, 0.9)
        self.assertEqual([s.key for s in kept], ["keep"])
        self.assertEqual(removed, {"exact": "method_opcodes", "same-window": "local_opcode_trigrams"})
        self.assertEqual([s.key for s in held_out], ["held"])

    def test_score_is_workload_blind_and_zero_support_retained_in_rows(self):
        site = toy_site("public", "one", "hash", [])
        site.labels = {"normal": label(1, 1), "shift": label(0, 0)}
        dormant = toy_site("public", "two", "hash2", [])
        dormant.labels = {"normal": label(0, 0), "shift": label(1, 0)}
        self.assertEqual([s.key for s in observed([site, dormant])], ["one"])
        scores = {m: [0.25, 0.375] for m in MODELS}
        rows = list(predict_rows([site, dormant], scores, "unseen", ("normal", "shift")))
        self.assertEqual(len(rows), 4 * len(MODELS))
        for model in MODELS:
            result = {(r["branch_id"], r["workload"]): (r["q"], r["taken"], r["fallthrough"])
                      for r in rows if r["model"] == model}
            self.assertEqual(result, {("one", "normal"): (.25, 1, 1), ("one", "shift"): (.25, 0, 0),
                                      ("two", "normal"): (.375, 0, 0), ("two", "shift"): (.375, 1, 0)})


class ModelJoinTest(unittest.TestCase):
    def test_prediction_and_embedding_ids_and_dimensions(self):
        sites = [toy_site("aa", "site-a", "ha", []), toy_site("bb", "site-b", "hb", [])]
        preds = [dict(branch_id=s.key, project_id=s.project, q_full=0.3, q_masked=0.4) for s in sites]
        # Embedding rows intentionally reversed against predictions.
        matrix = np.stack([np.full(896, value, dtype=np.float16) for value in [0.5, 0.25]])
        valid = dict(branch_id=["site-b", "site-a"], project_id=["bb", "aa"], full=matrix, masked=matrix)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
            np.savez(path / "embeddings.npz", **valid)
            _, vectors = read_model(path, sites)
            self.assertEqual(vectors["full"]["site-a"][0], .25)
            for change in [dict(project_id=["aa", "bb"]), dict(branch_id=["site-a", "site-a"]),
                           dict(masked=np.ones((2, 895))), dict(full=np.full((2, 896), np.nan))]:
                np.savez(path / "embeddings.npz", **(valid | change))
                with self.subTest(keys=list(change)), self.assertRaises(ValueError):
                    read_model(path, sites)
            np.savez(path / "embeddings.npz", **valid)
            with (path / "predictions.jsonl").open("a") as output:
                output.write(json.dumps(preds[0]) + "\n")
            with self.assertRaises(ValueError):
                read_model(path, sites)


class MetricsTest(unittest.TestCase):
    def test_execution_brier_uses_event_outcomes(self):
        rows = [dict(taken=1, fallthrough=1, q=.5), dict(taken=3, fallthrough=0, q=0.)]
        result = metrics(rows)
        self.assertEqual((result["sites"], result["executions"]), (2, 5))
        self.assertAlmostEqual(result["mae"], .5)
        self.assertAlmostEqual(result["weighted_mae"], .6)
        self.assertAlmostEqual(result["brier"], (2 * .25 + 3) / 5)

    def test_equal_project_weight_and_paired_resampling(self):
        # Two sites in A, one in B. Against p=0 the paired MAE advantage is .125 in both groups.
        rows = []
        for project, ids, q in [("a", ["1", "2"], .25), ("b", ["3"], .75)]:
            for key in ids:
                for workload, t, f in [("normal", 0, 1), ("shift", 1, 0)]:
                    for model, score in [("uniform", .5), ("lexical_ridge", q), ("zero_full", q-.125)]:
                        rows.append(dict(project=project, branch_id=key, workload=workload, model=model,
                                         q=score, taken=t, fallthrough=f, opcode="IFGE", setting="unseen"))
        # A globally unobserved branch must drop from the primary denominator and paired shift.
        for w in ("normal", "shift"):
            for model in ("uniform", "lexical_ridge", "zero_full"):
                rows.append(dict(project="a", branch_id="absent", workload=w, model=model,
                                 q=0.0, taken=0, fallthrough=0, opcode="IFGE", setting="unseen"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            write_rows(path / "predictions.csv", rows)
            summarize(path, {"projects": ["a", "b"], "bootstrap_draws": 500, "seed": 42})

            def read(name):
                with (path / name).open() as source:
                    return list(csv.DictReader(source))

            macro = next(r for r in read("metrics.csv") if r["model"] == "lexical_ridge" and r["workload"] == "normal")
            self.assertEqual((macro["projects"], macro["sites"]), ("2", "3"))
            self.assertAlmostEqual(float(macro["macro_mae"]), .5)
            self.assertEqual((float(macro["ci_low"]), float(macro["ci_high"])), (.25, .75))
            delta = next(r for r in read("paired_deltas.csv") if r["model"] == "zero_full" and r["workload"] == "normal")
            self.assertEqual({float(delta[k]) for k in ("mean_delta", "ci_low", "ci_high")}, {-.125})
            shift = read("workload_shift.csv")
            self.assertEqual({r["branch_id"] for r in shift}, {"1", "2", "3"})
            self.assertTrue(all(float(r["equal_weight_mae_floor"]) == .5 for r in shift))


if __name__ == "__main__":
    unittest.main()
