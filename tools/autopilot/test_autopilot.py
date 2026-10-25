#!/usr/bin/env python3
"""tests for tools/autopilot (no ssh, no ot-run, no systemd: the host / unit layer is faked)"""
import importlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

KIT = "epyc2:/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
ROW = ["s81", "slice_station__t5", KIT, "claude/s81-kits@0123456789ab", "PASS", "GEOM-REVIEW 03:33", "24", "120000",
       "S81"]


def so(verdict="NOT SIGNED", tt=5.0, ff=-3.0, fails=("hold_ff",), drc=0):
    return {"signoff": {"path": "/k/signoff/signoff.json", "verdict": verdict, "reasons": ["r"], "fails": list(fails),
                        "tt_wns": tt, "ff_wns": ff, "drc": drc, "odb": "/k/run/x/6_final.odb", "base": "/k/run/x"},
            "grt_overflow": 0}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AP_DIR"] = self.tmp.name
        os.environ["AP_QUEUE_FILE"] = str(Path(self.tmp.name) / "queue.tsv")
        os.environ["AP_COORD_FILES"] = str(Path(self.tmp.name) / "coord")
        (Path(self.tmp.name) / "coord" / "lanes").mkdir(parents=True)
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.DRY = False

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("AP_DIR", "AP_QUEUE_FILE", "AP_COORD_FILES"):
            os.environ.pop(k, None)

    def queue(self, *rows):
        Path(os.environ["AP_QUEUE_FILE"]).write_text("\n".join("\t".join(r) for r in rows) + "\n")


class TestQueue(Base):
    def test_valid_row(self):
        rows = self.ap.parse_queue("\t".join(ROW))
        (r,) = rows.values()
        self.assertEqual(r["error"], "")
        self.assertEqual((r["host"], r["mem_gb"], r["cells"], r["goal"], r["threads"]),
                         ("epyc2", 24, 120000, "auto", 8))

    def test_cell_cap_and_mem_and_paths(self):
        bad = {6: "500000", 5: "lots"}
        r = list(self.ap.parse_queue("\t".join(ROW[:7] + ["500000"] + ROW[8:])).values())[0]
        self.assertIn("400000", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:6] + ["lots"] + ROW[7:])).values())[0]
        self.assertIn("mem_gb", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:2] + ["epyc2:/home/ubuntu/kit"] + ROW[3:])).values())[0]
        self.assertIn("kit must be", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:2] + [KIT + "/../x"] + ROW[3:])).values())[0]
        self.assertIn("kit must be", r["error"])
        self.assertTrue(bad)

    def test_last_row_wins_and_comments(self):
        t = "# comment\n" + "\t".join(["die"] + ROW[1:]) + "\n" + "\t".join(ROW[:4] + ["PENDING", ""] + ROW[6:]) + \
            "\n" + "\t".join(ROW) + "\n"
        rows = self.ap.parse_queue(t)
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows.values())[0]["geom"], "PASS")


