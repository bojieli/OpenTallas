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


if __name__ == "__main__":
    unittest.main()
