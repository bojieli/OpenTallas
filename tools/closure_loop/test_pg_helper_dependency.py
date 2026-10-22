"""INFRA-PG 2026-10-19: every helper clk_net_protect.tcl calls is sourced, standard and strict, through the TT overlay
snapshot.  ot_qkh_ktree_lkp-lkp1-52f03a544 died in CTS ('cts.tcl, 6 invalid command name
"ot_pg_install_unsupported_birth_guards"'): the fleet snapshot shipped main's clk_net_protect.tcl over a pinned src
whose native_pg_binding.tcl predated that proc.  These tests execute the real Tcl hooks (tclsh, OpenROAD commands
stubbed) on a standard stale-src fixture, a strict fixture, and the negative (stale binding / snapshot without one)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tt_overlay as overlay
import helper_overlay as HO

HERE = Path(__file__).resolve().parent
CF = HERE.parents[1] / "physical/common_flow"
TCLSH = shutil.which("tclsh")
STUBS = """
proc write_db {args} {return written}
proc estimate_parasitics {args} {return est}
proc clock_tree_synthesis {args} {return native_cts}
proc repair_timing {args} {return native_rt}
namespace eval ord {proc get_db_block {} {return NULL}}
"""


def stale_binding():
    """main's binding without the procs the 52f03a544 src lacked (same failure as the pinned src)."""
    text = (CF / "native_pg_binding.tcl").read_text()
    for name in ("ot_pg_install_unsupported_birth_guards", "ot_pg_standard_bind", "ot_pg_bind_batch_before_protect"):
        text = text.replace(f"proc {name} ", f"proc ot_pg_fixture_removed_{name} ")
    return text


class Fixture:
    def __init__(self, snapshot_binding=True):
        self.root = Path(tempfile.mkdtemp(prefix="ot-pgdep-"))
        self.ovl = self.root / "ovl"
        (self.ovl / "tools/closure_loop").mkdir(parents=True)
        for n in ("tt_overlay.py", "h1_patch.py"):
            shutil.copy2(HERE / n, self.ovl / "tools/closure_loop" / n)
        ocf = self.ovl / "physical/common_flow"
        ocf.mkdir(parents=True)
        for n in overlay.COMMON:
            if n != overlay.PG_BINDING or snapshot_binding:
                shutil.copy2(CF / n, ocf / n)
        self.src = self.root / "src"
        scf = self.src / "physical/common_flow"
        scf.mkdir(parents=True)
        (scf / "native_pg_binding.tcl").write_text(stale_binding())         # pinned src predates the proc
        (scf / "clk_net_protect.tcl").write_text("# pinned src's older hook\n")
        (self.src / "physical/blk").mkdir(parents=True)
        (self.src / "physical/blk/config.mk").write_text("export DESIGN_NAME = blk\n")

    def run_overlay(self):
        return subprocess.run([sys.executable, str(self.ovl / "tools/closure_loop/tt_overlay.py"), str(self.src)],
                              capture_output=True, text=True, timeout=120)

    def hooks(self, case, fixes="physical/common_flow/clk_net_protect.tcl"):
        """The overlay's own apply_cts_fix_hooks (the code tt_overlay patches into run_abi3_physical.py)."""
        ns = dict(ROOT=self.src, Path=Path, os=os, re=re, shutil=shutil, json=json)
        exec(overlay.HOOKS_FN.replace("@TTB_SRC@", str(self.src)), ns)
        old = os.environ.get("OT_CTS_FIX_HOOKS")
        os.environ["OT_CTS_FIX_HOOKS"] = fixes
        try:
            return ns["apply_cts_fix_hooks"]([], case)
        finally:
            os.environ.pop("OT_CTS_FIX_HOOKS") if old is None else os.environ.__setitem__("OT_CTS_FIX_HOOKS", old)


def tcl(script, env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_PG_")}
    e.update(env or {})
    with tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False) as f:     # a script file: errors exit non-zero
        f.write(STUBS + script)
    try:
        return subprocess.run([TCLSH, f.name], capture_output=True, text=True, timeout=60, env=e)
    finally:
        os.unlink(f.name)