class TestClassify(Base):
    def test_signed(self):
        self.assertEqual(self.ap.classify(so("SIGNED", 1, 1, ()), {"exit": 0})[0], "SIGNED")

    def test_near_miss_hold(self):
        self.assertEqual(self.ap.classify(so(ff=-29.9), {"exit": 0})[0], "NEAR-MISS")

    def test_near_miss_bounds(self):
        self.assertEqual(self.ap.classify(so(ff=-30.0), {})[0], "NEAR-MISS")
        self.assertEqual(self.ap.classify(so(ff=-30.1), {})[0], "STRUCTURAL")
        self.assertEqual(self.ap.classify(so(tt=-12, ff=2, fails=("setup_tt",)), {})[0], "NEAR-MISS")
        self.assertEqual(self.ap.classify(so(tt=-40, ff=2, fails=("setup_tt",)), {})[0], "STRUCTURAL")
        self.assertEqual(self.ap.classify(so(ff=-3, drc=51), {})[0], "STRUCTURAL")
        c = so(ff=-3)
        c["grt_overflow"] = 12
        self.assertEqual(self.ap.classify(c, {})[0], "STRUCTURAL")

    def test_structural_checks_are_never_near_miss(self):
        for f in ("clock", "face_guard", "sdc_lint", "unconstrained"):
            self.assertEqual(self.ap.classify(so(ff=-1, fails=("hold_ff", f)), {})[0], "STRUCTURAL", f)

    def test_early_stops(self):
        self.assertEqual(self.ap.classify({"FAIL_PREFLOOR": "face_guard"}, {"exit": 1})[:2], ("STRUCTURAL", "preflight"))
        self.assertEqual(self.ap.classify({"FAIL_POSTCTS": "x"}, {"exit": 4})[0], "STRUCTURAL")
        self.assertEqual(self.ap.classify({"hold_structural": "OT_HOLD_STRUCTURAL stage=grt"}, {"exit": 2})[0],
                         "STRUCTURAL")
        self.assertEqual(self.ap.classify({"congestion": "GRT-0116"}, {"exit": 2})[1], "grt-overflow")
        self.assertEqual(self.ap.classify({"cells": 400001}, {"exit": 2})[1], "cell-cap")

    def test_crash_kinds(self):
        C = self.ap.classify
        self.assertEqual(C({"segfault": "Segmentation fault"}, {"exit": 139})[1], "tool-segfault")
        # a segfault that also shows 'Killed' text stays a tool crash, never infra
        self.assertEqual(C({"segfault": "Signal 11 received", "oom": "Killed"}, {"exit": 2})[1], "tool-segfault")
        self.assertEqual(C({"oom": "make: *** Error 137"}, {"exit": 2})[1], "infra-oom")
        self.assertEqual(C({}, {"not_run": True, "msg": "NOT RUN"})[1], "infra-notrun")
        self.assertEqual(C({}, {"not_completed": True})[1], "infra-lost")
        self.assertEqual(C({}, {"exit": 0})[1], "no-signoff")
        self.assertEqual(C({"orfs_error": "[ERROR CTS-0001] x"}, {"exit": 2})[1], "flow-error")
        self.assertNotIn("tool-segfault", self.ap.INFRA_KINDS)


class TestClientLog(Base):
    def test_ran(self):
        o = self.ap.parse_client_log("AP_START 1\n...\not-run: RAN on epyc3: exit 2\nAP_RC=2\n")
        self.assertEqual((o["ran_on"], o["exit"], o["ap_rc"]), ("epyc3", 2, 2))

    def test_ran_with_unit(self):
        o = self.ap.parse_client_log("ot-run: RAN on localhost (unit oth-ubuntu-657127-1792927330): exit 137\nAP_RC=137\n")
        self.assertEqual((o["ran_on"], o["exit"]), ("localhost", 137))

    def test_render_mem(self):
        self.assertEqual(self.ap.render_mem_gb(0), 8)
        self.assertEqual(self.ap.render_mem_gb(1873572309), 22)

    def test_not_run(self):
        o = self.ap.parse_client_log("ot-run: NOT RUN no host admitted 64 GB within --max-wait\nAP_RC=75\n")
        self.assertTrue(o["not_run"])


class FakeHosts:
    """stands in for ssh probes / systemd units: kit state per path"""
    def __init__(self, ap):
        self.ap, self.launched, self.active, self.calls, self.kits = ap, [], set(), [], {}

    def rpy(self, host, code, args, timeout=600):
        self.calls.append((host, code[:40], args))
        k = self.kits.get(args.get("kit"), {})
        if code is self.ap.PROBE_KIT:
            return {"exists": True, "config": True, "has_run": k.get("has_run", False), "signoff_dirs": [],
                    "routed": k.get("routed", []), "fail_marks": k.get("fail_marks", []), "busy": k.get("busy", False),
                    "log_age_s": k.get("log_age_s"), "runner": "/srv/opentallas-scratch2/claude/s81/kits/run_kit.sh"}
        if code is self.ap.PROBE_CLASSIFY:
            return dict(k.get("classify", {}), last_log_mtime=k.get("mtime", 0))
        if code is self.ap.PROBE_DELETE:
            return {"deleted": [args["kit"] + "/run/results"], "errors": []}
        if code is self.ap.PROBE_ARCHIVE:
            return {"files": 12, "errors": []}
        if code is self.ap.PROBE_MD5CHECK:
            return {"ok": True}
        return {"error": "unknown probe"}

    def launch(self, unit, logfile, argv):
        self.launched.append((unit, argv))
        self.active.add(unit)
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        Path(logfile).write_text("AP_START 0\n")
        return True


