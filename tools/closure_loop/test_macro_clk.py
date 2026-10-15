"""MACRO-CLK (macro-clk-1010, 2026-10-10): macro clock signature from CTS logs + calibrate, the clustering wrapper,
the snapshot shipping, the loop flag and auto-react class f."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="macroclk_"))
import closure_loop as cl  # noqa: E402
import ck_insertion as ck  # noqa: E402
import hold_corners_patch as hcp  # noqa: E402
import macro_clk as mc  # noqa: E402
from test_auto_react import Base, job, spec  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WRAPPER = REPO / "physical/common_flow/macro_cts_cluster.tcl"

# ds-1010 lcr0ctl calibrate 4_1_cts.log (the failing shape) and the clustered successor's
LOG_SHALLOW = """==== /r/routes/x_cal/work/orfs/logs/asap7/d/base/4_1_cts.log
clock_tree_synthesis -sink_clustering_enable -repair_clock_nets
[INFO CTS-0098] Clock net "ck[0]"
[INFO CTS-0099]  Sinks 10
[INFO CTS-0100]  Leaf buffers 0
[INFO CTS-0101]  Average sink wire length 436.55 um
[INFO CTS-0102]  Path depth 4 - 4
[INFO CTS-0098] Clock net "ck[0]_regs"
[INFO CTS-0099]  Sinks 12749
[INFO CTS-0100]  Leaf buffers 763
[INFO CTS-0101]  Average sink wire length 321.49 um
[INFO CTS-0102]  Path depth 8 - 10
Took 19 seconds: clock_tree_synthesis -sink_clustering_enable -repair_clock_nets
"""
LOG_CLUSTERED = """==== /r/routes/x/work/orfs/logs/asap7/d/base/4_1_cts.log
clock_tree_synthesis -sink_clustering_enable -repair_clock_nets
OT_MACRO_CTS 10 clocked macros: -macro_clustering_size 2 -macro_clustering_max_diameter 40
[INFO CTS-0098] Clock net "ck[0]"
[INFO CTS-0099]  Sinks 10
[INFO CTS-0100]  Leaf buffers 0
[INFO CTS-0101]  Average sink wire length 300.00 um
[INFO CTS-0102]  Path depth 4 - 4
[INFO CTS-0098] Clock net "ck[0]_regs"
[INFO CTS-0099]  Sinks 12749
[INFO CTS-0100]  Leaf buffers 763
"""
LOG_NOMACRO = """==== /r/routes/x/work/orfs/logs/asap7/d/base/4_1_cts.log
[INFO CTS-0098] Clock net "ck"
[INFO CTS-0099]  Sinks 9
[INFO CTS-0100]  Leaf buffers 0
[INFO CTS-0101]  Average sink wire length 400.00 um
"""
CALIB_FLAG = {"n": 10, "slew_ps": 120.0, "late_ps": 30.0, "flag": True,
              "outliers": [{"pin": "u.u_ep.u_fifo.g_t[2].u_m/clk", "why": "ff slew 210 ps > 120; ff 61 ps after the register mean > 30"}]}


class Parse(unittest.TestCase):
    def test_shallow_macro_tree_is_the_signature(self):
        logs = mc.parse_cts_logs(LOG_SHALLOW)
        self.assertEqual(logs[0]["macro_nets"], ["ck[0]"])
        self.assertEqual(logs[0]["trees"]["ck[0]"], dict(sinks=10, leaf=0, wire=436.55, depth=4))
        sig = mc.signature(logs)
        self.assertTrue(sig["hit"])
        self.assertIs(sig["clustered"], False)
        self.assertIn("10 macros on 0 leaf buffers", sig["why"])
        # lcrpx default CTS: 11 macro sinks on 4 leaf buffers (some macros on 200+ ps slew nets) is the defect too;
        # the clustered tree (11 on 8) is not
        for leaf, hit in ((4, True), (8, False)):
            t = LOG_SHALLOW.replace("Sinks 10", "Sinks 11").replace("Leaf buffers 0", f"Leaf buffers {leaf}", 1)
            self.assertIs(mc.signature(mc.parse_cts_logs(t))["hit"], hit)

    def test_clustered_run_is_structural(self):
        sig = mc.signature(mc.parse_cts_logs(LOG_CLUSTERED))
        self.assertTrue(sig["hit"])
        self.assertIs(sig["clustered"], True)

    def test_register_only_net_is_not_a_macro_tree(self):
        sig = mc.signature(mc.parse_cts_logs(LOG_NOMACRO))
        self.assertFalse(sig["hit"])
        self.assertIsNone(sig["clustered"])

    def test_calibrate_flag_alone_hits(self):
        sig = mc.signature([], CALIB_FLAG)
        self.assertTrue(sig["hit"])
        self.assertIn("1/10 macro clock pins", sig["why"])
        self.assertIn("MACRO-CLK flag after CTS", mc.calib_flag_text(CALIB_FLAG))
        self.assertIsNone(mc.calib_flag_text(dict(CALIB_FLAG, flag=False, outliers=[])))

    def test_scan_cmd_skips_the_snapshot(self):
        self.assertIn("-path '*/src' -prune", mc.scan_cmd("/r/j"))


class CkInsertion(unittest.TestCase):
    def test_outliers(self):
        rows = [("m0/clk", 400.0, 60.0, "n0"), ("m1/clk", 452.0, 210.0, "n1"), ("m2/clk", 395.0, 140.0, "n1")]
        rec = {"ff": {"macros": ck.macro_summary(rows, 400.0)},
               "tt": {"macros": ck.macro_summary([("m0/clk", 500.0, 50.0, "n0")], 500.0)}}
        self.assertEqual((rec["ff"]["macros"]["nets"], rec["ff"]["macros"]["max_per_net"]), (2, 2))
        v = ck.macro_outliers(rec)
        self.assertTrue(v["flag"])
        self.assertEqual([x["pin"] for x in v["outliers"]], ["m1/clk", "m2/clk"])
        self.assertIn("ff 52 ps after the register mean", v["outliers"][0]["why"])
        self.assertFalse(ck.macro_outliers({"ff": {"macros": None}})["flag"])

    def test_macro_libs_from_config_and_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            base = run / "routes/x/work/orfs/results/asap7/d/base"
            base.mkdir(parents=True)
            m = "physical/asap7_memory_macros_v2/m1/m1"
            (run / "src" / m).parent.mkdir(parents=True)
            for c in ("tt", "ff"):
                (run / "src" / f"{m}_{c}.lib").write_text("")
            (run / "routes/x/work/orfs/config.mk").write_text(
                f"export WC_LIB_FILES = $(WC_NLDM_LIB_FILES) /src/{m}_tt.lib\nexport BC_LIB_FILES = x /src/{m}_ff.lib\n")
            root, libs = ck.macro_libs(base, "ff")
            self.assertEqual((root, libs), (run / "src", [f"/src/{m}_ff.lib"]))
            self.assertEqual(ck.macro_libs(base, "ss"), (None, []))      # no _ss view in the snapshot
            self.assertIn("read_liberty /src/x_ff.lib", ck.tcl("ff", "4_1_cts.odb", "4_cts.sdc", False, "ck", ["/src/x_ff.lib"]))


@unittest.skipUnless(shutil.which("tclsh"), "tclsh")
class Wrapper(unittest.TestCase):
    def run_tcl(self, body, env=None):
        stub = r"""
