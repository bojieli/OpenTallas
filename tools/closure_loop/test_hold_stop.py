"""HOLD-STOP (drive-resume 2026-10-09, coordinator APPROVED): a CTS/GRT hold repair that stalls already within
hold_nearmiss_ps (-15 ps) with the setup gate clear is not early-failed; the route resumes from its checkpoint with the
hold repair cut (OT_HOLD_STOP) and the post-route hold ECO fixes the residue."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl
import stuckscan as ss
from test_stuckscan import ProbeAndGates, job, make_run

HERE = Path(__file__).resolve().parent


def rows(n0, pts):
    """rows at 100-it steps through (iteration offset, buffers, ws) points"""
    return "\n".join(f"{n0 + 100 * k:9d} |       0 | {b:7d} |            0 |    +0.5% | {w:7.3f} | -50.213 | u.x[{k}]$_DFF_P_/D"
                     for k, (b, w) in enumerate(pts))


def tile_like(final_ws):
    # converges -32.6 -> final_ws by buffer 7,909, then flat for 40 rows (4,000 iterations)
    conv = [(int(7909 * k / 39), -32.584 + (final_ws + 32.584) * k / 39) for k in range(40)]
    flat = [(7909 + 50 * k, final_ws) for k in range(1, 41)]
    return "[INFO RSZ-0046] Found 37041 endpoints with hold violations.\n" + rows(0, conv + flat)


class Gate(ProbeAndGates):
    def test_nearmiss_stall_is_hold_stop(self):
        d = self.hold_diag("OT_HOLD_GUARD start: x\n" + tile_like(-3.569))
        self.assertEqual((d["action"], d["kind"]), ("hold_stop", "hold_nearmiss"))
        self.assertEqual(d["hold_stop"]["stage"], "cts")
        self.assertEqual(d["hold_stop"]["buffers"], int(7909 * 1.02) + 10)
        self.assertIn("near-miss", d["why"][0])

    def test_deep_stall_still_early_fails(self):
        d = self.hold_diag("OT_HOLD_GUARD start: x\n" + tile_like(-20.0))
        self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")

    def test_setup_gate_blocks_hold_stop(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=-600, count=9000, tmp="4_1_cts.tmp.log",
                           tmp_text="OT_HOLD_GUARD start: x\n" + tile_like(-3.0), ages=self.HOLD_AGES)
            d = self.diag(run)
        self.assertEqual(d["action"], "early_fail")
        self.assertEqual(d["verdict"], "EARLY_FAIL_SETUP")

    def test_stage_stopped_once_only(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=0, count=0, tns=0, tmp="4_1_cts.tmp.log",
                           tmp_text="OT_HOLD_GUARD start: x\n" + tile_like(-3.0), ages=self.HOLD_AGES)
            o = self.probe(run)
            b = o["bases"][0]
            hp = ss.hopeless(b, job(run=str(run), hold_stop_log=[dict(stage="cts")]), 1e12)
        self.assertEqual(hp[0][0], "EARLY_FAIL_HOLD")


class LoopSide(unittest.TestCase):
    def test_daemon_gate_resumes_instead_of_early_fail(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=0, count=0, tns=0, tmp="4_1_cts.tmp.log",
                           tmp_text="OT_HOLD_GUARD start: x\n" + tile_like(-3.6), ages=ProbeAndGates.HOLD_AGES)
            j = job(run=str(run))
            with patch.object(cl, "STATE", Path(t)), patch.object(cl, "hold_stop_resume") as h, \
                    patch.object(cl, "early_fail_finish") as ef:
                cl.early_fail_gate(j, dict(key="route", kind="route"))
            h.assert_called_once()
            self.assertEqual(h.call_args[0][1:3], ("cts", int(7909 * 1.02) + 10))
            ef.assert_not_called()

    def test_docker_shim_passes_hold_stop(self):
        self.assertEqual(cl.DOCKER_SHIM.count("-e OT_HOLD_STOP"), 2)

    def test_tcl_cap_parsing(self):
        tcl = (HERE.parent / "orfs_hold_mm.tcl").read_text()
        start = tcl.index("proc ot_hold_stop_cap")
        end = tcl.index("proc ot_hold_stop {")
        script = tcl[start:end] + """
set ::env(OT_HOLD_STOP) "cts:8077 grt:0"
puts [ot_hold_stop_cap cts],[ot_hold_stop_cap grt]
unset ::env(OT_HOLD_STOP)
puts "x[ot_hold_stop_cap cts]x"
puts [ot_hold_stop_args {-hold_margin 10 -max_buffer_percent 100 -verbose} 0.5]
puts [ot_hold_stop_args {-hold_margin 10} 0.5]
"""
        r = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
        self.assertEqual(r.stdout.split("\n")[:4], ["8077,0", "xx", "-hold_margin 10 -max_buffer_percent 0.5 -verbose",
                                                    "-hold_margin 10 -max_buffer_percent 0.5"])


if __name__ == "__main__":
    unittest.main()
