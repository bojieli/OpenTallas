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
    def test_ordered_pin_group_limit_reaches_gate_and_route(self):
        s = RT.load_spec(spec("nhb_pbst_ref", route={"pin_group_max": 16}))
        r = RT.gen(spec("nhb_pbst_ref", route={"pin_group_max": 16}), write=False)
        blocks = RT.place_blocks(s, *r["outline"], RT.blocks_of(s))
        env = RT.gen_env(s, "k", *r["outline"], RT.layer_contract(s, None), blocks)
        self.assertIn("export OT_PIN_GROUP_MAX=16", env)
        self.assertIn("PIN_MIN_TRACKS=2", env)
        self.assertIn("OT_PIN_GROUP_MAX=16", RT.gen_job(s, "k", "deadbeef", blocks)["stages"]["route"]["cmd"])
        s["route"].pop("pin_group_max")
        self.assertEqual(RT.pin_group_max(s), 32)

    def test_invalid_ordered_pin_group_limit_refused(self):
        for value in (0, -1, 33, True, 16.5, "16"):
            with self.assertRaises(RT.SpecError):
                RT.load_spec(spec("nhb_pbst_ref", route={"pin_group_max": value}))
    def test_secondary_clock_is_declared_before_data_slew(self):
        s = {"name": "two_root", "clock_port": "ck",
             "sdc_extra": ["physical/qwen_romio_slots/qfd_coll_xfifo_native.sdc"]}
        text = RT.gen_sdc(s, 770)
        self.assertLess(text.index("create_clock -name ckd"),
                        text.index("set_input_transition 150 [all_inputs -no_clocks]"))
        # Source slew stays explicit, and data arrival tags are removed before
        # measuring the secondary boundary reference in the extra SDC.
        self.assertIn("set_input_transition 150 [get_ports ckd]", text)
        self.assertLess(text.index("unset_input_delay -clock $ot_xf_refclk"),
                        text.index("arrival_max_rise"))

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


class Abut(unittest.TestCase):
    """two R0 macros stacked N-S at gap <= 0.1 um with pins on W / E only are one abutted stack (no channel FAIL);
    side by side, or a real gap under 20 um, keeps the channel rule"""
    V = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"

    def blk(self, i, x, y):
        m = RT.read_view_lef(self.V)
        return {"kind": "macro", "view": self.V, "master": m["name"], "inst": None, "w": m["W"], "h": m["H"], "at": [x, y],
                "orient": "R0", "count": 1, "idx": i, "x": x, "y": y, "offtrack": 0}

    def chan(self, blocks):
        s = {"pins": {"S": ["ck"]}}
        return [m for sev, chk, m, _ in RT.floorplan_checks(s, 400.0, 400.0, blocks, None) if chk == "channel"]

    def test_abut_plan_is_probe_only(self):
        """abut_plan admits a planned narrow channel as WARN only on a probe cluster (job.hold_merge); without the
        probe marker it FAILs itself and the 20-um channel rule still fires"""
        w = RT.read_view_lef(self.V)["W"]
        bl = [self.blk(0, 100.0, 100.0), self.blk(1, 100.0 + w + 4.32, 100.0)]
        ab = {"channel_um": 4.32, "edge_um": 20.0, "why": "lane bay probe"}
        probe = {"kind": "cluster", "pins": {"S": ["ck"]}, "abut_plan": ab, "job": {"hold_merge": "probe"}}
        r = RT.floorplan_checks(probe, 400.0, 400.0, bl, None)
        self.assertEqual([c for sev, c, _, _ in r if sev == "FAIL" and c == "channel"], [])
        self.assertEqual([sev for sev, c, _, _ in r if c == "abut_plan"], ["WARN"])
        merge = {"kind": "cluster", "pins": {"S": ["ck"]}, "abut_plan": ab, "job": {}}
        r = RT.floorplan_checks(merge, 400.0, 400.0, bl, None)
        self.assertEqual([sev for sev, c, _, _ in r if c == "abut_plan"], ["FAIL"])
        self.assertEqual(len([c for sev, c, _, _ in r if sev == "FAIL" and c == "channel"]), 1)
        tight = [self.blk(0, 100.0, 100.0), self.blk(1, 100.0 + w + 2.16, 100.0)]        # under the declared channel
        r = RT.floorplan_checks(probe, 400.0, 400.0, tight, None)
        self.assertEqual(len([c for sev, c, _, _ in r if sev == "FAIL" and c == "channel"]), 1)

    def test_stack_abutted(self):
        h = RT.read_view_lef(self.V)["H"]
        self.assertEqual(self.chan([self.blk(0, 100.0, 100.0), self.blk(1, 100.0, 100.0 + h + 0.024)]), [])

    def test_stack_abutted_mirrored(self):
        """MY / MX / R180 banks abut like R0 (touching faces carry no signal pin); a rotated macro keeps the rule"""
        h = RT.read_view_lef(self.V)["H"]
        for o in ("MY", "MX", "R180"):
            a, b = self.blk(0, 100.0, 100.0), self.blk(1, 100.0, 100.0 + h + 0.024)
            a["orient"] = b["orient"] = o
            self.assertEqual(self.chan([a, b]), [], o)
        a, b = self.blk(0, 100.0, 100.0), self.blk(1, 100.0, 100.0 + h + 0.024)
        a["orient"] = b["orient"] = "R90"
        self.assertEqual(len(self.chan([a, b])), 1)

    def test_at_exact_is_not_snapped(self):
        h = RT.read_view_lef(self.V)["H"]
        s = {"kind": "tile", "pins": {"S": ["ck"]}, "children": [],
             "macros": [{"view": self.V, "count": 1, "at": [99.792, 99.36], "at_exact": True},
                        {"view": self.V, "count": 1, "at": [99.792, round(99.36 + h + 0.024, 3)], "at_exact": True}]}
        bl = RT.place_blocks(s, 400.0, 400.0, RT.blocks_of(s))
        self.assertEqual([b["y"] for b in bl], [99.36, round(99.36 + h + 0.024, 3)])
        self.assertEqual([b["offtrack"] for b in bl], [bl[0]["offtrack"]] * 2)      # same residue on every track grid
        self.assertEqual([m for sev, chk, m, _ in RT.floorplan_checks(s, 400.0, 400.0, bl, None) if chk == "channel"], [])

    def test_gap_and_side_by_side_still_fail(self):
        m = RT.read_view_lef(self.V)
        self.assertEqual(len(self.chan([self.blk(0, 100.0, 100.0), self.blk(1, 100.0, 100.0 + m["H"] + 5.0)])), 1)
        self.assertEqual(len(self.chan([self.blk(0, 100.0, 100.0), self.blk(1, 100.0 + m["W"] + 0.024, 100.0)])), 1)