class TickBase(Base):
    def setUp(self):
        super().setUp()
        self.f = FakeHosts(self.ap)
        self.ap.rpy = self.f.rpy
        self.ap.launch_unit = self.f.launch
        self.ap.unit_active = lambda u: u in self.f.active
        self.ap.rbash = lambda host, script, timeout=0: (0, "", "")
        self.ap.sh = lambda cmd, timeout=0, input=None: (0, "", "")
        self.ap.hub_procs = lambda path: []

    def tick(self):
        self.ap.tick(type("A", (), {"dry_run": False})())
        return json.loads((Path(self.tmp.name) / "state.json").read_text())["jobs"]

    def finish_client(self, unit, text):
        self.f.active.discard(unit)
        st = json.loads((Path(self.tmp.name) / "state.json").read_text())
        j = [j for j in st["jobs"].values() if j.get("unit") == unit][0]
        Path(j["client_log"]).write_text(text)


class TestTick(TickBase):
    def test_submit_once_with_honest_mem_and_geom_gate(self):
        self.queue(ROW, ROW[:2] + [KIT + "x"] + ROW[3:4] + ["FAIL", "GR"] + ROW[6:])
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 1)
        argv = self.f.launched[0][1]
        self.assertEqual(argv[argv.index("--mem") + 1], "24")
        self.assertNotIn("--hosts", argv)
        self.assertIn("--stage", argv)
        self.assertEqual(argv[-4:], ["/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5", "route", "24", "8"])
        self.assertEqual(sorted(j["status"] for j in jobs.values()), ["RUNNING", "WAIT-GEOM"])
        self.tick()                                       # idempotent: still running, nothing new
        self.assertEqual(len(self.f.launched), 1)

    def test_refuses_routed_or_failed_kit(self):
        for k in ({"has_run": True, "routed": ["5_route.odb"]}, {"has_run": True, "fail_marks": ["FAIL_POSTCTS"]}):
            self.f.kits["/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"] = k
            (Path(self.tmp.name) / "state.json").unlink(missing_ok=True)
            self.queue(ROW)
            jobs = self.tick()
            self.assertEqual(list(jobs.values())[0]["status"], "REJECTED")
            self.assertEqual(self.f.launched, [])

    def test_placed_kit_continues_unless_busy(self):
        K5 = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[K5] = {"has_run": True, "log_age_s": 120}
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])                 # placement logs still moving: hold
        self.f.kits[K5] = {"has_run": True, "log_age_s": 3600, "busy": True}
        self.tick()
        self.assertEqual(self.f.launched, [])                 # a container still mounts it: hold
        self.f.kits[K5] = {"has_run": True, "log_age_s": 3600}
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 1)
        self.assertEqual(list(jobs.values())[0]["status"], "RUNNING")

    def test_signed_archived_once(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": so("SIGNED", 3.0, 2.0, ()), "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        jobs = self.tick()
        self.assertEqual(list(jobs.values())[0]["status"], "ARCHIVED")
        self.tick()
        rows = (Path(self.tmp.name) / "signed.tsv").read_text().splitlines()
        self.assertEqual(len(rows), 2)                   # header + one row
        self.assertNotIn(path, [c[2]["kit"] for c in self.f.calls if c[1] == self.ap.PROBE_DELETE[:40]])

    def test_near_miss_goes_to_review_no_eco_and_deletes(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": so(ff=-4.2), "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        jobs = self.tick()
        j = list(jobs.values())[0]
        self.assertEqual(j["status"], "REVIEW-NEAR-MISS")
        unit, argv = self.f.launched[-1]
        self.assertTrue(unit.endswith("-review"))
        self.assertIn("render_review.sh", " ".join(argv))
        self.assertEqual(argv[argv.index("--mem") + 1], "8")
        self.finish_client  # review unit ends:
        self.f.active.discard(unit)
        Path(j["review_log"]).write_text("AP_REVIEW_PNG /r/paths.png\nAP_REVIEW_PATHS /r/paths_ff_hold.txt\nAP_RC=0\n")
        jobs = self.tick()
        j = list(jobs.values())[0]
        self.assertEqual(j["status"], "DONE-NEAR-MISS")
        rv = (Path(self.tmp.name) / "review.tsv").read_text()
        self.assertIn("/r/paths.png", rv)
        self.assertIn("/r/paths_ff_hold.txt", rv)
        self.assertEqual(len(self.f.launched), 2)        # the run + the render, never an ECO / re-route
        self.assertTrue(any(c[1] == self.ap.PROBE_DELETE[:40] for c in self.f.calls))

    def test_infra_oom_resubmits_once_with_more_mem_then_marks(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": {"oom": "make: *** [x] Error 137"}, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 2\nAP_RC=2\n")
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 2)
        argv = self.f.launched[1][1]
        self.assertEqual(argv[argv.index("--mem") + 1], "36")
        self.finish_client(self.f.launched[1][0], "ot-run: RAN on epyc2: exit 2\nAP_RC=2\n")
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 2)        # once only
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-CRASH")
        self.assertIn("CRASH/infra-oom", (Path(self.tmp.name) / "structural.tsv").read_text())

    def test_segfault_is_marked_not_resubmitted(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": {"segfault": "Signal 11 received"}, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 139\nAP_RC=139\n")
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 1)
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-CRASH")

    def test_structural_preflight(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": {"FAIL_PREFLOOR": "FAIL_PREFLOOR face_guard"}, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 1\nAP_RC=1\n")
        jobs = self.tick()
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-STRUCTURAL")
        self.assertIn("preflight", (Path(self.tmp.name) / "structural.tsv").read_text())

    def test_dry_run_writes_nothing(self):
        self.queue(ROW)
        self.ap.tick(type("A", (), {"dry_run": True})())
        self.assertEqual(self.f.launched, [])
        self.assertFalse((Path(self.tmp.name) / "state.json").exists())
        self.assertFalse((Path(self.tmp.name) / "log.txt").exists())


