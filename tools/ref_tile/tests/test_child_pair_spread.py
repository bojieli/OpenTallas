"""HANDOFF 0fz 2026-10-18 (owner 0dq "boundary matched to the neighbours"): a wires-only parent is judged per LINKED
child pair (a net from one child's output to another's input), not across all children.  The KP4 decoder gate6
figures: all-children FF spread 99.7 ps, but per pair syn-chn 67.3 / syn-dly 99.7 / chn-out 54.4 / dly-out 67.4."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as G  # noqa: E402

RTL = """module top (input wire clk, input wire rst_n, input wire [3:0] p, output wire [3:0] q, output wire s);
    wire [3:0] x, y, z;  // a comment naming u_out
`ifndef HARD
    ka #(.MUT(1)) u_a (.clk(clk), .p(p), .x(x), .s(s));
`else
    ka u_a (.clk(clk), .p(p), .x(x[3:0]), .s(s));
`endif
    kb u_b (.clk(clk), .rst_n(rst_n), .x(x), .y(y));
    kc u_c (.clk(clk), .p(p[1:0]), .z(z));
    kd u_d (.clk(clk), .y({y[1:0], 2'b00}), .z(z), .q(q));
endmodule
"""
# boundary insertion per child at TT / FF; pin arrival per child below
INS = dict(a=((250.0, 300.0), (200.0, 250.0)), b=((140.0, 190.0), (110.0, 160.0)),
           c=((240.0, 290.0), (190.0, 240.0)), d=((230.0, 270.0), (180.0, 220.0)))
ARR = dict(tt=dict(a=520.0, b=630.0, c=530.0, d=540.0), ff=dict(a=450.0, b=480.0, c=445.0, d=450.0))


class ChildPair(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "top.sv").write_text(RTL)
        for n, (tt, ff) in INS.items():
            v = self.root / "v" / n
            v.mkdir(parents=True)
            (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"min": tt[0], "max": tt[1]}},
                                                          "ff": {"boundary": {"min": ff[0], "max": ff[1]}}}))
        self.old, G.ROOT = G.ROOT, self.root
        self.spec = dict(kind="cluster", top="top", sources=["top.sv"], defines=["HARD"],
                         children=[dict(view=f"v/{n}", inst=f"*u_{n}") for n in INS])

    def tearDown(self):
        G.ROOT = self.old
        self.td.cleanup()

    def dom(self):
        out = {}
        for c in ("tt", "ff"):
            pins = [dict(pin=f"u_{n}/clk", arr=a) for n, a in ARR[c].items()]
            out[c] = {"boundary": {"n": 4, "min": min(ARR[c].values()), "max": max(ARR[c].values())},
                      "all": {"n": 4, "min": min(ARR[c].values()), "max": max(ARR[c].values())}, "macros": {"pins": pins}}
        return out

    def rec(self, spec=None):
        spec = spec or self.spec
        d = G.with_child_flops(self.dom(), spec)
        return G.child_pair_spreads(G.corner_spreads({}, d), d, spec)

    def test_linked_pairs_from_rtl(self):
        # x: a->b, y: b->d, z: c->d; p / q / s / clk / rst_n are parent ports, not links
        self.assertEqual(G.linked_child_pairs(self.spec), [("*u_a", "*u_b"), ("*u_b", "*u_d"), ("*u_c", "*u_d")])

    def test_worst_linked_pair_is_judged(self):
        r = self.rec()
        # FF child flops: a 650..700, b 590..640, c 635..685, d 630..670; all-children 590..700 = 110
        self.assertEqual(r["ff_child_flop_spread_ps"], 110.0)
        pairs = {(x["corner"], x["a"], x["b"]): x["ps"] for x in r["child_pairs"]}
        self.assertEqual(pairs[("ff", "u_a", "u_b")], 110.0)      # max(700-590, 640-650)
        self.assertEqual(pairs[("ff", "u_b", "u_d")], 80.0)       # max(640-630, 670-590)
        self.assertEqual(pairs[("ff", "u_c", "u_d")], 55.0)
        self.assertNotIn(("ff", "u_a", "u_c"), pairs)              # a and c do not communicate
        self.assertEqual(r["ff_pin_spread_ps"], 110.0)
        self.assertEqual(r["ff_pin_spread_basis"], "child_pair")

    def test_unlinked_outlier_passes(self):
        # move b off the path a->b: only b-d and c-d remain linked; a (the earliest FF tap) no longer counts
        rtl = RTL.replace(".x(x), .y(y)", ".x(p), .y(y)")
        (self.root / "top.sv").write_text(rtl)
        r = self.rec()
        self.assertEqual(r["ff_pin_spread_ps"], 80.0)
        self.assertEqual(r["tt_pin_spread_ps"], max(x["ps"] for x in r["child_pairs"] if x["corner"] == "tt"))

    def test_unreadable_rtl_keeps_all_children(self):
        r = self.rec(dict(self.spec, sources=["missing.sv"]))
        self.assertEqual(r["ff_pin_spread_basis"], "child_flop")
        self.assertNotIn("child_pairs", r)

    def test_tile_unchanged(self):
        r = G.child_pair_spreads({"tt_pin_spread_ps": 50.0}, self.dom(), dict(kind="tile"))
        self.assertEqual(r, {"tt_pin_spread_ps": 50.0})


if __name__ == "__main__":
    unittest.main()