proc clock_tree_synthesis {args} { puts "CTS_CALLED $args" }
namespace eval ord {}
set ::nmac 3
proc ord::get_db_block {} { return BLK }
proc BLK {m} { set r {}; for {set i 0} {$i < $::nmac} {incr i} { lappend r INST } ; lappend r STD; return $r }
proc INST {m} { switch $m { getMaster { return MBLK } getITerms { return {IT} } } }
proc STD {m} { switch $m { getMaster { return MSTD } getITerms { return {} } } }
proc MBLK {m} { return 1 }
proc MSTD {m} { return 0 }
proc IT {m} { switch $m { isInputSignal { return 1 } getMTerm { return MT } getNet { return NET } } }
proc MT {m} { return CLOCK }
proc NET {m} { return SIGNAL }
"""
        e = dict(os.environ, **(env or {}))
        for k in ("OT_CTS_MACRO_CLUSTER", "OT_CTS_MACRO_SIZE", "OT_CTS_MACRO_DIAM"):
            if k not in (env or {}):
                e.pop(k, None)
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "t.tcl"
            f.write_text(stub + f"source {WRAPPER}\n" + body)
            return subprocess.run(["tclsh", str(f)], capture_output=True, text=True, env=e, timeout=60).stdout

    def test_appends_macro_clustering(self):
        out = self.run_tcl("clock_tree_synthesis -sink_clustering_enable -repair_clock_nets\n")
        self.assertIn("CTS_CALLED -sink_clustering_enable -repair_clock_nets -macro_clustering_size 2 "
                      "-macro_clustering_max_diameter 40", out)
        self.assertIn("OT_MACRO_CTS 3 clocked macros", out)

    def test_respects_caller_optout_and_small_blocks(self):
        out = self.run_tcl("clock_tree_synthesis -macro_clustering_size 3\n")
        self.assertIn("CTS_CALLED -macro_clustering_size 3\n", out)
        out = self.run_tcl("clock_tree_synthesis -repair_clock_nets\n", {"OT_CTS_MACRO_CLUSTER": "0"})
        self.assertIn("CTS_CALLED -repair_clock_nets\n", out)
        out = self.run_tcl("set ::nmac 1\nclock_tree_synthesis -repair_clock_nets\n")
        self.assertIn("OT_MACRO_CTS skipped: 1 clocked macro", out)
        out = self.run_tcl("clock_tree_synthesis\n", {"OT_CTS_MACRO_SIZE": "3", "OT_CTS_MACRO_DIAM": "25"})
        self.assertIn("CTS_CALLED -macro_clustering_size 3 -macro_clustering_max_diameter 25", out)
        out = self.run_tcl("clock_tree_synthesis\n", {"OT_CTS_MACRO_SIZE": "1"})     # TritonCTS segfaults at 1
        self.assertIn("CTS_CALLED -macro_clustering_size 2 -macro_clustering_max_diameter 40", out)

    def test_idempotent_double_source(self):
        out = self.run_tcl(f"source {WRAPPER}\nclock_tree_synthesis -x\n")
        self.assertEqual(out.count("-macro_clustering_size"), 2)   # the OT_MACRO_CTS line + one CTS call, not doubled
        self.assertIn("CTS_CALLED -x -macro_clustering_size 2 -macro_clustering_max_diameter 40\n", out)

    def test_orfs_hold_mm_sources_it(self):
        self.assertIn("macro_cts_cluster.tcl", (REPO / "tools/orfs_hold_mm.tcl").read_text())


class Shipping(unittest.TestCase):
    def test_hold_corners_patch_ships_the_wrapper(self):
        with tempfile.TemporaryDirectory() as t:
            src = Path(t)
            (src / "tools").mkdir()
            shutil.copy2(REPO / "tools/run_abi3_physical.py", src / "tools/run_abi3_physical.py")
            hcp.patch(str(src))
            dst = src / "physical/common_flow/macro_cts_cluster.tcl"
            self.assertEqual(dst.read_bytes(), WRAPPER.read_bytes())
            self.assertEqual((src / "tools/orfs_hold_mm.tcl").read_bytes(), (REPO / "tools/orfs_hold_mm.tcl").read_bytes())
            self.assertNotIn("macro_cts_cluster", hcp.patch(str(src)))       # idempotent
        self.assertIn("macro_cts_cluster.tcl", " ".join(cl.HELPERS))


class LoopFlag(unittest.TestCase):
    def test_calibration_flag_event(self):
        j = dict(name="j", events=[], calibration={"env": {}})
        with patch.object(cl, "ledger") as lg, patch.object(cl, "save_job"):
            cl.macro_clk_flag(j, {"macro_clk": CALIB_FLAG})
        self.assertEqual(j["calibration"]["macro_clk"], CALIB_FLAG)
        self.assertTrue(any("MACRO-CLK flag after CTS" in e for e in j["events"]))
        lg.assert_called_once()
        j2 = dict(name="j2", events=[], calibration={"env": {}})
        cl.macro_clk_flag(j2, {"env": {}})
        self.assertNotIn("macro_clk", j2["calibration"])

    def test_launch_env_optout_and_shim(self):
        bodies = []

        def fake_ssh(host, c, input=None, **k):
            if input is not None:
                bodies.append(input)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        for extra, want in (({"macro_cts": False}, True), ({}, False)):
            bodies.clear()
            sp = {"name": "t", "block": "b", "route_hold_corners": "keep", "source": {"branch": "main", "commit": "c" * 40},
                  "stages": {}, **extra}
            j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": sp, "commit_full": "c" * 40, "attempt": 1,
                 "created": "2026-10-08T19:00:00-07:00"}
            with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
                cl.launch_stage(j, {"kind": "route", "key": "route", "threads": 4}, "echo x")
            self.assertEqual("export OT_CTS_MACRO_CLUSTER=0" in bodies[0], want)
            self.assertIn("-e OT_CTS_MACRO_CLUSTER -e OT_CTS_MACRO_SIZE -e OT_CTS_MACRO_DIAM", bodies[0])


class ClassF(Base):
    def setUp(self):
        super().setUp()
        self.ssh_out = ""
        p = patch.object(cl, "ssh", lambda h, c, **k: SimpleNamespace(returncode=0, stdout=self.ssh_out, stderr=""))
        p.start()
        self.addCleanup(p.stop)

    def test_shallow_macro_tree_successor_before_pinflop(self):
        self.ssh_out = LOG_SHALLOW
        sp = spec("ln", owner="Claude:ds-1010", pinflop_ref=False)
        j = job("ln", "EARLY_FAIL_HOLD", spec=sp, stage_started="2026-10-10T05:00", rtl_boundary_verdict="PASS")
        self.assertEqual(self.run_pass(j), [("ln", "f:ln-arf")])
        s = self.drop("ln-arf")
        self.assertEqual((s["auto_react_parent"], s["auto_react_class"], s["macro_cts"]), ("ln", "f", True))
        self.assertEqual(s["source"]["commit"], "abcdef123")
        self.assertIs(cl.load_job("ln")["macro_clk_sig"]["hit"], True)

    def test_clustered_run_goes_to_owner_log(self):
        self.ssh_out = LOG_CLUSTERED
        j = job("ln", "EARLY_FAIL_HOLD", spec=spec("ln", owner="Claude:ds-1010"), pinflop_ref_applied=True)
        self.assertEqual(self.run_pass(j), [("ln", "none")])
        self.assertIn("WITH the clustering default on", (self.tk / "ds-1010.log").read_text())

    def test_no_signature_falls_through_to_c(self):
        self.ssh_out = LOG_NOMACRO
        sp = spec("hf", pinflop_ref=False)
        j = job("hf", "EARLY_FAIL_HOLD", spec=sp, stage_started="2026-10-10T05:00", rtl_boundary_verdict="PASS")
        self.assertEqual(self.run_pass(j), [("hf", "c:hf-arc")])

    def test_needs_rtl_hold_only(self):
        self.ssh_out = LOG_SHALLOW
        j = job("nr", metrics=dict(ss_ps=-60.0, ff_ps=-80.0, drc=0))       # deep setup miss too: not class f
        self.assertEqual(self.run_pass(j), [("nr", "none")])
        j = job("nh", spec=spec("nh", block="b2"), metrics=dict(ss_ps=-5.0, ff_ps=-80.0, drc=0))
        self.assertEqual(self.run_pass(j), [("nh", "f:nh-arf")])

    def test_successor_and_optout(self):
        self.ssh_out = LOG_SHALLOW
        sp = spec("ln-arf", auto_react_parent="ln", auto_react_class="f")
        j = job("ln-arf", "EARLY_FAIL_HOLD", spec=sp, pinflop_ref_applied=True)
        self.assertEqual(self.run_pass(j), [("ln-arf", "none")])
        sp = spec("lo", block="b3", macro_cts=False)
        j = job("lo", "EARLY_FAIL_HOLD", spec=sp, pinflop_ref_applied=True)
        self.assertEqual(self.run_pass(j), [("lo", "none")])
        self.assertIsNone(self.drop("lo-arf"))


if __name__ == "__main__":
    unittest.main()
