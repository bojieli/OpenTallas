#!/usr/bin/env python3
"""gen_core_kit_qc.py on main's tools (FLOW-FIX 10-25, canary F4): structural anchors patch main's face_flops.tcl /
tap_balance.tcl (and fail hard when a construct vanished), the generated run_kit.sh carries the rtl_lint / SELRANGE /
LEC / FF-only GRT steps, config.mk the RC + per-corner vclk keys, and the SDC vclk latency equals the bound TT value.
    python3 -m unittest physical/die_plan/qwen_compute/cores/legacy/test_gen_core_kit_qc.py"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_qc as G  # noqa: E402

MODULE = "qfd_dv_s5_su8_rst3"   # smallest QC core recipe (macro-free, SIGNED 10-25)


class Anchors(unittest.TestCase):
    def test_sub1_fails_hard_when_construct_vanished(self):
        with self.assertRaises(SystemExit):
            G._sub1("set other 1\n", r"^set ff_skip_re \{[^\n]*?\}", "x", "face_flops.tcl skip regex")
        with self.assertRaises(SystemExit):   # twice = ambiguous, also a hard failure
            G._sub1("set a {1}\nset a {2}\n", r"^set a \{[^\n]*\}", "x", "dup")


class SliceClockPinsOut(unittest.TestCase):
    """QC-A0-KITS-4 10-28: a master-slice clock entry (interior M5) leaves the face-pin audit table pins.json, so
    pin_audit does not compare the routed entry against the stale face pin; other pins and slice-less kits unchanged."""
    def test_moved_clock_dropped_others_kept(self):
        sys.path.insert(0, str(HERE.parents[4] / "tools/die_plan"))
        import master_slice as MS
        with tempfile.TemporaryDirectory() as t:
            kd = Path(t)
            rows = [dict(bus="clk", bit=None, layer="M4", x=0.042, y=21.756, face="W"),
                    dict(bus="a", bit=0, layer="M4", x=0.042, y=10.0, face="W")]
            (kd / "pins.json").write_text(json.dumps(rows) + "\n")
            self.assertEqual(G.slice_clock_pins_out(kd, MS, ["clk"]), [])          # no slice: unchanged
            self.assertEqual(len(json.loads((kd / "pins.json").read_text())), 2)
            sl = dict(kind="core", core_clock_port="clk",
                      islands=[dict(name="i0", clock_pin=dict(layer="M5", xy_um=[86.412, 98.4]))])
            (kd / "master_slice.json").write_text(json.dumps(sl))
            self.assertEqual(G.slice_clock_pins_out(kd, MS, ["clk"]), ["clk"])
            left = json.loads((kd / "pins.json").read_text())
            self.assertEqual([r["bus"] for r in left], ["a"])
            self.assertEqual(G.slice_clock_pins_out(kd, MS, ["clk"]), [])          # idempotent


class GeneratedKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_qc.py"), "--module", MODULE, "--out", cls.tmp.name],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        cls.kd = Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])
        cls.cfg = (cls.kd / "config.mk").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_lef_contract_records_gate_pins_2(self):
        """QC-A0-KITS-3 10-28: a LEF-contract kit stages plan_pins.json (the LEF pin centres) as its kit-relative
        pins_file, records pins_canon_sha256 and passes kit_contract.pins_canonical."""
        import hashlib
        sys.path.insert(0, str(HERE.parents[4] / "tools/die_plan"))
        import kit_contract
        fz = json.loads((self.kd / "freeze.json").read_text())
        self.assertEqual(fz["pins_file"], "plan_pins.json")
        self.assertTrue(fz["pins_contract_lef"].endswith(".lef"))
        self.assertEqual(fz["pins_sha256"], hashlib.sha256((self.kd / "plan_pins.json").read_bytes()).hexdigest())
        self.assertTrue(fz["pins_canon_sha256"])
        err, info = kit_contract.pins_canonical(self.kd)
        self.assertEqual(err, [])
        self.assertTrue(info["plan_file"].endswith("plan_pins.json"))

    def test_face_flops_anchors_patched(self):
        ff = (self.kd / "face_flops.tcl").read_text()
        skip = (self.kd / "face_guard_skip.txt").read_text().strip()
        self.assertEqual(re.findall(r"^set ff_skip_re \{([^\n]*?)\}", ff, re.M), [skip])
        self.assertNotIn("start_i", ff.split("set ff_skip_re", 1)[1].split("\n", 1)[0].split(";#")[0])
        self.assertIn("set ff_unreg [open $::env(RESULTS_DIR)/ot_unreg_pins.txt w]", ff)
        self.assertIn('puts $ff_unreg "$pass\\t$nm"', ff)
        tb = (self.kd / "tap_balance.tcl").read_text()
        self.assertEqual(re.findall(r"^set tb_port_re \{([^\n]*)\}", tb, re.M), [r"^(ck)(\[0\])?$"])

    def test_run_kit_preflight_steps(self):
        rk = (self.kd / "run_kit.sh").read_text()
        self.assertNotIn("@LINT_STEP@", rk)
        i_lint, i_sdc = rk.index("/work/rtl_lint.py /work"), rk.index("/work/sdc_lint.py /work")
        i_sel, i_synth = rk.index("/work/selrange_gate.py /work"), rk.index("\\$M synth")
        i_fg, i_lec = rk.index("/work/face_guard_core.py"), rk.index("/work/lec.py /work --netlist")
        i_ffg, i_goal = rk.index("OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc"), rk.index("\\$M $GOAL; rc")
        self.assertTrue(i_lint < i_sdc < i_sel < i_synth < i_fg < i_lec < i_ffg < i_goal)
        for marker in ("rc=8", "FAIL_PREFLOOR selrange (FAIL or NOT RUN)", "rc=3", "FAIL_PREFLOOR LEC NOT EQUIVALENT",
                       "rc=5", "LEC WARNING"):
            self.assertIn(marker, rk)
        for f in ("rtl_lint.py", "selrange_gate.py", "lec.py", "vclk_corner.tcl", "grt_pre.tcl", "grt_post.tcl",
                  "setRC_rcx.tcl", "clock_binding.json"):
            self.assertTrue((self.kd / f).is_file(), f)
        self.assertEqual(subprocess.run(["bash", "-n", str(self.kd / "run_kit.sh")]).returncode, 0)

    def test_config_rc_and_vclk(self):
        kv = dict(re.findall(r"^(?:override )?export (\S+) = (.*)$", self.cfg, re.M))   # last value wins
        self.assertEqual(kv["LAYER_PARASITICS_FILE"], "/work/setRC_rcx.tcl")
        self.assertEqual(kv["SET_RC_TCL"], "/work/setRC_rcx.tcl")
        self.assertEqual(kv["PRE_GLOBAL_ROUTE_TCL"], "/work/grt_pre_core.tcl")
        self.assertEqual(kv["POST_GLOBAL_ROUTE_TCL"], "/work/grt_post_core.tcl")
        self.assertIn("OT_HOLD_FF_MARGIN", kv)
        tt, ff = float(kv["OT_VCLK_TT"]), float(kv["OT_VCLK_FF"])
        cb = json.loads((self.kd / "clock_binding.json").read_text())
        self.assertEqual((cb["insertion_ps"]["tt"], cb["insertion_ps"]["ff"]), (tt, ff))
        self.assertTrue(0 < ff <= tt)
        lat = re.search(r"set_clock_latency -source ([\d.]+) \[get_clocks vclk\]", (self.kd / "constraint.sdc").read_text())
        self.assertAlmostEqual(float(lat.group(1)), tt, places=3)
        lctx = json.loads((self.kd / "sdc_lint.json").read_text())
        self.assertEqual((lctx["insertion_ps"], lctx["insertion_ff_ps"]), (tt, ff))
        self.assertNotIn("LEC_CHECK = 1", self.cfg)
        pre = (self.kd / "grt_pre_core.tcl").read_text()
        self.assertIn("source /work/drv.tcl", pre)
        post = (self.kd / "grt_post_core.tcl").read_text()
        self.assertLess(post.index("post_grt_drv.tcl"), post.index("source /work/grt_post.tcl"))



def _lef(pins_e, pins_w=0, w=172.824, h=41.064, pitch=0.096):
    out = [f"MACRO m\n  CLASS BLOCK ;\n  SIZE {w} BY {h} ;"]
    for i in range(pins_e):
        y = 0.768 + i * pitch
        out.append(f"  PIN e{i}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M4 ;\n        RECT {w - 0.024:.3f} {y:.3f} {w:.3f} {y + 0.024:.3f} ;\n    END\n  END e{i}")
    for i in range(pins_w):
        y = 0.768 + i * 2.0
        out.append(f"  PIN w{i}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M4 ;\n        RECT 0.000 {y:.3f} 0.024 {y + 0.024:.3f} ;\n    END\n  END w{i}")
    out.append("  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M4 ;\n        RECT 0 0 0.024 41 ;\n    END\n  END VDD\nEND m")
    return "\n".join(out)


class SramPinColumnHalo(unittest.TestCase):
    """QC-SU-SRAMHALO: strips in front of dense pin columns only, depth = halo + rho*turn*p_v/fill, orientation-aware"""

    def test_blockage_rects_leave_row_end_endcap_column(self):
        # the cut rows beside the macro end at the rows halo with a fixed TAPCELL endcap; no blockage rect may cover it
        s = G.pincol_halo_strips(_lef(410), [(90.72, 86.4, "R0")], 4.32)[0]
        x0, y0, x1, y1 = s["rect"]
        area = sum((q[2] - q[0]) * (q[3] - q[1]) for q in s["rects"])
        cy = [round(86.4 - 4.32 + k * 0.27, 3) for k in range(int((s["macro_rect"][3] - 86.4 + 8.64) / 0.27))]
        ex = s["macro_rect"][2] + 4.32 + 0.03                    # endcap origin as snapped by tapcell (prog L2h)
        for q in s["rects"]:
            for y in cy:
                self.assertFalse(q[0] < ex + 0.108 and q[2] > ex and q[1] < y + 0.27 and q[3] > y, (q, y))
        self.assertLess(area, (x1 - x0) * (y1 - y0))
        self.assertGreater(area, 0.95 * (x1 - x0) * (y1 - y0))

    def test_dense_column_depth_and_corner_extension(self):
        s = G.pincol_halo_strips(_lef(410), [(90.72, 86.4, "R0")], 4.32)
        self.assertEqual(len(s), 1)
        st = s[0]
        self.assertEqual(st["edge"], "E")
        rho = 410 / (409 * 0.096)   # pins / column span
        self.assertAlmostEqual(st["ext_um"], rho * 4.32 * 0.036 / 0.6, places=3)
        self.assertGreaterEqual(st["depth_um"], 4.32 + st["ext_um"])
        self.assertAlmostEqual(st["depth_um"] / 0.054, round(st["depth_um"] / 0.054), places=6)
        x0, y0, x1, y1 = st["rect"]
        self.assertAlmostEqual(x0, 90.72 + 172.824, places=4)
        self.assertAlmostEqual(x1 - x0, st["depth_um"], places=4)
        self.assertLess(y0, 86.4 + 0.78 - st["depth_um"] + 1e-6)   # extended past the column ends (corner junction)

    def test_sparse_column_and_power_ignored(self):
        s = G.pincol_halo_strips(_lef(0, pins_w=10), [(10, 10, "R0")], 4.32)
        self.assertEqual(s, [])

    def test_mirror_flips_edge(self):
        s = G.pincol_halo_strips(_lef(410), [(90.72, 86.4, "MY")], 4.32)
        self.assertEqual(s[0]["edge"], "W")
        self.assertAlmostEqual(s[0]["rect"][2], 90.72, places=4)

    def test_hits_and_tcl(self):
        s = G.pincol_halo_strips(_lef(410), [(0, 0, "R0")], 4.32)
        self.assertEqual(G.pch_hits(s, [("in", 175.0, 20.0), ("out", 190.0, 20.0)]), ["in"])
        self.assertIn("odb::dbBlockage_create", G.pch_tcl(s))

    def test_post_tapcell_clears_physical_cells_under_every_rect(self):
        # CORES-EARLY-2 (btab a1713 DPL-0033, 72 taps at macro x - 0.54 in the uncut rows beside the column ends)
        s = G.pincol_halo_strips(_lef(410), [(90.72, 86.4, "R0")], 4.32)
        t = G.pch_tap_tcl(s)
        self.assertIn("source /work/keepout_phys.tcl", t)
        self.assertIn("ot_clear_keepout_physical $b $ot_pch_rects sram_pincol_halo", t)
        for q in s[0]["rects"]:
            self.assertIn("{%g %g %g %g}" % tuple(q), t)


class SeamHold(unittest.TestCase):
    """DIE-QC-22 (COORD 10-28 19:05): opt-in --seam-hold SENDER,SEAM = the shared CLOCK-RESET IO-HOLD seam_hold contract
    (gen_phys.seam_hold, KV gen_core_kit_kv form): min input SENDER-SEAM, min output -SENDER, recorded in sdc_lint.json
    (sdc_lint checks sender + receiver = seam >= floor) and freeze.json; unset = legacy text byte-identical."""
    def test_legacy_text_unchanged(self):
        t = G.sdc(833.0, 250.0, 40.0, ["clk"], [], "m")
        self.assertEqual(t, G.sdc(833.0, 250.0, 40.0, ["clk"], [], "m", None))
        self.assertIn("set_input_delay -min -40.0000 -clock vclk $non_clk_in\n", t)
        self.assertIn("set_output_delay -min 0.0000 -clock vclk [all_outputs]\n", t)
        self.assertNotIn("seam_hold", t)

    def test_contract_text(self):
        t = G.sdc(833.0, 250.0, 40.0, ["clk"], [], "m", (25.0, 25.0))
        self.assertIn("set_input_delay -min 0.0000 -clock vclk $non_clk_in\n", t)
        self.assertIn("set_output_delay -min -25.0000 -clock vclk [all_outputs]\n", t)
        self.assertNotIn("-40.0000", t)

    def test_parse_refuses_bad_contracts(self):
        self.assertIsNone(G.parse_seam_hold(None, "m"))
        self.assertEqual(G.parse_seam_hold("25,25", "m"), (25.0, 25.0))
        for bad in ("25,10", "-1,25", "25", "a,b"):
            with self.assertRaises(SystemExit):
                G.parse_seam_hold(bad, "m")

    def test_generated_kit_carries_contract(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_qc.py"), "--module", MODULE, "--out", t,
                                "--seam-hold", "25,25"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            kd = Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])
            lctx = json.loads((kd / "sdc_lint.json").read_text())
            self.assertEqual((lctx["hold_in_min_ps"], lctx["hold_out_min_ps"], lctx["seam_hold_ps"]), (0.0, -25.0, 25.0))
            sys.path.insert(0, str(HERE.parents[4] / "tools/die_plan"))
            import sdc_lint
            self.assertEqual(sdc_lint.lint((kd / "constraint.sdc").read_text(), **lctx), [])
            fz = json.loads((kd / "freeze.json").read_text())
            self.assertEqual(fz["seam_hold"]["in_min_ps"], 0.0)
            self.assertEqual(fz["seam_hold"]["out_min_ps"], -25.0)
            self.assertIn("set_output_delay -min -25.0000", (kd / "constraint.sdc").read_text())


if __name__ == "__main__":
    unittest.main()