def ts(ago_min):
    return time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(time.time() - ago_min * 60))


class TestAdopt(TickBase):
    K5 = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"

    def test_adopt_watches_then_records_without_submitting(self):
        live = {"on": True}
        self.ap.hub_procs = lambda path: [(4242, 300)] if live["on"] else []
        self.f.kits[self.K5] = {"has_run": True, "busy": True, "log_age_s": 30}
        self.queue(ROW[:4] + ["REQ", "PROTO-KITS"] + ROW[6:] + ["", "", "", "adopt"])
        jobs = self.tick()
        j = list(jobs.values())[0]
        self.assertEqual(j["status"], "RUNNING")
        self.assertTrue(j["adopted"])
        self.assertGreater(j["started"], 0)
        self.assertEqual(self.f.launched, [])
        self.tick()
        self.assertEqual(self.f.launched, [])
        live["on"] = False
        self.f.kits[self.K5] = {"has_run": True, "busy": False, "log_age_s": 3600,
                                "classify": {"FAIL_POSTCTS": "FAIL_POSTCTS FF structural hold gate"}}
        jobs = self.tick()
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-STRUCTURAL")
        self.assertEqual(self.f.launched, [])
        self.assertIn("post-cts-hold", (Path(self.tmp.name) / "structural.tsv").read_text())

    def test_adopted_infra_crash_is_not_resubmitted(self):
        self.ap.hub_procs = lambda path: []
        self.f.kits[self.K5] = {"has_run": True, "busy": False, "log_age_s": 3600, "classify": {"oom": "Killed"}}
        self.queue(ROW + ["", "", "", "adopt"])
        self.tick()
        jobs = self.tick()
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-CRASH")
        self.assertEqual(self.f.launched, [])


