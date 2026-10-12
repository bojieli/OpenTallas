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


def spec(_ex, **kw):
    s = json.loads((EX / f"{_ex}.json").read_text())
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
        self.assertIn("PLACE_DENSITY_LB_ADDON=", env)      # PD means the spec PD (addon cleared)
        place = RT.gen_place(s, blocks)
        self.assertNotIn("dbBlockage_create", place)       # no blockage over row-end endcaps (DPL-0033)
        self.assertIn("ot_ref_strip", place)

    # 2026-10-12 layer contract (results/arch/hier_contract_1011/layer_usage_1012.md)
    def test_new_tile_caps_at_m5(self):
        s = RT.load_spec(spec("nhb_pbst_ref", name="m5cap_new_t"))
        lc = RT.layer_contract(s, None)
        self.assertEqual((lc["pg_layer"], lc["rlayers"], lc["strap_layer"], lc["layer_cap"]), ("M5", ("M2", "M5"), "M6", "M5"))
        r = RT.gen(spec("nhb_pbst_ref", name="m5cap_new_t"), write=False)
        self.assertEqual([f for f in r["findings"] if f[0] == "FAIL"], [])
        blocks = RT.place_blocks(s, *r["outline"], RT.blocks_of(s))
        env = RT.gen_env(s, "k", *r["outline"], lc, blocks)
        self.assertIn("RLAYERS='M2 M5'", env)
        self.assertIn("PIN_H='M4'", env)
        self.assertIn("PIN_V='M5'", env)
        pdn = RT.gen_pdn(s, lc)
        self.assertIn("-pins {M5}", pdn)
        self.assertNotIn("-layer {M6}", pdn)
        self.assertNotIn("-layers {M5 M6}", pdn)

    def test_m6_needs_a_grant(self):
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x", pg_layer="M6")), None)
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x", layer_cap="M6")), None)
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x", layer_cap="M7", layer_cap_grant="x")), None)
        lc = RT.layer_contract(RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x", layer_cap="M6",
                                                 layer_cap_grant="hgi lead: 512-pin edge relay")), None)
        self.assertEqual((lc["pg_layer"], lc["rlayers"], lc["strap_layer"], lc["cap_basis"]), ("M6", ("M2", "M6"), "M7", "granted"))

    def test_legacy_kit_keeps_its_contract(self):
        lc = RT.layer_contract(RT.load_spec(spec("nhb_pbst_ref")), None)
        self.assertEqual((lc["pg_layer"], lc["rlayers"], lc["strap_layer"]), ("M6", ("M2", "M6"), "M7"))
        self.assertTrue(lc["cap_basis"].startswith("legacy"))

    def test_pins_above_cap_refused(self):
        s = RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x", route={"pin_h": "M4 M6"}))
        with self.assertRaises(RT.SpecError):
            RT.pin_layers(s, RT.layer_contract(s, None))

    def test_slot_layer_cap(self):
        s = RT.load_spec(spec("nhb_pbst_ref", name="m5cap_x"))
        self.assertEqual(RT.layer_contract(s, {"pg_layer": "M5", "layer_cap": "M5"})["pg_layer"], "M5")
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(s, {"pg_layer": "M7"})                       # a slot not bumped to the M5 contract
        lc = RT.layer_contract(s, {"pg_layer": "M6", "layer_cap": "M6", "layer_cap_grant": "lead: dense relay"})
        self.assertEqual(lc["pg_layer"], "M6")

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
