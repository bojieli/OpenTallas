"""STUCKSCAN (2026-10-08): the remote probe on a synthetic ORFS run dir (run locally), the early-fail gates, the
redundancy / stall / never-started diagnoses, and the daemon's early-fail gate + STARTING timeout."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl
import stuckscan as ss

CTS_RPT = """==========================================================================
cts final report_checks -path_delay max
--------------------------------------------------------------------------
Startpoint: u.a_q[3]$_DFF_P_
            (rising edge-triggered flip-flop clocked by ck)
Endpoint: u.b_q[7]$_DFF_P_ (rising edge-triggered flip-flop clocked by ck)
Path Group: ck
Path Type: max

Fanout     Cap    Slew   Delay    Time   Description
-----------------------------------------------------------------------------
                          0.00    0.00   clock ck (rise edge)
     1   22.12    0.00    0.00    0.00 ^ ck (in)
                                         ck (net)
                 78.96   24.91   24.91 ^ clkbuf_0_ck/A (BUFx24_ASAP7_75t_R)
     2    9.95   14.40   41.46   66.37 ^ clkbuf_0_ck/Y (BUFx24_ASAP7_75t_R)
                                         clknet_0_ck (net)
                 14.28    0.64   67.01 ^ u.a_q[3]$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
     2    2.31   34.65   66.72  133.73 v u.a_q[3]$_DFF_P_/QN (DFFHQNx1_ASAP7_75t_R)
                                         n1 (net)
                 34.65  300.00  433.73 v u1/A (BUFx2_ASAP7_75t_R)
   312    1.08    9.13   27.76  461.49 v u1/Y (BUFx2_ASAP7_75t_R)
                                         n2 (net)
                  9.13  500.00  961.49 v u.b_q[7]$_DFF_P_/D (DFFHQNx1_ASAP7_75t_R)
                               961.49   data arrival time

                        770.00  770.00   clock ck (rise edge)
                               -500.00   slack (VIOLATED)

Startpoint: rd_out[2] (input port clocked by ck)
Endpoint: o_q[1] (output port clocked by ck)
Path Group: path delay
Path Type: max

Fanout     Cap    Slew   Delay    Time   Description
-----------------------------------------------------------------------------
                        400.00  400.00 ^ input external delay
     1   22.12    0.00    0.00  400.00 ^ rd_out[2] (in)
                                         rd_out[2] (net)
                 20.00   10.00  410.00 ^ u2/A (AND2x2_ASAP7_75t_R)
     1    3.00   20.00   90.00  500.00 ^ u2/Y (AND2x2_ASAP7_75t_R)
                                         o_q[1] (net)
                 20.00    5.00  505.00 ^ o_q[1] (out)
                               505.00   data arrival time
                                 12.00   slack (MET)