class TestGeomAutoSubmit(TickBase):
    def geom(self, text):
        (Path(self.tmp.name) / "coord" / "lanes" / "GEOM-REVIEW.md").write_text(text)

    def test_pass_reply_submits_in_the_same_tick(self):
        self.queue(ROW[:4] + ["REQ", "PROTO-KITS"] + ROW[6:])
        jobs = self.tick()
        self.assertEqual(list(jobs.values())[0]["status"], "WAIT-GEOM")
        self.geom(f"{ts(40)} PROTO-KITS: GEOM REQ [PROTO-KITS] kits slice_station__t5, slice_station__t6\n"
                  f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS {ts(40)[11:16]}] t5: PASS, route it; t6: FAIL (pins)\n")
        jobs = self.tick()
        j = list(jobs.values())[0]
        self.assertEqual(j["status"], "RUNNING")
        self.assertEqual(j["geom"], "PASS")
        self.assertEqual(len(self.f.launched), 1)

    def test_fail_clause_old_verdict_and_ambiguous_never_submit(self):
        t6 = ROW[:1] + ["slice_station__t6", KIT.replace("t5", "t6")] + ROW[3:4] + ["REQ", "PROTO-KITS"] + ROW[6:]
        t5 = ROW[:4] + ["REQ", "PROTO-KITS"] + ROW[6:]
        self.queue(t5, t6)
        self.geom(f"{ts(300)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS (older kit)\n"
                  f"{ts(40)} GEOM REQ [PROTO-KITS] slice_station__t5 slice_station__t6 regenerated\n"
                  f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] t5 and t6 reviewed: PASS for one, FAIL for the other\n"
                  f"{ts(4)} GEOM-REVIEW: REPLY [PROTO-KITS] t6: FAIL (far pin regs)\n")
        jobs = self.tick()
        self.assertEqual(self.f.launched, [])
        self.assertEqual(sorted(j["status"] for j in jobs.values()), ["WAIT-GEOM", "WAIT-GEOM"])
        gaps = (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text()
        self.assertIn("no gaps", gaps)                   # REQ answered within 20 min window

    def test_loop_gaps_file(self):
        self.geom(f"{ts(90)} S81: GEOM REQ [S81/H4 {ts(90)[11:16]}] hd_turn kits\n"
                  f"{ts(50)} GEOM REQ [QC-CQB] cqb\n{ts(45)} COORD GEOM VERDICT [QC-CQB 04:18]: PASS -- route it\n"
                  f"{ts(10)} GEOM REQ [NEW] too young\n"
                  f"{ts(60)} GEOM REQ [QC-VMR] qfd_dv_s8x_vmr routed review\n"
                  f"{ts(59)} COORD GEOM VERDICT [QC qfd_dv_s8x_vmr_cqb, 2 kits]: PASS (no route needed)\n")
        (Path(self.tmp.name) / "coord" / "lanes" / "COORD-REVIEW-QUEUE.md").write_text(
            f"READY [S81 {ts(120)}] claude/a-1025@aaaaaaaaaa: x\n[COORD {ts(100)}] APPROVED claude/a-1025@aaaaaaaaaa\n"
            f"READY [QC {ts(60)}] claude/b-1025@bbbbbbbbbb: y\n")
        self.ap.sh = lambda cmd, timeout=0, input=None: (
            (0, "epyc2 admits 18 GB (avail 499) load 64/128 waiters 0 | epyc4 admits 300 GB (avail 400) load 10/128 "
                "| next 16-thread 32 GB job -> epyc4", "") if cmd[-1] == "--status" else (0, "", ""))
        self.tick()
        g = (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text().splitlines()
        body = g[1:]
        self.assertRegex(body[0].strip(), r"^9[01] m ", body)
        self.assertIn("GEOM-REQ-UNANSWERED [S81/H4]", body[0])
        self.assertTrue(any("GEOM-PASS-NOT-ROUTED [QC-CQB]" in l for l in body))
        self.assertTrue(any("READY-NO-COORD claude/b-1025" in l for l in body))
        self.assertFalse(any("claude/a-1025" in l for l in body))
        self.assertTrue(any("HOST-IDLE epyc4" in l for l in body))
        self.assertFalse(any("epyc2" in l or "[NEW]" in l or "QC-VMR" in l for l in body))

    def test_review_row_without_lane_action(self):
        p = Path(self.tmp.name)
        old = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time() - 7200))
        (p / "review.tsv").write_text(self.ap.TSV_HEAD["review.tsv"] + "\n" + "\t".join(
            [old, "abc123", "s81", "slice_station__t5", "x@1234567", "epyc2", KIT, "NEAR-MISS", "r", "", "", "", "S81"]) +
            "\n" + "\t".join([old, "def456", "s81", "slice_station__t9", "x@1234567", "epyc2", KIT, "NEAR-MISS", "r",
                               "", "", "", "S81"]) + "\n")
        (p / "coord" / "lanes" / "S81.md").write_text(f"{ts(30)} S81: fix for slice_station__t9: re-plan pins\n")
        self.tick()
        g = (p / "LOOP-GAPS.txt").read_text()
        self.assertIn("REVIEW-NO-ACTION review.tsv abc123", g)
        self.assertNotIn("def456", g)


