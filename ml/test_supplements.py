"""Checks on the exploratory supplement scripts and the paper consistency check, using invented inputs."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

from rmse import rmse
from scale import read_any_width
from study_data import ROOT, Site

sys.path.insert(0, str(ROOT / "scripts"))
import check_paper  # noqa: E402


def toy_site(project, key):
    return Site(project=project, key=key, selected=True, context={"method_hash": key}, window=frozenset(),
                static={"branch_opcode": "IFGE"}, labels={})


class PooledRmseTest(unittest.TestCase):
    def test_site_and_execution_share_weights(self):
        rows = [
            # Project aa: errors 0.5 over 1 execution and 0.0 over 3 executions.
            dict(setting="unseen", project="aa", workload="normal", branch_id="a1", opcode="IFGE", model="m", q=0.5, taken=1, fallthrough=0),
            dict(setting="unseen", project="aa", workload="normal", branch_id="a2", opcode="IFGE", model="m", q=0.0, taken=0, fallthrough=3),
            # Project bb: error 0.2 over 10 executions.
            dict(setting="unseen", project="bb", workload="normal", branch_id="b1", opcode="IFGE", model="m", q=0.3, taken=5, fallthrough=5),
            # Never executed, and a seen-setting row: both excluded.
            dict(setting="unseen", project="bb", workload="normal", branch_id="b2", opcode="IFGE", model="m", q=0.9, taken=0, fallthrough=0),
            dict(setting="seen", project="bb", workload="shift", branch_id="b1", opcode="IFGE", model="m", q=0.9, taken=5, fallthrough=5),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.csv"
            with path.open("w", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            (result,) = rmse(path)
        self.assertEqual((result["workload"], result["model"], result["sites"]), ("normal", "m", 3))
        self.assertAlmostEqual(result["rmse"], np.sqrt((0.25 + 0 + 0.04) / 3))
        # Shares within aa are 1/4 and 3/4; bb has one site. Projects then count equally.
        self.assertAlmostEqual(result["execution_share_rmse"], np.sqrt((0.25 / 4 + 0.04) / 2))


class AnyWidthLoaderTest(unittest.TestCase):
    def test_accepts_one_shared_width_and_rejects_mismatch(self):
        sites = [toy_site("aa", "site-a"), toy_site("bb", "site-b")]
        preds = [dict(branch_id=s.key, project_id=s.project, q_full=0.3, q_masked=0.4) for s in sites]
        wide = np.ones((2, 1536), dtype=np.float16)
        valid = dict(branch_id=["site-a", "site-b"], project_id=["aa", "bb"], full=wide, masked=wide)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
            np.savez(path / "embeddings.npz", **valid)
            _, vectors = read_any_width(path, sites)
            self.assertEqual(vectors["masked"]["site-b"].shape, (1536,))
            for change in [dict(masked=np.ones((2, 896))), dict(full=np.ones((3, 1536))),
                           dict(project_id=["bb", "aa"])]:
                np.savez(path / "embeddings.npz", **(valid | change))
                with self.subTest(keys=list(change)), self.assertRaises(ValueError):
                    read_any_width(path, sites)


class PaperCheckTest(unittest.TestCase):
    def test_numbers_match_across_markup_and_differ_on_edit(self):
        markdown = "## Abstract\n\nMAE was 0.424 (−0.022 to 0.024) over 9 × 10⁻⁶ runs. **Table 2.** See [x](../a/b.csv) and `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`."
        latex = (r"\begin{abstract}MAE was 0.424 ($-$0.022 to 0.024) over $9 \times 10^{-6}$ runs~\citep[Table 6.2]{k}."
                 r" See \repo{a/b.csv}{x} at \texttt{2e1fd397}.\label{tab:2}")
        self.assertEqual(check_paper.markdown_numbers(markdown), check_paper.latex_numbers(latex))
        self.assertNotEqual(check_paper.markdown_numbers(markdown),
                            check_paper.latex_numbers(latex.replace("0.424", "0.442")))


if __name__ == "__main__":
    unittest.main()
