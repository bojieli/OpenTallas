import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_qc_rows as Q
import test_clksite_stamp_native as TN


class T(unittest.TestCase):
    def test_conflict_is_counted_and_slid_clear(self):
        P = TN.FakeP()
        t = TN.tree()
        t["nodes"]["2"]["x"] = 4.0           # box x 3.46..6.16 overlaps the M7 pair [3.984, 4.656]
        t["nodes"]["2"]["y"] = 20.0
        self.assertIn((2, "A"), Q.pg_conflicts(P, t))
        moved, stuck = Q.slide_rest(P, t, None, 1.7)
        self.assertGreaterEqual(moved, 1); self.assertEqual(stuck, [])
        self.assertEqual(Q.pg_conflicts(P, t), [])
        self.assertLessEqual(abs(t["nodes"]["2"]["x"] - 4.0), 1.7 + 1e-9)

    def test_run_has_no_conflicts_after_and_snaps_taps(self):
        P = TN.FakeP()
        out, rep = Q.run(P, TN.tree(), None, max_slide=1.7)
        self.assertEqual(rep["pg_conflicts_after"], 0)
        self.assertEqual(rep["stamped_types"], 1)
        for t in out["taps"]:
            self.assertAlmostEqual((t["xy"][0] - 0.04) / 0.08, round((t["xy"][0] - 0.04) / 0.08), places=3)


if __name__ == "__main__":
    unittest.main()