class TestRender(unittest.TestCase):
    LOG = """Startpoint: a/q_reg (rising edge-triggered flip-flop clocked by clk)
Endpoint: b/q_reg (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: min

  Delay    Time   Description
---------------------------------------------------------
   0.00    0.00   clock clk (rise edge)
   0.00    0.00 ^ ck (in)
  14.45   14.45 ^ ck_buf/Y (BUFx4_ASAP7_75t_R)
   0.66  179.81 ^ a/q_reg/CLK (DFFHQNx1_ASAP7_75t_R)
  32.93  212.75 v a/q_reg/QN (DFFHQNx1_ASAP7_75t_R)
  14.26  227.01 v hold1/Y (BUFx2_ASAP7_75t_R)
   4.68  231.69 ^ b/q_reg/D (DFFHQNx1_ASAP7_75t_R)
         231.69   data arrival time
---------------------------------------------------------
          -3.64   slack (VIOLATED)


Startpoint: x[3] (input port clocked by vclk)
Endpoint: c/q_reg (rising edge-triggered flip-flop clocked by clk)
Path Group: vclk
Path Type: min

  Delay    Time   Description
   0.00    0.00   clock vclk (rise edge)
 -40.00  -40.00 v input external delay
   0.00  -40.00 v x[3] (in)
   5.00  -35.00 v c/q_reg/D (DFFHQNx1_ASAP7_75t_R)
         -35.00   data arrival time
          -1.00   slack (VIOLATED)


Startpoint: d (input port clocked by vclk)
Endpoint: e
Path Type: min
           5.00   slack (MET)
"""

    def test_blocks_and_points(self):
        import render_review as R
        blks = R.violated_blocks(self.LOG, "min")
        self.assertEqual(len(blks), 2)
        self.assertEqual(R.violated_blocks(self.LOG, "max"), [])
        self.assertEqual(R.path_points(blks[0]), [("a/q_reg", False), ("hold1", False), ("b/q_reg", False)])
        self.assertEqual(R.path_points(blks[1]), [("x[3]", True), ("c/q_reg", False)])

    def test_points_with_fields(self):
        import render_review as R
        blk = """Startpoint: ft0_i[276] (input port clocked by vclk)
Endpoint: u/eq_reg
Path Type: max
     1    1.92   11.50    2.65 1019.01 ^ ft0_i[276] (in)
                        766.36 1016.36 ^ input external delay
     1    1.92   11.50    2.65 1019.01 ^ ft0_i[276] (in)
     1    0.58    5.37   14.99 1034.00 ^ input213/Y (BUFx6f_ASAP7_75t_R)
                  5.37    0.04 1034.04 ^ u/eq_reg/D (DFFASRHQNx1_ASAP7_75t_R)
                               1034.04   data arrival time
                                -20.90   slack (VIOLATED)"""
        self.assertEqual(R.path_points(R.violated_blocks(blk, "max")[0]),
                         [("ft0_i[276]", True), ("input213", False), ("u/eq_reg", False)])

    def test_draw(self):
        import render_review as R
        layout = {"die": [0, 0, 100, 50], "std_cells": [["a/q_reg", "DFF", "PLACED", 1, 1, 2, 2],
                                                         ["hold1", "BUF", "PLACED", 50, 20, 51, 21],
                                                         ["b/q_reg", "DFF", "PLACED", 90, 40, 91, 41]],
                  "pins": [["x\\[3\\]", "M4", 0, 10, 0.1, 10.1]], "blocks": []}
        with tempfile.TemporaryDirectory() as d:
            p = R.draw_paths(layout, [((0, 0, 255), R.violated_blocks(self.LOG, "min"))], Path(d) / "p.png", "t")
            self.assertTrue(Path(p).read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
