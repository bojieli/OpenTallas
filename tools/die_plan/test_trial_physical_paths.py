import json
import tempfile
import unittest
from pathlib import Path
import trial_tap_arrivals as T


class PhysicalPaths(unittest.TestCase):
    def test_raw_repeater_is_visible_only_with_opt_in(self):
        tree = dict(meta={"clock_cell": "inv2"},
                    nodes={"0": dict(parent=None, kids=[1], x=0, y=0, region_root="A"),
                           "1": dict(parent=0, kids=[], x=300, y=0)},
                    taps=[dict(port="t_P__clk", part="P", node=1, xy=[301, 0])],
                    node_buf={"0": "b0", "1": "b1"},
                    parent_of={"r1_0": "b0", "b1": "r1_0"},
                    sites={"b0": [0, 0], "r1_0": [150, 0], "b1": [300, 0]})
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / "tree.json").write_text(json.dumps(tree))
            (p / "arr.txt").write_text("T t_P__clk 95 85 10\nN b0 10 8\nN r1_0 45 40\nN b1 90 80\n")
            old, miss = T.export(p / "tree.json", p / "arr.txt", "TT", node_cells=True)
            full, missing = T.export(p / "tree.json", p / "arr.txt", "TT", node_cells=True, physical_paths=True)
            self.assertEqual((miss, missing), (0, 0))
            self.assertNotIn("r1_0", old["node_cell"].values())
            self.assertIn("r1_0", full["node_cell"].values())
            self.assertEqual(full["taps"][0]["tree_path"], "h00")
            self.assertEqual(old["taps"][0]["tree_path"], "h0")
            self.assertEqual(full["taps"][0]["late_ps"], old["taps"][0]["late_ps"])
            self.assertEqual(full["node_late_ps"]["h0"], 45)


if __name__ == "__main__":
    unittest.main()
