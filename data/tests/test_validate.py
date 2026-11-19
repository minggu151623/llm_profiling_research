import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate import load_examples

SHA = "a" * 64
ID = SHA + ":1:3"
SITE = dict(schema_version="v0", artifact_sha256=SHA, branch_id=ID, class_name="C",
            method_index=1, method_name="check", method_descriptor="(I)I", original_bci=3,
            target_bci=12, fallthrough_bci=6, branch_opcode="IFNE")
LABEL = dict(schema_version="v0", branch_id=ID, workload_id="w",
             taken_count=1, fallthrough_count=3, p_taken=0.25)


class LoaderTest(unittest.TestCase):
    def load(self, sites, labels):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = (Path(tmp) / n for n in ("static", "w"))
            for path, records in [(a, sites), (b, labels)]:
                path.write_text("".join(json.dumps(r) + "\n" for r in records))
            return load_examples(a, {"w": b})

    def test_separate_features_and_unobserved(self):
        for label in [LABEL, dict(LABEL, taken_count=0, fallthrough_count=0, p_taken=None)]:
            [(key, features, workload, target)] = self.load([SITE], [label])
            self.assertEqual((key, workload, target), (ID, "w", label))
            self.assertTrue(features.keys().isdisjoint(LABEL.keys()))

    def test_reject_corrupt_joins_and_labels(self):
        for sites, labels in [
            ([dict(SITE, taken_count=1)], [LABEL]), ([SITE, SITE], [LABEL]),
            ([SITE], [LABEL, LABEL]), ([SITE], []), ([SITE], [dict(LABEL, branch_id=SHA + ":0:0")]),
            ([SITE], [dict(LABEL, taken_count=-3)]), ([SITE], [dict(LABEL, p_taken=1)]),
            ([SITE], [dict(LABEL, p_taken=None)]), ([SITE], [dict(LABEL, workload_id="other")]),
            ([SITE], [dict(LABEL, taken_count=0, fallthrough_count=0, p_taken=0)]),
        ]:
            with self.subTest(sites=sites, labels=labels), self.assertRaises(ValueError):
                self.load(sites, labels)