==========================================================================
cts final report_check_types
"""


def hold_rows(n0, ws_start, ws_end, rows=40):
    out = []
    for k in range(rows):
        it = n0 + 100 * k
        ws = ws_start + (ws_end - ws_start) * k / (rows - 1)
        out.append(f"{it:9d} |       0 | {1000 + k:7d} |            0 |    +6.1% | {ws:7.3f} |   0.000 | u.x[{k}]$_DFF_P_/D")
    return "\n".join(out)


def make_run(root, *, corner="TT", cts_ws=-500.0, count=5000, tns=-2e6, period=770, tmp="5_1_grt.tmp.log",
             tmp_text="", congestion=None, ages=None):
    run = Path(root) / "job"
    d = "design_x"
    orfs = run / "routes/job_x/work/orfs"
    base = orfs / f"logs/asap7/{d}/base"
    rep = orfs / f"reports/asap7/{d}/base"
    res = orfs / f"results/asap7/{d}/base"
    for p in (base, rep, res, run / "cl"):
        p.mkdir(parents=True, exist_ok=True)
    (base / "1_2_yosys.log").write_text(f"read asap7sc7p5t_AO_RVT_{corner}_nldm_211120.lib.gz\n")
    (base / "3_5_place_dp.log").write_text("dp\n")
    (base / "4_1_cts.log").write_text("cts\n")
    (base / "4_1_cts.json").write_text(json.dumps({"cts__timing__setup__ws": cts_ws, "cts__timing__setup__tns": tns,
                                                   "cts__timing__drv__setup_violation_count": count}))
    (base / tmp).write_text(tmp_text)
    (rep / "4_cts_final.rpt").write_text(CTS_RPT)
    (res / "clock_period.txt").write_text(str(period))
    (res / "2_floorplan.odb").write_bytes(b"x" * 1000)
    for it, n in (congestion or []):
        (rep / f"congestion-{it}.rpt").write_text("violation type: Horizontal congestion\n" * n)
    now = time.time()
    for name, age in (ages or {"1_2_yosys.log": 7 * 3600, "3_5_place_dp.log": 6 * 3600, "4_1_cts.log": 5 * 3600}).items():
        os.utime(base / name, (now - age, now - age))
    (run / "cl/route.a1.log").write_text("x")
    return run


def job(name="blk-0123456789-tt", **kw):
    j = dict(name=name, status="RUNNING", stage_key="route", stage_tag="route.a1", host="localhost", run="",
             commit_full="0123456789abcdef", created="2026-10-08T10:00:00-07:00", spec=dict(block="blk", owner="t",
             source=dict(commit="0123456789abcdef")), stage_started="2026-10-08T10:00:00-07:00")
    j.update(kw)
    return j


class ProbeAndGates(unittest.TestCase):
    def probe(self, run):
        res, err = ss.probe("localhost", [dict(name="job", run=str(run), tag="route.a1", live=True)], cpu=False)
        self.assertIsNone(err)
        return res["jobs"]["job"]

    def diag(self, run, j=None, jobs=None):
        o = self.probe(run)
        j = j or job(run=str(run))
        return ss.diagnose(j, o, {}, jobs or [j], set(), time.time())

    def test_setup_gate_and_path_classes(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=-500.0, count=5000)
            d = self.diag(run)
            self.assertEqual((d["action"], d["verdict"]), ("early_fail", "EARLY_FAIL_SETUP"))
            self.assertAlmostEqual(d["setup"]["ws"], -500.0 + 63.3, places=1)
            p = d["paths"][0]
            self.assertEqual(p["cls"], "reg->reg")
            self.assertEqual(p["dominated"], "wire")          # 300 + 500 ps of wire vs 66.7 + 27.8 ps of cells
            self.assertEqual(p["max_fanout"], 312)
            self.assertEqual(d["paths"][1]["cls"], "input->out")

    def test_setup_gate_spares_calibrated_closures(self):
        # qfd_io_emb_root closed from post-CTS -329 / 656 endpoints; hbm_router_k2 from -358 / 4
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.diag(make_run(t, cts_ws=-329.3 - 63.3, count=656, tns=-143823))["action"], "let_run")
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.diag(make_run(t, cts_ws=-358.1 - 63.3, count=4, tns=-1202))["action"], "let_run")

    def test_setup_gate_needs_tt_and_skips_finished_route(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.diag(make_run(t, corner="SS", cts_ws=-900))["action"], "let_run")
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.diag(make_run(t, cts_ws=-900, tmp="6_report.tmp.log"))["action"], "let_run")

    def test_half_rate_period_is_not_shifted(self):
        self.assertEqual(ss.norm_ws(-282.8, 1111.1), -282.8)
        self.assertAlmostEqual(ss.norm_ws(-100, 770), -36.667, places=2)

    def test_hold_flood(self):
        txt = "OT_HOLD_MM sync: SS setup ws -10.00 / FF hold ws -40.00 ps\n[INFO RSZ-0046] Found 80635 endpoints with " \
              "hold violations.\n" + hold_rows(100, -40, -38)
        with tempfile.TemporaryDirectory() as t:
            d = self.diag(make_run(t, cts_ws=0, count=0, tns=0, tmp="4_1_cts.tmp.log", tmp_text=txt,
                                   ages={"1_2_yosys.log": 9000, "3_5_place_dp.log": 8000}))
            self.assertEqual(d["verdict"], "EARLY_FAIL_HOLD")
            self.assertIn("old flow", d["why"][0])

    def test_margin_chase_stall_kill_and_guarded_run_kept(self):
        txt = "[INFO RSZ-0046] Found 13110 endpoints with hold violations.\n" + hold_rows(8000, 38.2, 38.5)
        with tempfile.TemporaryDirectory() as t:
            d = self.diag(make_run(t, cts_ws=-20, count=10, tns=-100, tmp_text=txt))
            self.assertEqual((d["action"], d["kind"]), ("kill_stage", "stalled"))
        with tempfile.TemporaryDirectory() as t:
            d = self.diag(make_run(t, cts_ws=-20, count=10, tns=-100, tmp_text="OT_HOLD_GUARD start: x\n" + txt))
            self.assertEqual(d["action"], "let_run")

    def test_congestion_and_drc(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.diag(make_run(t, cts_ws=0, count=0, tns=0, tmp_text="[INFO GRT-0102] Start extra iteration 26/30\n",
                                   congestion=[(10, 3000), (15, 2500), (20, 2600), (25, 2550)]))
            self.assertEqual(d["verdict"], "EARLY_FAIL_CONGESTION")
        with tempfile.TemporaryDirectory() as t:     # still finding new bests: keep
            d = self.diag(make_run(t, cts_ws=0, count=0, tns=0, tmp_text="[INFO GRT-0102] Start extra iteration 26/30\n",
                                   congestion=[(10, 3000), (15, 2500), (20, 1600), (25, 2550)]))
            self.assertEqual(d["action"], "let_run")
        drt = "".join(f"[INFO DRT-0195] Start {i}th optimization iteration.\n[INFO DRT-0199]   Number of violations = "
                      f"{v}.\n" for i, v in [(18, 900), (19, 700), (20, 450)] + [(i, 470 + i % 3) for i in range(21, 30)])
        with tempfile.TemporaryDirectory() as t:
            d = self.diag(make_run(t, cts_ws=0, count=0, tns=0, tmp="5_2_route.tmp.log", tmp_text=drt))
            self.assertEqual(d["verdict"], "EARLY_FAIL_DRC")

    def test_redundant_newer_commit_same_variant(self):
        old = job("qfd_hub-172d343d8-tt", commit_full="172d343d8aaaa", created="2026-10-07T22:00:00-07:00")
        new = job("qfd_hub-3d5ad2a4ftt", commit_full="3d5ad2a4fbbbb", created="2026-10-08T03:00:00-07:00")
        with patch.object(ss, "is_ancestor", return_value=True):
            why, sure = ss.redundant(old, [old, new], set())
        self.assertTrue(sure)
        self.assertIn("qfd_hub-3d5ad2a4ftt", why)

    def test_closed_on_older_commit_only_flags(self):
        j = job()
        c = job("blk-aaaaaaaaa", status="CLOSED", commit_full="aaaaaaaaa000")
        with patch.object(cl, "revoked_closures", return_value=(set(), set())), \
                patch.object(ss, "is_ancestor", return_value=False):
            why, sure = ss.redundant(j, [j, c], {"blk"})
        self.assertFalse(sure)


class DaemonGate(unittest.TestCase):
    def test_gate_finishes_early_fail(self):
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, cts_ws=-600, count=9000)
            j = job(run=str(run))
            st = dict(key="route", kind="route")
            with patch.object(cl, "STATE", Path(t)), patch.object(cl, "kill_own_stage") as k, \
                    patch.object(cl, "ledger"), patch.object(cl, "experiment"), \
                    patch.object(ss, "FAILTRIG", Path(t) / "failtrig"):
                cl.early_fail_gate(j, st)
            self.assertEqual(j["status"], "EARLY_FAIL_SETUP")
            k.assert_called_once()
            self.assertTrue((Path(t) / "early_fail" / f"{j['name']}.json").exists())
            self.assertTrue((Path(t) / "failtrig/stuck" / f"{j['name']}.json").exists())
            self.assertTrue((run / "cl/early_fail.json").exists())

    def test_gate_opt_out_and_interval(self):
        j = job(spec=dict(block="b", early_fail=False, source=dict(commit="x")))
        with patch.object(ss, "probe") as p:
            cl.early_fail_gate(j, dict(kind="route"))
            p.assert_not_called()

    def test_starting_timeout_is_lost(self):
        j = job(stage_started="2026-10-08T00:00:00-07:00", stage_idx=0, status="RUNNING")
        st = dict(key="route", kind="route")
        with patch.object(cl, "stage_list", return_value=[st]), patch.object(cl, "poll_stage", return_value=("STARTING", None)), \
                patch.object(cl, "bench_track", return_value=True), patch.object(cl, "cal_track"), \
                patch.object(cl, "crash") as c:
            cl.step(j, None)
        c.assert_called_once()
        self.assertTrue(c.call_args[0][3].startswith("LOST: stage route.a1 never started"))


if __name__ == "__main__":
    unittest.main()