class Job(unittest.TestCase):
    def test_structural_change_reaches_job(self):
        s = json.loads((EX / "nhb_pbst_ref.json").read_text())
        self.assertNotIn("structural_change", RT.gen_job(s, RT.kit_dir(s), "0123456789ab", []))
        s["structural_change"] = "  macro pin-edge M5 guard band  "
        self.assertEqual(RT.gen_job(s, RT.kit_dir(s), "0123456789ab", [])["structural_change"],
                         "macro pin-edge M5 guard band")
        del s["structural_change"]
        s["job"] = dict(s["job"], structural_change="row split")
        self.assertEqual(RT.gen_job(s, RT.kit_dir(s), "0123456789ab", [])["structural_change"], "row split")


    def test_contract_slot_layer_cap_dict(self):
        # qwen_rom_tp8 v3 slots carry layer_cap as {"cap": "M5", "view_max_layer": ..., "conforms": ...}
        s = {"name": "x", "top": "x", "contract": {"file": "results/arch/hier_contract_1012/qwen_rom_tp8.json",
                                                   "slot": "s_0_0"}}
        slot = RT.contract_slot(s)
        self.assertEqual(slot["layer_cap"], "M5")
        self.assertEqual(RT.tile_cap(s, slot), ("M5", "contract"))


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


