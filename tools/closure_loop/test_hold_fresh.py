"""HOLD-FRESH (ROOT 2026-10-17): a frozen 4_1_cts hold repair is re-run ONCE in a fresh OpenROAD process from the CTS
checkpoint (OT_HOLD_FRESH=cts) instead of EARLY_FAIL_HOLD.  Q-IO W head w5: -27.249 ps frozen for 8,700 iterations in
the route's session; the identical CTS state converged in a fresh session (-50.4 -> +31.4)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl
import stuckscan as ss
from test_hold_stop import tile_like
from test_stuckscan import ProbeAndGates, job, make_run

HERE = Path(__file__).resolve().parent
TCL = HERE.parent / "orfs_hold_mm.tcl"
sys_path = str(HERE.parent)


def w5_like():
    """the W head w5 signature: converging, then WNS flat at -27.249 for >2000 it while TNS barely moves"""
    conv = [(int(9000 * k / 39), -50.44 + (50.44 - 27.249) * k / 39) for k in range(40)]
    flat = [(9000 + 25 * k, -27.249) for k in range(1, 41)]
    rows = "\n".join(f"{100 * k:9d} |       0 | {b:7d} |            0 |    +0.5% | {w:7.3f} | -50.213 | u.x[{k}]$_DFF_P_/D"
                     for k, (b, w) in enumerate(conv + flat))
    return "OT_HOLD_GUARD start: x\n[INFO RSZ-0046] Found 8920 endpoints with hold violations.\n" + rows


class Gate(ProbeAndGates):
    def test_w5_signature_is_hold_fresh(self):
        d = self.hold_diag(w5_like(), fresh_used=False)
        self.assertEqual((d["action"], d["kind"]), ("hold_fresh", "hold_fresh"))
        self.assertIn("fresh OpenROAD process", d["why"][0])
        self.assertIn("not converging", d["why"][0])

    def test_once_per_job(self):
        d = self.hold_diag(w5_like(), fresh_used=True)
        self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")
        self.assertIn("HOLD-FRESH already used once", d["why"][0])

    def test_nearmiss_keeps_hold_stop(self):
        d = self.hold_diag(tile_like(-3.569), fresh_used=False)
        self.assertEqual(d["action"], "hold_stop")

    def test_spec_opt_out(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=0, count=0, tns=0, tmp="4_1_cts.tmp.log", tmp_text=w5_like(), ages=self.HOLD_AGES)
            j = job(run=str(run))
            j["spec"]["hold_fresh"] = False
            d = self.diag(run, j=j)
        self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")

    def test_buffer_explosion_while_improving_is_not_fresh(self):
        # cap exceeded but WNS still gains 1 ps / 100 it: a genuine buffer explosion (design problem)
        rows = "\n".join(f"{100 * k:9d} |       0 | {4000 * k:7d} |            0 |    +6.1% | {-90 + k:7.3f} |   0.000 | "
                         f"u.x$_DFF_P_/D" for k in range(30))
        d = self.hold_diag("[INFO RSZ-0046] Found 90000 endpoints with hold violations.\n" + rows, fresh_used=False)
        self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")
        self.assertIn("buffer cap", d["why"][0])

    def test_buffer_cap_on_frozen_wns_is_fresh(self):
        hd = dict(series=[[0, 0, -60.0], [1000, 30000, -40.5], [3000, 65000, -40.0]], guard=True)
        b = dict(current="4_1_cts.tmp.log", hold=hd)
        with patch.object(ss, "place_instances", return_value=192064):
            hv = ss.hold_verdict(hd, b, 3600)
        self.assertIn("buffer cap", hv)
        self.assertEqual(ss.hold_fresh_plan(b, {}, hv), dict(stage="cts", ws=-40.0))
        self.assertIsNone(ss.hold_fresh_plan(dict(b, current="5_1_grt.tmp.log"), {}, hv))   # CTS only

    def test_fresh_session_stall_early_fails(self):
        # the resumed route: 4_1_cts deferred, the fresh-session repair inside 5_1_grt freezes too -> EARLY_FAIL_HOLD
        txt = "OT_HOLD_FRESH start: hold ws -50.44 tns -9000.0 viol 812 (fresh process)\n" + w5_like()
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=0, count=0, tns=0, tmp="5_1_grt.tmp.log", tmp_text=txt,
                           ages=dict(self.HOLD_AGES, **{"4_1_cts.log": 7000}))
            o = self.probe(run)
            self.assertEqual(o["bases"][0]["hold"]["fresh"], "start")
            j = job(run=str(run), hold_fresh=["cts"], hold_fresh_log=[dict(stage="cts")])
            d = ss.diagnose(j, o, {}, [j], set(), 1e12)
        self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")
        self.assertIn("fresh-process CTS hold repair is not converging either", d["why"][0])

    def test_probe_sees_fresh_done(self):
        o = self.probe_text("OT_HOLD_FRESH start: x\nOT_HOLD_FRESH done: hold ws -50.44 -> 31.40\n")
        self.assertEqual(o["bases"][0]["hold"]["fresh"], "done")


class LoopSide(unittest.TestCase):
    def gate(self, resume_side_effect=None):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=0, count=0, tns=0, tmp="4_1_cts.tmp.log", tmp_text=w5_like(),
                           ages=ProbeAndGates.HOLD_AGES)
            j = job(run=str(run))
            with patch.object(cl, "STATE", Path(t)), \
                    patch.object(cl, "hold_fresh_resume", side_effect=resume_side_effect) as h, \
                    patch.object(cl, "early_fail_finish") as ef, patch.object(cl, "event") as ev, \
                    patch.object(ss, "failtrig_item"):
                cl.early_fail_gate(j, dict(key="route", kind="route"))
        return h, ef, ev

    def test_daemon_gate_resumes_in_fresh_process(self):
        h, ef, _ = self.gate()
        h.assert_called_once()
        self.assertIn("HOLD-FRESH", h.call_args[0][1])
        ef.assert_not_called()

    def test_daemon_gate_early_fails_when_resume_impossible(self):
        h, ef, ev = self.gate(ValueError("no checkpoint"))
        ef.assert_called_once()
        self.assertEqual(ef.call_args[0][1], "EARLY_FAIL_HOLD")
        self.assertIn("HOLD-FRESH not possible", ev.call_args_list[0][0][1])

    def resume(self, j):
        chk = subprocess.CompletedProcess([], 0, stdout="RESUME_FROM=4_1_cts\nRESUME_OK=1\n", stderr="")
        with patch.object(cl, "stage_list", return_value=[dict(key="route", kind="route")]), \
                patch.object(cl, "stage_checkpoint_resume", return_value=chk) as scr, \
                patch.object(cl, "event"), patch.object(cl, "ledger"), patch.object(cl, "experiment"):
            cl.hold_fresh_resume(j, "stuckscan: 4_1_cts hold repair frozen")
        return scr

    def test_resume_sets_env_state_once(self):
        j = dict(name="x", status="RUNNING", stage_idx=0, attempt=1, host="h", run="/r", spec={})
        scr = self.resume(j)
        self.assertEqual(scr.call_args[0][1:], ("4_1_cts", "hold-fresh"))
        self.assertEqual((j["status"], j["attempt"], j["hold_fresh"], j["resume"]["kind"]), ("READY", 2, ["cts"], "hold_fresh"))
        self.assertEqual(len(j["hold_fresh_log"]), 1)
        with self.assertRaises(ValueError):
            self.resume(j)

    def test_env_and_shim(self):
        src = (HERE / "closure_loop.py").read_text()
        self.assertIn("export OT_HOLD_FRESH=", src)
        self.assertEqual(cl.DOCKER_SHIM.count("-e OT_HOLD_FRESH"), 2)

    def test_hold_stop_resume_unchanged_after_refactor(self):
        j = dict(name="x", status="RUNNING", stage_idx=0, attempt=1, host="h", run="/r", spec={})
        chk = subprocess.CompletedProcess([], 0, stdout="RESUME_OK=1\n", stderr="")
        with patch.object(cl, "stage_list", return_value=[dict(key="route", kind="route")]), \
                patch.object(cl, "stage_checkpoint_resume", return_value=chk) as scr, \
                patch.object(cl, "event"), patch.object(cl, "ledger"), patch.object(cl, "experiment"):
            cl.hold_stop_resume(j, "cts", 8077, "near miss")
        self.assertEqual(scr.call_args[0][1:], ("4_1_cts", "hold-stop"))
        self.assertEqual(j["hold_stop"], {"cts": 8077, "grt": 0})

    def test_events_from_receipt(self):
        rec = dict(schema="opentallas.hold_fresh.v1", hold_ws_before_ps=-50.44, hold_ws_after_ps=31.4, hold_tns_before_ps=-9000,
                   hold_tns_after_ps=0, viol_before=812, viol_after=0, instances_added=8067, seconds=900, stalled=False)
        j = dict(name="x", host="h", run="/r", attempt=2)
        out = subprocess.CompletedProcess([], 0, stdout=json.dumps(rec), stderr="")
        with patch.object(cl, "ssh", return_value=out), patch.object(cl, "event") as ev, patch.object(cl, "ledger"):
            cl.hold_fresh_events(j)
            cl.hold_fresh_events(j)            # same attempt: no duplicate event
        self.assertEqual(ev.call_count, 1)
        self.assertIn("-50.44 -> 31.4", ev.call_args[0][1])
        self.assertEqual(j["hold_fresh_result"]["attempt"], 2)


class OrfsPatch(unittest.TestCase):
    def test_pre_grt_hook_patch(self):
        import sys
        sys.path.insert(0, sys_path)
        import orfs_hold_mm as ohm
        with tempfile.TemporaryDirectory() as t:
            util = Path(t) / "util.tcl"
            util.write_text("proc x {} {}\n" + ohm.FPL_ANCHOR + "}\n")
            self.assertEqual(ohm.patch_fp_lint(Path(t)), "patched")
            self.assertEqual(ohm.patch_hold_fresh(Path(t)), "patched")
            self.assertEqual(ohm.patch_hold_fresh(Path(t)), "already patched")
            txt = util.read_text()
            self.assertEqual(txt.count("ot_hold_fresh_run"), 2)
            # after the block's own hook (source_env_var_if_exists), inside source_step_tcl
            self.assertLess(txt.index("source_env_var_if_exists"), txt.index("ot_hold_fresh_run"))
            util.write_text("no anchor\n")
            self.assertIn("anchor not found", ohm.patch_hold_fresh(Path(t)))


def tcl_procs(*names):
    src = TCL.read_text()
    out = []
    for name in names:
        i = src.index(f"proc {name} ")
        j = src.find("\nproc ", i + 1)
        out.append(src[i:j if j > 0 else len(src)])
    return "\n".join(out)


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class TclSide(unittest.TestCase):
    STUBS = r"""
