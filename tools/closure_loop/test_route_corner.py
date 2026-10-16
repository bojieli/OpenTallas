"""LOOP-CORNER 2026-10-10: SM piece routes that set only OT_ORFS_CORNER_OVERRIDE=TC routed at SS (the {_SC} generator form
was left unpatched by tt_overlay), and ttb_routed_at_TC passed on an unrelated overlay mark.  The generator honours the
loop corner, the overlay patches the {_SC} form of old snapshots, and the check reads the liberties in the route logs."""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl
import route_corner_check as rcc
import tt_overlay as overlay

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GEN = REPO / "tools/hbm_accel_smh_physical.py"
CLEAN = {k: "" for k in ("OT_ORFS_CORNER", "OT_ORFS_CORNER_OVERRIDE", "OT_SMH_CORNER", "OT_TTB_CORNER_MARK")}
MACRO = ["physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"]


def load(path):
    spec = importlib.util.spec_from_file_location(f"gen_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lib_line(cfg):
    return next(l for l in cfg.split("\n") if "_LIB_FILES = $(" in l and not l.startswith("export BC_"))


SC_FORM = '''import os
from pathlib import Path


def config_mk(name, nick, die, macros, extra):
    lib_ss = " ".join(f"/src/{m}/{Path(m).name}_ss.lib" for m in macros)
    _SC = os.environ.get("OT_SMH_CORNER", "WC").strip().upper() or "WC"
    lib_su = lib_ss if _SC == "WC" else " ".join(f"/src/{m}/{Path(m).name}_tt.lib" for m in macros)
    lines = [f"export CORNER = {_SC}",
             f"export CORNERS = {_SC} BC", f"export {_SC}_LIB_FILES = $({_SC}_NLDM_LIB_FILES) {lib_su}",
             "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)"]
    return "\\n".join(lines) + "\\n"
'''


class GeneratorHonoursLoopCorner(unittest.TestCase):
    def cfg(self, **env):
        with patch.dict(os.environ, {**CLEAN, **env}):
            return load(GEN).config_mk("n", "k", (10, 10), MACRO, {})

    def test_override_tc_reads_tt_keeps_wc_name(self):
        line = lib_line(self.cfg(OT_ORFS_CORNER_OVERRIDE="TC"))
        self.assertEqual(line.split(" = ")[0], "export WC_LIB_FILES")
        self.assertIn("$(TC_NLDM_LIB_FILES)", line)
        self.assertIn("_tt.lib", line)
        self.assertNotIn("_ss.lib", line)

    def test_loop_env_tc_reads_tt(self):
        self.assertIn("$(TC_NLDM_LIB_FILES)", lib_line(self.cfg(OT_ORFS_CORNER="TC")))

    def test_default_and_keep_stay_ss(self):
        for env in ({}, {"OT_ORFS_CORNER": "WC"}):
            line = lib_line(self.cfg(**env))
            self.assertIn("$(WC_NLDM_LIB_FILES)", line)
            self.assertIn("_ss.lib", line)

    def test_smh_corner_tc_unchanged(self):
        cfg = self.cfg(OT_SMH_CORNER="TC")
        self.assertIn("export CORNERS = TC BC", cfg)
        self.assertIn("export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)", cfg)


class OverlayPatchesScForm(unittest.TestCase):
    def snap(self, text):
        d = Path(tempfile.mkdtemp())
        (d / "tools").mkdir()
        (d / "tools/hbm_accel_smh_physical.py").write_text(text)
        return d

    def run_overlay(self, d, mark):
        with patch.dict(os.environ, {**CLEAN, "OT_ORFS_CORNER": "TC", "OT_TTB_CORNER_MARK": str(mark)}):
            return overlay.ensure_smh(d)

    def test_sc_form_snapshot_patched_and_idempotent(self):
        d = self.snap(SC_FORM)
        mark = d / "mark.txt"
        msg = self.run_overlay(d, mark)
        self.assertFalse(any("missing" in m or "not patched" in m for m in msg), msg)
        once = (d / "tools/hbm_accel_smh_physical.py").read_text()
        self.assertEqual(self.run_overlay(d, mark), msg)
        self.assertEqual((d / "tools/hbm_accel_smh_physical.py").read_text(), once)
        with patch.dict(os.environ, CLEAN):
            line = lib_line(load(d / "tools/hbm_accel_smh_physical.py").config_mk("n", "k", (1, 1), MACRO, {}))
        self.assertIn("export WC_LIB_FILES = $(TC_NLDM_LIB_FILES)", line)
        self.assertIn("_tt.lib", line)
        self.assertNotIn("_ss.lib", line)
        self.assertIn("smh_config wc_reads_tt", mark.read_text())

    def test_real_pre_fix_commit_is_patched(self):
        """80412d770 (the SM cg jobs' generation) carries the {_SC} form"""
        r = subprocess.run(["git", "-C", str(REPO), "show", "80412d770:tools/hbm_accel_smh_physical.py"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("commit not available")
        d = self.snap(r.stdout)
        msg = self.run_overlay(d, d / "mark.txt")
        self.assertIn("SMH flow ({_SC} form): WC reads TT", msg)
        with patch.dict(os.environ, CLEAN):
            line = lib_line(load(d / "tools/hbm_accel_smh_physical.py").config_mk("n", "k", (10, 10), MACRO, {}))
        self.assertIn("$(TC_NLDM_LIB_FILES)", line)
        self.assertNotIn("_ss.lib", line)

    def test_fixed_generator_left_alone(self):
        d = self.snap(GEN.read_text())
        msg = self.run_overlay(d, d / "mark.txt")
        self.assertEqual(msg, ["SMH flow: generator honours OT_ORFS_CORNER (no patch)"])
        self.assertEqual((d / "tools/hbm_accel_smh_physical.py").read_text(), GEN.read_text())

    def test_old_wc_form_still_patched(self):
        old = SC_FORM.replace('f"export {_SC}_LIB_FILES = $({_SC}_NLDM_LIB_FILES) {lib_su}"', overlay.SMH_OLD) \
                     .replace('    lib_su = lib_ss if _SC == "WC" else " ".join(f"/src/{m}/{Path(m).name}_tt.lib" for m in macros)\n', "")
        d = self.snap(old + "# OT_SMH_POST_SDC\n")
        self.assertIn("SMH flow: WC reads TT", self.run_overlay(d, d / "mark.txt"))
        self.assertIn(overlay.SMH_NEW, (d / "tools/hbm_accel_smh_physical.py").read_text())

    def test_no_corner_lib_generator_not_patched(self):
        d = self.snap("def config_mk():\n    return ''\n")
        self.assertTrue(self.run_overlay(d, d / "m")[0].startswith("SMH: generator has no WC_LIB_FILES line"))


def write_log(root, rel, corners):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl"]
    for c, t in corners:
        pre = f"-corner {c} " if c else ""
        lines += [f"read_liberty {pre}/x/asap7sc7p5t_AO_RVT_{t}_nldm_211120.lib.gz",
                  f"read_liberty {pre}/x/asap7sc7p5t_SEQ_RVT_{t}_nldm_220123.lib"]
    p.write_text("\n".join(lines) + "\n")


CTS = "routes/lbl/logs/asap7/n/base/4_1_cts.log"


class RouteCornerCheck(unittest.TestCase):
    def root(self):
        return tempfile.mkdtemp()

    def test_ss_route_fails(self):
        r = self.root()
        write_log(r, CTS, [("WC", "SS"), ("BC", "FF")])
        ok, lines = rcc.check(r)
        self.assertFalse(ok)
        self.assertIn("WC=SS", lines[0])

    def test_tt_route_passes(self):
        r = self.root()
        write_log(r, CTS, [("WC", "TT"), ("BC", "FF")])
        write_log(r, "routes/lbl/logs/asap7/n/base/3_3_place_gp.log", [("TC", "TT"), ("BC", "FF")])
        self.assertTrue(rcc.check(r)[0])

    def test_single_corner_scene(self):
        r = self.root()
        write_log(r, CTS, [(None, "TT"), (None, "FF")])
        self.assertTrue(rcc.check(r)[0])
        write_log(r, CTS, [(None, "SS"), (None, "FF")])
        self.assertFalse(rcc.check(r)[0])

    def test_macro_ss_view_fails(self):
        r = self.root()
        write_log(r, CTS, [("WC", "TT"), ("BC", "FF")])
        with open(Path(r) / CTS, "a") as f:
            f.write("read_liberty -corner WC /src/physical/m/ot_sram_ss.lib\n")
        self.assertFalse(rcc.check(r)[0])

    def test_cal_and_attempts_ignored_unproven_fails(self):
        r = self.root()
        write_log(r, "routes/lbl_cal/logs/asap7/n/base/4_1_cts.log", [("WC", "SS"), ("BC", "FF")])
        write_log(r, "routes/lbl.attempt1/logs/asap7/n/base/4_1_cts.log", [("WC", "SS"), ("BC", "FF")])
        write_log(r, "src/results/old/4_1_cts.log", [("WC", "SS"), ("BC", "FF")])
        self.assertFalse(rcc.check(r)[0])             # no route log: unproven
        self.assertFalse(rcc.check(r, include_cal=True)[0])
        write_log(r, CTS, [("WC", "TT"), ("BC", "FF")])
        self.assertTrue(rcc.check(r)[0])

    def test_no_logs_fails(self):
        self.assertFalse(rcc.check(self.root())[0])


class VerdictCheckWiring(unittest.TestCase):
    CHK = {"name": "ttb_routed_at_TC", "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}

    def job(self, run):
        return {"run": run, "host": "localhost", "name": "j", "spec": {"block": "b", "source": {"commit": "c"}}}

    def run_check(self, run):
        cmd = cl.subst(cl.route_corner_check_cmd(self.CHK), self.job(run))
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

    def test_other_checks_untouched(self):
        c = {"name": "lef_check_MATCH", "cmd": "true"}
        self.assertEqual(cl.route_corner_check_cmd(c), "true")

    def test_unrelated_mark_no_longer_passes_ss_route(self):
        r = self.root_with_mark()
        write_log(r, CTS, [("WC", "SS"), ("BC", "FF")])
        p = self.run_check(r)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("ROUTE_CORNER FAIL", p.stdout)

    def test_tt_route_with_mark_passes(self):
        r = self.root_with_mark()
        write_log(r, CTS, [("WC", "TT"), ("BC", "FF")])
        p = self.run_check(r)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_mark_still_required(self):
        r = tempfile.mkdtemp()
        write_log(r, CTS, [("WC", "TT"), ("BC", "FF")])
        self.assertNotEqual(self.run_check(r).returncode, 0)

    def test_helper_shipped(self):
        self.assertIn("route_corner_check.py", cl.HELPERS)

    @staticmethod
    def root_with_mark():
        r = tempfile.mkdtemp()
        os.makedirs(f"{r}/cl")
        Path(f"{r}/cl/ttb_corner.txt").write_text("TC 1 direct_config_mk x6 wc_reads_tt\n")
        return r


if __name__ == "__main__":
    unittest.main()