class Recipe(unittest.TestCase):
    """kit recipe (el1013-finishing-recipe part B): an existing kit keeps recipe 1 byte for byte, a new kit takes recipe 2"""
    EXN = "nhb_pbst_ref"

    def kit(self, root, **kw):
        kw.setdefault("route", {"pd": 0.5})       # the example pins hold_margin_ns; the recipe default is under test
        r = RT.gen(spec(self.EXN, **kw), commit="c" * 40, out_root=Path(root))
        d = Path(root) / r["kit"]
        return {f.name: f.read_text() for f in d.iterdir()}

    def old_kit(self, root, **kw):
        d = Path(root) / RT.KIT_ROOT / kw.get("name", json.loads((EX / f"{self.EXN}.json").read_text())["name"])
        d.mkdir(parents=True)
        (d / "kit.env").write_text("# a kit generated before recipes\nTOP=x\n")
        return self.kit(root, **kw)

    def test_existing_kit_stays_recipe_1(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            old, pinned = self.old_kit(a), self.kit(b, recipe=1)
        self.assertNotIn("RECIPE=", old["kit.env"])
        self.assertNotIn("recipe", json.loads(old["spec.json"]))
        self.assertNotIn("pre_gpl.tcl", old)
        self.assertNotIn("OT_OFLOP", old["kit.env"])
        self.assertNotIn("leaf_iohold", old["kit.env"])
        self.assertIn("--macro-place-halo 2.16 2.16", old["kit.env"])
        job = json.loads(old["job.json"])
        self.assertEqual(job["route_hold_margin_ns"], 0.010)
        self.assertIn("HM=0.01 ", job["stages"]["route"]["cmd"])
        # an explicit "recipe": 1 on a NEW kit is the same kit (only spec.json records the key)
        self.assertEqual({k: v for k, v in old.items() if k != "spec.json"},
                         {k: v for k, v in pinned.items() if k != "spec.json"})
        # a second regeneration of the old kit does not drift into the new recipe
        with tempfile.TemporaryDirectory() as a:
            first = self.old_kit(a)
            self.assertEqual(first, self.kit(a))

    def test_kit_spec_json_reads_the_kit_env_beside_it(self):
        # the submit gate regenerates <tmp>/<kit>/spec.json with ROOT = a tree that has no kits: the recipe comes from
        # the kit.env beside the spec, so an old kit is not re-judged with the new-kit defaults
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            old = self.old_kit(a, name="rcp_old_x")
            kd = Path(a) / RT.KIT_ROOT / "rcp_old_x"
            again = RT.gen(str(kd / "spec.json"), commit="c" * 40, out_root=Path(b))
            self.assertEqual({f.name: f.read_text() for f in (Path(b) / again["kit"]).iterdir()}, old)
            s = RT.load_spec(str(kd / "spec.json"))
            self.assertEqual(RT.kit_recipe(s, Path(b), str(kd / "spec.json")), 1)
        with tempfile.TemporaryDirectory() as c:      # no kit.env anywhere in sight: a new kit
            self.assertEqual(RT.kit_recipe(s, Path(c)), RT.RECIPE_LATEST)

    def test_recipe_1_still_refuses_the_combination(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(RT.SpecError):
                self.old_kit(a, io_flop_at_pins={"cols": 4}, outhold=True)

    def test_new_kit_takes_recipe_2(self):
        with tempfile.TemporaryDirectory() as a:
            new = self.kit(a)
            again = self.kit(a)                    # regeneration reads RECIPE=2 back from kit.env
        self.assertEqual(new, again)
        env = new["kit.env"]
        self.assertIn(f"\nRECIPE={RT.RECIPE_LATEST}\n", env)
        kd = f"{RT.KIT_ROOT}/{json.loads(new['spec.json'])['name']}"
        self.assertIn(f"--step-tcl PRE_GLOBAL_PLACE={kd}/pre_gpl.tcl", env)
        self.assertIn(f"--step-tcl PRE_DETAIL_PLACE={kd}/pre_dpl.tcl", env)
        self.assertEqual(env.count("PRE_GLOBAL_PLACE="), 1)      # ORFS takes ONE hook per step
        self.assertEqual(env.count("PRE_DETAIL_PLACE="), 1)
        for k in ("OT_OFLOP_HOPS=8", "OT_OFLOP_ALLOW_NONE=1", "OT_OFLOP_COLS=4", "OT_IOHOLD_IN=1",
                  "OT_INHOLD_DRV=BUFx4f_ASAP7_75t_R", "--macro-place-halo 5.4 5.4"):
            self.assertIn(k, env)
        gpl = [x for x in new["pre_gpl.tcl"].splitlines() if x.startswith("source ")]
        self.assertEqual(gpl, ["source /src/physical/common_flow/pin_reg_split.tcl",          # one flop per pin FIRST
                               "source /src/physical/dsrom_window_source/leaf_iohold.tcl",      # then the hold stages
                               "source /src/physical/qwen_die_masters/io_flop_at_pins.tcl"])
        # recipe-2 pin defaults (el1014-root-recipe2): HB2 pad, synthesis keep of top-level pin registers
        self.assertIn("OT_INHOLD_MASTER=HB2xp67_ASAP7_75t_R", env)
        self.assertIn("OT_KEEP_PIN_REGS=1", env)
        self.assertNotIn("HB4xp67", env)
        self.assertNotIn("OT_HOLD_PAD_STRONG", env)
        dpl = new["pre_dpl.tcl"]
        self.assertIn("leaf_inhold_release.tcl", dpl)
        self.assertIn("out_flop_release.tcl", dpl)
        job = json.loads(new["job.json"])
        self.assertEqual(job["route_hold_margin_ns"], 0.030)
        self.assertIn("HM=0.03 ", job["stages"]["route"]["cmd"])
        sp = json.loads(new["spec.json"])
        self.assertEqual((sp["recipe"], sp["inhold"], sp["outhold"], sp["io_flop_at_pins"]["cols"]), (RT.RECIPE_LATEST, True, True, 4))
        ref = json.loads(new["floorplan.json"])["referenced"]
        for f in (f"{kd}/pre_gpl.tcl", f"{kd}/pre_dpl.tcl", "physical/dsrom_window_source/leaf_iohold.tcl",
                  "physical/common_flow/pin_reg_split.tcl",
                  "physical/dsrom_window_source/leaf_inhold.tcl", "physical/dsrom_window_source/leaf_inhold_release.tcl",
                  "physical/qwen_die_masters/io_flop_at_pins.tcl", "physical/qwen_die_masters/out_flop_release.tcl"):
            self.assertIn(f, ref)
            if not f.startswith(kd):
                self.assertTrue((RT.ROOT / f).is_file(), f)

    def test_recipe_2_macro_edge_guard_default(self):
        # el1014-root-macro-edge: a recipe-2 tile with hard macros routes with the macro-edge via guard (pre-GRT add,
        # post-DRT remove); recipe 1, a spec with its own edge guard, and "macro_edge_guard": false do not get it
        g = "source /src/physical/qwen_die_masters/sram_edge_guard.tcl"
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, \
                tempfile.TemporaryDirectory() as c, tempfile.TemporaryDirectory() as d:
            new, old = self.kit(a), self.kit(b, recipe=1)
            own = self.kit(c, boundary_tcl=["physical/qwen_die_masters/sram_edge_guard.tcl"])
            off = self.kit(d, macro_edge_guard=False)
        self.assertEqual(new["pre_grt.tcl"].count(g), 1)
        self.assertEqual(new["post_drt.tcl"].count(g), 1)
        self.assertLess(new["pre_grt.tcl"].index("grt_macro_top_layer.tcl"), new["pre_grt.tcl"].index(g))
        self.assertNotIn(g, old["pre_grt.tcl"] + old["post_drt.tcl"])
        self.assertEqual(own["pre_grt.tcl"].count(g), 1)                    # the spec's own entry, not a second one
        self.assertNotIn(g, off["pre_grt.tcl"] + off["post_drt.tcl"])
        s = RT.load_spec(spec(self.EXN))
        RT.apply_recipe(s, 2)
        kd = RT.kit_dir(s)
        self.assertIn("physical/common_flow/macro_edge_via_guard.tcl", RT.referenced_paths(s, kd))
        self.assertFalse(RT.macro_edge_guard(dict(s, macros=[])))           # no hard macro: no guard

    def test_io_hold_margin_split(self):
        # q14 r8 2026-10-14: route.io_hold_margin_ns relieves ONLY the route-time FF repair SDC of the boundary; sign-off
        # (signoff.sdc, verdict post_sdc) is unchanged; no field -> one margin, no extra file (existing kits unchanged)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            k = self.kit(a, name="iohm_a", route={"hold_margin_ns": 0.06, "io_hold_margin_ns": 0.01})
            o = self.kit(b, name="iohm_b", route={"hold_margin_ns": 0.03})
        ffr, so = k["signoff_ffrepair.sdc"], k["signoff.sdc"]
        self.assertIn("set ::env(OT_IO_HOLD_SKEW) 0\nset ::env(OT_IO_IN_HOLD_SKEW) -50\n", ffr)
        self.assertTrue(ffr.rstrip().endswith("unset -nocomplain ::env(OT_IO_IN_HOLD_SKEW)"))
        self.assertNotIn("set ::env(OT_IO_IN_HOLD_SKEW)", so)
        self.assertIn("set ::env(OT_IO_HOLD_SKEW) 50\n", so)
        job = json.loads(k["job.json"])
        self.assertIn("signoff_ffrepair.sdc'", job["stages"]["route"]["cmd"])
        self.assertIn("HM=0.06 ", job["stages"]["route"]["cmd"])
        self.assertTrue(job["verdict"]["post_sdc"][0].endswith("/signoff.sdc"))
        self.assertTrue(any(f.endswith("/signoff_ffrepair.sdc") for f in json.loads(k["floorplan.json"])["referenced"]))
        self.assertNotIn("signoff_ffrepair.sdc", o)
        self.assertNotIn("signoff_ffrepair", json.loads(o["job.json"])["stages"]["route"]["cmd"])
        with self.assertRaises(RT.SpecError):
            RT.io_hold_relief_ps({"route": {"hold_margin_ns": 0.01, "io_hold_margin_ns": 0.02}})

    def test_recipe_2_spec_overrides(self):
        with tempfile.TemporaryDirectory() as a:
            k = self.kit(a, name="rcp_a", inhold=False, outhold=False, route={"hold_margin_ns": 0.02, "macro_halo_um": 3.24})
            env = k["kit.env"]
            self.assertIn(f"RECIPE={RT.RECIPE_LATEST}", env)
            self.assertNotIn("pre_gpl.tcl", k)                   # pin flops alone: the repo hooks directly, default hop limit
            self.assertIn("PRE_GLOBAL_PLACE=physical/qwen_die_masters/io_flop_at_pins.tcl", env)
            self.assertNotIn("OT_OFLOP_HOPS", env)
            self.assertNotIn("OT_IOHOLD_IN", env)
            self.assertIn("--macro-place-halo 3.24 3.24", env)
            self.assertEqual(json.loads(k["job.json"])["route_hold_margin_ns"], 0.02)
            k = self.kit(a, name="rcp_b", io_flop_at_pins=None)   # hold stages alone
            self.assertNotIn("pre_gpl.tcl", k)
            self.assertIn("PRE_GLOBAL_PLACE=physical/dsrom_window_source/leaf_iohold.tcl", k["kit.env"])
            self.assertNotIn("OT_OFLOP", k["kit.env"])
            k = self.kit(a, name="rcp_c", outhold=False)          # input hold + pin flops
            self.assertIn("source /src/physical/dsrom_window_source/leaf_inhold.tcl", k["pre_gpl.tcl"])
            self.assertNotIn("leaf_iohold", k["pre_gpl.tcl"])
            k = self.kit(a, name="rcp_d", io_flop_at_pins={"cols": 6})   # an explicit request keeps the no-flop error
            self.assertIn("OT_OFLOP_COLS=6", k["kit.env"])
            self.assertNotIn("OT_OFLOP_ALLOW_NONE", k["kit.env"])
            self.assertIn("pre_gpl.tcl", k)
            # a spec that owns its boundary hook, or carries RTL hold-delay cells, gets no default pin hooks on top
            s = RT.apply_recipe({"route": {}, "orfs_vars": {"POST_TAPCELL_TCL": "x.tcl"}}, 2)
            self.assertFalse(any(k in s for k in ("inhold", "outhold", "io_flop_at_pins")))
            s = RT.apply_recipe({"route": {"hold_delay": True}}, 2)
            self.assertIn("io_flop_at_pins", s)
            self.assertFalse("inhold" in s or "outhold" in s)
            with self.assertRaises(RT.SpecError):
                self.kit(a, name="rcp_e", recipe=RT.RECIPE_LATEST + 1)

    def test_hold_pad_strong_ports_need_a_measured_basis(self):
        with tempfile.TemporaryDirectory() as a:
            with self.assertRaises(RT.SpecError):        # HB4 on some pins only with the routed FF evidence
                self.kit(a, name="rcp_hp0", hold_pad={"strong_ports": "^n_y"})
            k = self.kit(a, name="rcp_hp1", hold_pad={"strong_ports": "^(n_y|rq_row)",
                                                      "basis": "job x-r1: FF -7.1 ps on n_y[*] with HB2"})
            env = k["kit.env"]
            self.assertIn("OT_INHOLD_MASTER=HB2xp67_ASAP7_75t_R", env)
            self.assertIn("OT_HOLD_PAD_STRONG_RE='^(n_y|rq_row)'", env)
            self.assertIn("OT_HOLD_PAD_STRONG_MASTER=HB4xp67_ASAP7_75t_R", env)
            k = self.kit(a, name="rcp_hp2", hold_pad={"cell": "HB4xp67_ASAP7_75t_R"})   # an explicit pad wins
            self.assertIn("OT_INHOLD_MASTER=HB4xp67_ASAP7_75t_R", k["kit.env"])
            with self.assertRaises(RT.SpecError):
                self.kit(a, name="rcp_hp3", hold_pad={"cell": "BUFx2_ASAP7_75t_R"})

    def test_spec_orfs_vars_pad_and_driver_win(self):
        # a spec that names its own pad / driver in orfs_vars keeps them (no recipe default appended after them)
        with tempfile.TemporaryDirectory() as a:
            k = self.kit(a, name="rcp_ov", orfs_vars={"OT_INHOLD_MASTER": "HB2xp67_ASAP7_75t_R",
                                                      "OT_INHOLD_DRV": "BUFx2_ASAP7_75t_R"})
            env = k["kit.env"]
            self.assertEqual(env.count("OT_INHOLD_MASTER="), 1)
            self.assertEqual(env.count("OT_INHOLD_DRV="), 1)
            self.assertIn("OT_INHOLD_DRV=BUFx2_ASAP7_75t_R", env)
            self.assertNotIn("hold_pad", json.loads(k["spec.json"]))

    def test_split_and_keep_switch_off(self):
        with tempfile.TemporaryDirectory() as a:
            k = self.kit(a, name="rcp_off", pin_reg_split=False, keep_pin_regs=False)
            self.assertNotIn("pin_reg_split", k["pre_gpl.tcl"])
            self.assertNotIn("OT_KEEP_PIN_REGS", k["kit.env"])
            k = self.kit(a, name="rcp_noflop", io_flop_at_pins=None)          # hold stages alone: no split, no keep
            self.assertNotIn("OT_KEEP_PIN_REGS", k["kit.env"])
            self.assertIn("OT_INHOLD_MASTER=HB2xp67_ASAP7_75t_R", k["kit.env"])

    def test_existing_kit_keeps_hb4_pad(self):
        with tempfile.TemporaryDirectory() as a:
            old = self.old_kit(a, name="rcp_old_pad", outhold=True)
            self.assertNotIn("OT_INHOLD_MASTER", old["kit.env"])          # recipe 1: leaf_iohold default (HB4), unchanged
            self.assertNotIn("OT_KEEP_PIN_REGS", old["kit.env"])

    def test_pin_flop_hook_knobs_are_opt_in(self):
        t = (RT.ROOT / "physical/qwen_die_masters/io_flop_at_pins.tcl").read_text()
        self.assertIn("$::env(OT_OFLOP_HOPS) : 4}]", t)          # unset = the old hop limit
        self.assertEqual(t.count("{$hop < $ot_hops}"), 2)
        self.assertIn("$ot_n + $ot_ni == 0 && !$ot_allow_none", t)


class Sources(unittest.TestCase):
    def test_unsynced_hook_fails(self):
        g = G.Gate()
        job = {"source": {"commit": None, "paths": ["tools"]}, "stages": {"route": {"cmd": "true"}}}
        r = G.check_sources(g, job, ("physical/qwen_die_masters/pre_cts_skew.tcl",), None)
        self.assertIn("physical/qwen_die_masters/pre_cts_skew.tcl", r["outside"])
        self.assertEqual(g.verdict, "FAIL")


if __name__ == "__main__":
    unittest.main()


class PgSpread(unittest.TestCase):
    """ROOT 2026-10-15 (hbm_ckgen_rel-r1, 15.12 um): the export's child_lint (b) PG spread is predicted at gen time"""
    def test_model_matches_measured_failures(self):
        t = {"kind": "tile", "route": {}}
        r = RT.pg_stripe_spread(t, {"pg_layer": "M5"}, 15.12, 30)
        self.assertEqual(r[1], 2)
        self.assertAlmostEqual(r[2], 5.4 / 15.12)                                                    # measured 36 %
        self.assertFalse(RT.pg_spread_ok(RT.pg_stripe_spread(t, {"pg_layer": "M5"}, 15.12, 30)))
        self.assertTrue(RT.pg_spread_ok(RT.pg_stripe_spread(t, {"pg_layer": "M5"}, 17.28, 30)))
        m6 = {"kind": "tile", "route": {"pg_pitch": 10.8}}
        self.assertAlmostEqual(RT.pg_stripe_spread(m6, {"pg_layer": "M6"}, 30, 25.92)[2], 10.8 / 25.92)  # measured 42 %
        self.assertTrue(RT.pg_spread_ok(RT.pg_stripe_spread({"kind": "tile", "route": {"m5_pg_pitch": 2.7}},
                                                            {"pg_layer": "M5"}, 15.12, 30)))
        self.assertIsNone(RT.pg_stripe_spread({"kind": "cluster", "route": {}}, {"pg_layer": "M7"}, 15, 15))


class PinRegs(unittest.TestCase):
    """OWNER RULE 19:50 PT 2026-10-15: recipe 3 = pin registers on every data port of a new leaf tile"""
    def test_plan_and_env(self):
        s = {"kind": "tile", "clock_port": "clk", "pin_regs": {"enable": True}}
        p = RT.pin_regs_plan(s)
        self.assertEqual((p["clock"], p["latency_cycles"]), ("clk", {"input": 1, "output": 1}))
        self.assertEqual(RT.pin_regs_vars(s), ["--orfs-var OT_PIN_REGS=1", "--orfs-var OT_PIN_REGS_CLOCK=clk"])
        self.assertIsNone(RT.pin_regs_plan({"kind": "tile", "clock_port": "clk"}))
        with self.assertRaises(RT.SpecError):
            RT.pin_regs_plan({"kind": "tile", "clock_port": "clk", "pin_regs": {"enable": False}})       # no reason
        self.assertEqual(RT.pin_regs_vars({"kind": "tile", "clock_port": "clk",
                                           "pin_regs": {"enable": False, "reason": "PHY timing owned by the parent"}}), [])
        with self.assertRaises(RT.SpecError):
            RT.pin_regs_plan({"kind": "tile", "clock_port": "a", "clock": "entries", "clock_ports": ["a", "b"],
                              "pin_regs": {"enable": True}})
        with self.assertRaises(RT.SpecError):
            RT.pin_regs_plan({"kind": "tile", "clock_port": "clk", "pin_regs": {"enable": True, "exclude": "^cfg"}})
        v = RT.pin_regs_vars({"kind": "tile", "clock_port": "clk",
                              "pin_regs": {"enable": True, "exclude": "^cfg_", "reason": "static config"}})
        self.assertIn("--orfs-var OT_PIN_REGS_EXCLUDE='^cfg_'", v)

    def test_recipe_3_defaults(self):
        s = {"kind": "tile", "route": {}, "orfs_vars": {}}
        RT.apply_recipe(s, 3)
        self.assertEqual(s["pin_regs"], {"enable": True})
        c = {"kind": "cluster", "route": {}, "orfs_vars": {}}
        RT.apply_recipe(c, 3)
        self.assertNotIn("pin_regs", c)
        o = {"kind": "tile", "route": {}, "orfs_vars": {}}
        RT.apply_recipe(o, 2)
        self.assertNotIn("pin_regs", o)


class PinRegsGate(unittest.TestCase):
    def test_warn_then_fail(self):
        import datetime as dt
        sys.path.insert(0, str(Path(RT.__file__).parent))
        import pre_route_gate as PG
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td)
            (kd / "kit.env").write_text("EXTRA=(--orfs-var OT_KEEP_PIN_REGS=1)\n")
            early = dt.datetime.fromisoformat("2026-10-16T10:00:00-07:00")
            late = dt.datetime.fromisoformat("2026-10-17T10:00:00-07:00")
            for now, spec, want in ((early, {}, "WARN"), (late, {}, "FAIL"), (late, {"auto_react_parent": "p"}, "WARN"),
                                    (late, {"pin_regs": {"enable": False, "reason": "parent owns the boundary"}}, "INFO"),
                                    (late, {"kind": "cluster"}, None)):
                g = PG.Gate()
                PG.check_pin_regs(g, kd, spec, now=now)
                got = [i["severity"] for i in g.items if i["check"] == "pin_regs"]
                self.assertEqual(got, [want] if want else [], (now, spec))
            (kd / "kit.env").write_text("EXTRA=(--orfs-var OT_PIN_REGS=1 --orfs-var OT_PIN_REGS_CLOCK=clk)\n")
            g = PG.Gate()
            PG.check_pin_regs(g, kd, {}, now=late)
            self.assertEqual([i["severity"] for i in g.items], ["INFO"])
