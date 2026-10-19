"""S81-DEC2 10-18: a wires-only cluster's pin-flop spread is judged at the child boundary flops
(child clock-pin arrival + the child's own boundary insertion), not at the raw child clock pins."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as G  # noqa: E402


class ChildFlop(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        for n, (lo, hi) in dict(a=(250.0, 300.0), b=(140.0, 190.0)).items():
            v = self.root / "v" / n
            v.mkdir(parents=True)
            (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"min": lo, "max": hi}}}))
        self.old, G.ROOT = G.ROOT, self.root
        self.spec = dict(kind="cluster", children=[dict(view="v/a", inst="*u_a"), dict(view="v/b", inst="*u_b")])

    def tearDown(self):
        G.ROOT = self.old
        self.td.cleanup()

    def dom(self, n=2):
        pins = [dict(pin="u_a/clk", arr=580.0), dict(pin="u_b/clk", arr=690.0)]
        return {"tt": {"boundary": {"n": n, "min": 580.0, "max": 690.0}, "all": {"n": n, "min": 580.0, "max": 690.0},
                       "macros": {"pins": pins}}}

    def test_compensated_children_pass(self):
        rec = G.corner_spreads({}, G.with_child_flops(self.dom(), self.spec))
        self.assertEqual(rec["tt_pin_spread_ps"], 50.0)      # 830..880 at the child flops; raw pins 110 apart
        self.assertEqual(rec["tt_pin_spread_basis"], "child_flop")

    def test_glue_registers_keep_measured_boundary(self):
        rec = G.corner_spreads({}, G.with_child_flops(self.dom(n=5), self.spec))
        self.assertEqual(rec["tt_pin_spread_ps"], 110.0)

    def test_tile_unchanged(self):
        rec = G.corner_spreads({}, G.with_child_flops(self.dom(), dict(kind="tile", children=[])))
        self.assertEqual(rec["tt_pin_spread_ps"], 110.0)


if __name__ == "__main__":
    unittest.main()