@unittest.skipUnless(TCLSH, "tclsh not installed")
class PgHelperDependencyTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.case = self.fx.root / "case"
        self.case.mkdir()

    def tearDown(self):
        shutil.rmtree(self.fx.root, ignore_errors=True)

    def test_standard_stale_src_overlay_ships_coherent_binding_and_hook_executes(self):
        r = self.fx.run_overlay()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("shipped common_flow/native_pg_binding.tcl", r.stdout)
        scf = self.fx.src / "physical/common_flow"
        self.assertEqual((scf / "native_pg_binding.tcl").read_bytes(), (CF / "native_pg_binding.tcl").read_bytes())
        self.assertEqual(overlay.pg_dependency_gaps(scf), [])
        self.fx.hooks(self.case)
        hook = self.case / "hooks/ot_cts_fix_0_clk_net_protect.tcl"
        self.assertEqual((self.case / "hooks/native_pg_binding.tcl").read_bytes(),
                         (CF / "native_pg_binding.tcl").read_bytes())
        t = tcl(f"set ::env(OT_PG_STRICT) 0\nsource {hook}\n"
                "if {[info commands ot_protect_clock_tree] eq \"\"} {error NO_PROTECT}\n"
                "if {[clock_tree_synthesis] ne \"native_cts\"} {error STANDARD_GUARDED}\nputs STANDARD_OK\n")
        self.assertEqual(t.returncode, 0, t.stdout + t.stderr)
        self.assertIn("STANDARD_OK", t.stdout)

    def test_strict_fixture_hook_installs_guards_from_coherent_binding(self):
        self.assertEqual(self.fx.run_overlay().returncode, 0)
        self.fx.hooks(self.case)
        hook = self.case / "hooks/ot_cts_fix_0_clk_net_protect.tcl"
        for env in ({}, {"OT_PG_HELPER": str(self.fx.src / "physical/common_flow/native_pg_binding.tcl")}):
            t = tcl(f"set ::env(OT_PG_STRICT) 1\nsource {hook}\n"
                    "if {[info commands ot_pg_original_write_db] eq \"\"} {error NO_WRITE_GUARD}\n"
                    "if {![catch clock_tree_synthesis msg] || ![string match *OT_PG_NATIVE_BIRTH_CAPABILITY_REQUIRED* $msg]} "
                    "{error NO_BIRTH_GUARD}\nputs STRICT_OK\n", env)
            self.assertEqual(t.returncode, 0, t.stdout + t.stderr)
            self.assertIn("STRICT_OK", t.stdout)

    def test_negative_stale_binding_beside_hook_reproduces_cts_crash(self):
        hooks = self.case / "hooks"
        hooks.mkdir()
        shutil.copy2(CF / "clk_net_protect.tcl", hooks / "ot_cts_fix_0_clk_net_protect.tcl")
        (hooks / "native_pg_binding.tcl").write_text(stale_binding())
        t = tcl(f"set ::env(OT_PG_STRICT) 0\nsource {hooks / 'ot_cts_fix_0_clk_net_protect.tcl'}\n")
        self.assertNotEqual(t.returncode, 0)
        self.assertIn('invalid command name "ot_pg_install_unsupported_birth_guards"', t.stderr)
        self.assertEqual(overlay.pg_dependency_gaps(hooks, ["ot_cts_fix_0_clk_net_protect.tcl"]),
                         [("ot_cts_fix_0_clk_net_protect.tcl", ["ot_pg_bind_batch_before_protect",
                                                               "ot_pg_install_unsupported_birth_guards",
                                                               "ot_pg_standard_bind"])])

    def test_negative_snapshot_without_binding_refuses_before_route(self):
        fx = Fixture(snapshot_binding=False)
        try:
            r = fx.run_overlay()
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("OT_PG_HELPER_DEPENDENCY missing: clk_net_protect.tcl calls", r.stdout)
            self.assertIn("ot_pg_install_unsupported_birth_guards", r.stdout)
        finally:
            shutil.rmtree(fx.root, ignore_errors=True)


class PgSnapshotAndPlanTests(unittest.TestCase):
    def test_main_common_hooks_have_no_gaps(self):
        self.assertEqual(overlay.pg_dependency_gaps(CF), [])
        self.assertEqual(overlay.COMMON[0], overlay.PG_BINDING)

    def test_snapshot_refresh_ships_binding_before_its_hooks(self):
        import closure_loop as cl
        names = [n for n, d in cl.TTB_FILES if d == "physical/common_flow"]
        self.assertLess(names.index("native_pg_binding.tcl"), names.index("clk_net_protect.tcl"))
        self.assertTrue(set(overlay.COMMON) <= set(names))
        self.assertIn("physical/common_flow/native_pg_binding.tcl", HO.helper_paths())   # every plan ships it


if __name__ == "__main__":
    unittest.main()
