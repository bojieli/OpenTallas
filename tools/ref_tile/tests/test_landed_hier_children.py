"""QO-RP4LP 10-18: landed clusters whose hard children sit below a top-level soft instance (smh_tile_rp4lp: u_lf0.u_lh.u_xs),
and the pre-CTS ::ot_ce_counts that clock_entries.tcl needs to admit child clock pins as region-root sinks."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import clock_entry_constraints as CE  # noqa: E402
import pre_route_gate as P  # noqa: E402

RTL = """
module top (input ck_a, input ck_b, input [3:0] i, output [3:0] o);
  wire [3:0] x, y, y__l_b;
  leaf u_lf0 (.clk(ck_a), .d(i), .q(x));
  hard u_h (.clk(ck_a), .d(x), .q(y));
  ot_pl_land_w u_lpl_0_w (.ck(ck_a), .i(y), .bank(bk), .vld(v));
  ot_pl_land_r u_lpl_0_r (.ck(ck_b), .bank(bk), .vld(v), .o(y__l_b));
  leaf u_lf1 (.clk(ck_b), .d(%s), .q(o));
endmodule
"""


def spec(root, unlanded=False):
    src = Path(root) / "top.sv"
    src.write_text(RTL % ("y" if unlanded else "y__l_b"))
    return dict(kind="cluster", clock="multiple_cts_roots", top="top", sources=[str(src)], clock_ports=["ck_a", "ck_b"],
                children=[dict(inst="u_lf0.u_lh.u_xs", view="v/ot_xs"), dict(inst="u_h", view="v/ot_h"),
                          dict(inst="u_lf1.u_lh.u_xs", view="v/ot_xs")])


class T(unittest.TestCase):
    def test_hier_children_read_and_landed(self):
        with tempfile.TemporaryDirectory() as d:
            g = P.parent_link_graph(spec(d))
            self.assertIsNotNone(g)
            self.assertEqual(g["insts"]["u_lf0"]["kids"], ["u_lf0.u_lh.u_xs"])
            self.assertEqual(g["insts"]["u_lf1"]["root"], "ck_b")
            bad, landed = P.cross_region_links(g)
            self.assertEqual(bad, [])
            self.assertIn(("u_h", "u_lf1.u_lh.u_xs", "u_lpl_0"), landed)

    def test_unlanded_mutant_fails(self):
        with tempfile.TemporaryDirectory() as d:
            bad, _ = P.cross_region_links(P.parent_link_graph(spec(d, unlanded=True)))
            self.assertTrue(any("unlanded cross-region link" in b for b in bad))

    def test_missing_child_still_unreadable(self):
        with tempfile.TemporaryDirectory() as d:
            s = spec(d)
            s["children"].append(dict(inst="u_nope.u_x", view="v/ot_x"))
            self.assertIsNone(P.parent_link_graph(s))

    def test_pre_cts_counts(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(CE.landed_counts_tcl(spec(d)), "set ::ot_ce_counts [dict create {ot_xs} 2 {ot_h} 1]\n")
            self.assertEqual(CE.landed_counts_tcl(dict(spec(d), kind="tile")), "")


if __name__ == "__main__":
    unittest.main()