set ::calls {}
proc log_cmd {args} { lappend ::calls [join $args " "] }
proc ot_hm_guard {a} { return $a }
proc ot_hold_window_report {why hist} { set ::ot_hold_stalled 1; puts "STALL $why" }
"""

    def run_tcl(self, body):
        return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout

    def procs(self):
        return tcl_procs("ot_env_num", "ot_hold_guard_on", "ot_hold_stage", "ot_hold_stop_cap", "ot_hold_stop_args",
                         "ot_hold_stop", "ot_repair_timing", "ot_hold_repair", "ot_hold_fresh_on", "ot_hold_fresh_args_file",
                         "ot_hold_fresh_defer", "ot_json_num", "ot_hold_fresh_run")

    def test_cts_defers_and_fresh_session_repairs_with_saved_args(self):
        with tempfile.TemporaryDirectory() as t:
            res = Path(t)
            body = self.STUBS + self.procs() + f"""
set ::env(RESULTS_DIR) {res}
set ::env(OT_HOLD_FRESH) cts
set ::env(OT_HOLD_STOP) "cts:0 grt:0"
set ::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) 1
set ::env(DONT_USE_CELLS) "*x1p*"
set ::stats {{{{-50.44 -9000.0 812}} {{-50.44 -9000.0 812}} {{-50.44 -9000.0 812}} {{31.4 0.0 0}}}}
proc ot_hold_stats {{}} {{ set s [lindex $::stats 0]; if {{[llength $::stats] > 1}} {{ set ::stats [lrange $::stats 1 end] }}; return $s }}
# 4_1_cts session: setup repair only, hold deferred with its exact args
ot_repair_timing {{-setup_margin 0 -hold_margin 30 -match_cell_footprint -verbose}}
puts "CTS_CALLS [llength $::calls] [lindex $::calls 0]"
set ::calls {{}}
# 5_1_grt session (4_1_cts.odb exists -> stage grt), PRE GLOBAL_ROUTE
close [open {res}/4_1_cts.odb w]
namespace eval ord {{ proc get_db_block {{}} {{ return ::blk }} }}
set ::ninst 1000
proc ::blk {{m}} {{ incr ::ninst 8067; return [lrepeat [expr {{$::ninst}}] i] }}
proc set_dont_use {{a}} {{ lappend ::calls "set_dont_use $a" }}
proc set_propagated_clock {{a}} {{}}
proc all_clocks {{}} {{ return clk }}
proc set_placement_padding {{args}} {{ lappend ::calls "pad $args" }}
proc check_placement {{args}} {{ lappend ::calls "check_placement" }}
ot_hold_fresh_run
foreach c $::calls {{ puts "CALL $c" }}
puts "STAGE [ot_hold_stage]"
"""
            out = self.run_tcl(body)
            self.assertIn("CTS_CALLS 1 repair_timing -setup_margin 0 -hold_margin 30 -match_cell_footprint -verbose -setup", out)
            self.assertIn("OT_HOLD_FRESH stage=cts: hold repair deferred", out)
            self.assertEqual((res / "ot_hold_fresh_cts.args").read_text().strip(),
                             "-setup_margin 0 -hold_margin 30 -match_cell_footprint -verbose")
            calls = [ln[5:] for ln in out.splitlines() if ln.startswith("CALL ")]
            hold = [c for c in calls if c.startswith("repair_timing")]
            # the SAVED args (MATCH_CELL_FOOTPRINT is erased in the grt stage env), hold only, NOT capped by OT_HOLD_STOP
            self.assertTrue(hold and all("-match_cell_footprint" in c and "-hold" in c and "-setup " not in c + " "
                                         and "max_buffer_percent" not in c for c in hold), hold)
            self.assertIn("set_dont_use *x1p*", calls)
            self.assertIn("detailed_placement", calls)
            self.assertLess(calls.index(hold[-1]), calls.index("detailed_placement"))
            self.assertIn("STAGE grt", out)                  # override removed after the fresh session
            rec = json.loads((res / "4_1_cts.hold_fresh.json").read_text())
            self.assertEqual((rec["hold_ws_before_ps"], rec["hold_ws_after_ps"], rec["viol_after"], rec["stalled"]),
                             (-50.44, 31.4, 0, False))
            self.assertIn("OT_HOLD_FRESH done: hold ws -50.44 -> 31.40", out)

    def test_inert_without_env(self):
        with tempfile.TemporaryDirectory() as t:
            body = self.STUBS + self.procs() + f"""
set ::env(RESULTS_DIR) {t}
set ::stats {{{{-5.0 -10.0 2}} {{12.0 0.0 0}}}}
proc ot_hold_stats {{}} {{ set s [lindex $::stats 0]; if {{[llength $::stats] > 1}} {{ set ::stats [lrange $::stats 1 end] }}; return $s }}
ot_repair_timing {{-setup_margin 0 -hold_margin 10 -verbose}}
ot_hold_fresh_run
foreach c $::calls {{ puts "CALL $c" }}
"""
            out = self.run_tcl(body)
            calls = [ln[5:] for ln in out.splitlines() if ln.startswith("CALL ")]
            self.assertEqual(calls[0], "repair_timing -setup_margin 0 -hold_margin 10 -verbose -setup")
            self.assertTrue(any("-hold -max_iterations" in c for c in calls[1:]))
            self.assertNotIn("OT_HOLD_FRESH", out)
            self.assertFalse((Path(t) / "ot_hold_fresh_cts.args").exists())


if __name__ == "__main__":
    unittest.main()
