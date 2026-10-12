"""tools/ref_tile (ref-flow-1011): kit generation invariants and gate checks that need no fleet host."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import ref_tile as RT  # noqa: E402
import pre_route_gate as G  # noqa: E402
import textbook_lint as TL  # noqa: E402

EX = HERE / "examples"


def spec(name, **kw):
    s = json.loads((EX / f"{name}.json").read_text())
    s.update(kw)
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(s, f)
    f.close()
    return f.name


class Gen(unittest.TestCase):
    def test_pbst_kit(self):
        r = RT.gen(spec("nhb_pbst_ref"), write=False)
        self.assertEqual([f for f in r["findings"] if f[0] == "FAIL"], [])
        s = RT.load_spec(spec("nhb_pbst_ref"))
        blocks = RT.place_blocks(s, *r["outline"], RT.blocks_of(s))
        self.assertTrue(all(b["offtrack"] == 0 for b in blocks))
        env = RT.gen_env(s, "k", *r["outline"], RT.layer_contract(s, None), blocks)
        self.assertIn("RLAYERS='M2 M6'", env)
        self.assertIn("OT_PK_ABOVE_ONLY=1", env)
        self.assertIn("PLACE_DENSITY_LB_ADDON=", env)      # macro-dominated tile: fixed density
        place = RT.gen_place(s, blocks)
        self.assertNotIn("dbBlockage_create", place)       # no blockage over row-end endcaps (DPL-0033)
        self.assertIn("ot_ref_strip", place)

    def test_pin_plan_rejects_bit_names(self):
        with self.assertRaises(RT.SpecError):
            RT.load_spec(spec("val_good_clt6", pins={"W": ["ck[0]"]}))

    def test_cluster_layer_contract_and_spine(self):
        s = RT.load_spec(spec("bad_qkv_hub_t_handviews"))
        lc = RT.layer_contract(s, None)
        self.assertEqual(lc["pg_layer"], "M7")
        self.assertEqual(set(lc["children"].values()), {"M6"})
        pdn = RT.gen_pdn(s, lc)
        self.assertIn("ot_ref_present", pdn)                # PDN-0217 guard
        self.assertIn("-layers {M6 M7}", pdn)
        hooks = RT.gen_hooks(s, "k")
        self.assertIn("clock_spine.tcl", hooks["pre_cts.tcl"])
        self.assertLess(hooks["pre_cts.tcl"].index("source /src/physical/common_flow/clock_spine"), hooks["pre_cts.tcl"].index("source /src/physical/qwen_die_masters/pre_cts_skew"))
        self.assertIn("ot_nhb_pbst", hooks["spine_ins.tcl"])

    def test_child_lattice(self):
        s = RT.load_spec(spec("bad_qkv_hub_t_handviews"))
        blocks = RT.place_blocks(s, 777.6, 604.8, RT.blocks_of(s))
        for b in blocks:
            for v in (b["x"], b["y"]):
                self.assertAlmostEqual(v / RT.CHILD_LATTICE_UM, round(v / RT.CHILD_LATTICE_UM), places=6)


class Rtl(unittest.TestCase):
    def test_runtime_partselect_loop_multiplicity(self):
        src = """module m(input clk, input [3:0] a, input [511:0] d, output reg [8191:0] bb);
          localparam integer N = 16; integer s; reg [3:0] r;
          always @(posedge clk) for (s = 0; s < N; s = s + 1) begin r = a + s; bb[512 * r +: 512] <= d; end
        endmodule"""
        with tempfile.NamedTemporaryFile("w", suffix=".sv", delete=False) as f:
            f.write(src)
        r = TL.rtl_lint([f.name], top="m")
        self.assertEqual(r["runtime_partselect_bits"], 16 * 512)
        self.assertIn("runtime_partselect", r["refuse"])

    def test_hard_child_params(self):
        src = """module top(input clk); child #(.W(4)) u (.clk(clk)); endmodule
                 module child #(parameter W = 4) (input clk); endmodule"""
        with tempfile.NamedTemporaryFile("w", suffix=".sv", delete=False) as f:
            f.write(src)
        r = TL.rtl_lint([f.name], hard_cells=["child"], top="top")
        self.assertIn("hard_child_params", r["refuse"])


class Sources(unittest.TestCase):
    def test_unsynced_hook_fails(self):
        g = G.Gate()
        job = {"source": {"commit": None, "paths": ["tools"]}, "stages": {"route": {"cmd": "true"}}}
        r = G.check_sources(g, job, ("physical/qwen_die_masters/pre_cts_skew.tcl",), None)
        self.assertIn("physical/qwen_die_masters/pre_cts_skew.tcl", r["outside"])
        self.assertEqual(g.verdict, "FAIL")


if __name__ == "__main__":
    unittest.main()
