"""METHODOLOGY 12.7a: PG shields on both sides of every clock wire (die_infra freeze --clock-shield)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_infra as DI  # noqa: E402

P = SimpleNamespace(layers={"M8": {"dir": "H"}, "M9": {"dir": "V"}})


class Shield(unittest.TestCase):
    def test_free_sides_get_vss_wires(self):
        sh, r = DI.clock_shields(P, [], [("ck", "M8", 0.0, 9.92, 100.0, 10.08, 0.08)])
        self.assertEqual(r["shield_wires"], 2)
        self.assertTrue(r["complete"])
        ys = sorted((s_[3], s_[5]) for s_ in sh)
        self.assertAlmostEqual(ys[0][1], 9.84)      # below: 0.08 spacing from the wire edge
        self.assertAlmostEqual(ys[1][0], 10.16)

    def test_adjacent_pg_stripe_is_the_shield(self):
        pg = [("VDD", "M8", 0.0, 10.20, 200.0, 10.68)]      # 0.12 from the edge: no signal track fits
        sh, r = DI.clock_shields(P, pg, [("ck", "M8", 0.0, 9.92, 100.0, 10.08, 0.08)])
        self.assertEqual((r["shielded_by_pg_stripe"], r["shield_wires"], r["conflicts"]), (1, 1, 0))

    def test_pg_inside_spacing_is_a_conflict(self):
        pg = [("VSS", "M8", 0.0, 10.12, 200.0, 10.60)]      # 0.04 < NDR spacing
        _, r = DI.clock_shields(P, pg, [("ck", "M8", 0.0, 9.92, 100.0, 10.08, 0.08)])
        self.assertEqual(r["conflicts"], 1)
        self.assertFalse(r["complete"])


if __name__ == "__main__":
    unittest.main()
