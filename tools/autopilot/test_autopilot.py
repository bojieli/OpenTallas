#!/usr/bin/env python3
"""tests for tools/autopilot (no ssh, no ot-run, no systemd: the host / unit layer is faked)"""
import importlib
import json
import os
import re
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
        os.environ["AP_RELEASE_CACHE"] = str(Path(self.tmp.name) / "release_cache.json")
        (Path(self.tmp.name) / "coord" / "lanes").mkdir(parents=True)
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.DRY = False

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("AP_DIR", "AP_QUEUE_FILE", "AP_COORD_FILES", "AP_RELEASE_CACHE", "AP_REPO_FILES"):
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


class TestCheckpointRetention(Base):
    def test_pending_delete_waits_for_explicit_owner_resolution(self):
        j={"id":"x", "path":"/kit", "host":"epyc2", "status":"DONE-STRUCTURAL", "delete_pending":True}
        self.ap.read_coord=lambda p:""
        self.ap.hub_procs=lambda p:[]
        self.ap.rpy=lambda *a,**kw:self.fail("deleted before owner diagnosis")
        self.ap.retry_pending({"jobs":{"x":j}})
        self.ap.read_coord=lambda p:"x\tDELETE\tresults/geom_review/diagnosis.json\n"
        self.ap.rpy=lambda *a,**kw:{"deleted":["/kit/run/results"]}
        self.ap.retry_pending({"jobs":{"x":j}})
        self.assertTrue(j["data_deleted"])


class TickBase(Base):
    def setUp(self):
        super().setUp()
        self.ap.canary_wave_gate = lambda row: (True, "fixture reference PASS")
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

    def test_near_miss_keeps_checkpoint_until_diagnosed(self):
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
        self.assertFalse(any(c[1] == self.ap.PROBE_DELETE[:40] for c in self.f.calls))

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
        body = [l for l in g if not l.startswith("#")]
        self.assertRegex(body[0].strip(), r"^9[01] m ", body)
        self.assertIn("GEOM-REQ-UNANSWERED [S81/H4]", body[0])
        self.assertTrue(any("GEOM-PASS-NOT-ROUTED [QC-CQB]" in l for l in body))
        self.assertTrue(any("READY-NO-COORD claude/b-1025" in l for l in body))
        self.assertFalse(any("claude/a-1025" in l for l in body))
        self.assertTrue(any("HOST-IDLE epyc4" in l for l in body))
        self.assertFalse(any("epyc2" in l or "[NEW]" in l or "QC-VMR" in l for l in body))

    def test_resolved_verdict_is_not_a_gap(self):
        self.geom(f"{ts(300)} GEOM-REVIEW: REPLY [S81/KITS {ts(305)[11:16]}] eg_c r7: PASS -> route\n"
                  f"{ts(100)} GEOM-REVIEW: REPLY [S81/KITS {ts(105)[11:16]}] slice_station x6: PASS-COND -> route\n"
                  f"{ts(90)} GEOM-REVIEW: REPLY [HBM-CORES] gq_land: PASS -> route\n")
        (Path(self.tmp.name) / "coord" / "autopilot").mkdir()
        (Path(self.tmp.name) / "coord" / "autopilot" / "resolved.tsv").write_text(
            self.ap.LG.RESOLVED_HEAD + "\n" + f"S81/KITS\t{ts(300)[:16]}\tSUPERSEDED\teg_c\tPASS-RECON\tx\tlegacy kit\n"
            f"HBM-CORES\t{ts(90)[:16]}\t\tgq_land\tPASS-RECON\tx\tno resolution -> still a gap\n")
        self.tick()
        g = (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text()
        self.assertNotIn("eg_c r7", g)                       # resolved verdict
        self.assertIn("slice_station x6", g)                 # same tag, other verdict: still flagged
        self.assertIn("GEOM-PASS-NOT-ROUTED [HBM-CORES]", g)  # empty resolution does not count

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



class TestGeomDemote(TickBase):
    """2026-10-25 R5 9a237c656129: plan-only PASS-COND 09:59, post-CTS FAIL 10:06 on the same tag -> must not route"""
    REQ_ROW = ROW[:4] + ["REQ", "[PROTO-KITS]"] + ROW[6:]

    def geom(self, text):
        (Path(self.tmp.name) / "coord" / "lanes" / "GEOM-REVIEW.md").write_text(text)

    def log(self):
        return (Path(self.tmp.name) / "log.txt").read_text()

    REQ = f"GEOM REQ [PROTO-KITS] slice_station__t5 kit\n"

    def test_latest_verdict_wins_both_orders(self):
        import loopgaps as L
        pc_fail = (f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 plan "
                   f"PASS-COND\n{ts(10)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 post-CTS: FAIL, no route\n")
        self.assertEqual(L.geom_verdicts(pc_fail, "PROTO-KITS", "slice_station__t5", "")[0], "FAIL")
        fail_pass = (f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: FAIL\n"
                     f"{ts(10)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 fixed: PASS\n")
        self.assertEqual(L.geom_verdicts(fail_pass, "PROTO-KITS", "slice_station__t5", "")[0], "PASS")
        rows = self.ap.parse_queue("\t".join(self.REQ_ROW))
        self.ap.resolve_geom(rows, pc_fail)
        self.assertEqual(list(rows.values())[0]["geom"], "FAIL")
        rows = self.ap.parse_queue("\t".join(self.REQ_ROW))
        self.ap.resolve_geom(rows, fail_pass)
        self.assertEqual(list(rows.values())[0]["geom"], "PASS")

    def test_correction_clause_mixing_fail_and_pass_cond_is_fail(self):
        import loopgaps as L                               # real btab_s6 09:07 wording
        t = (f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS-COND\n"
             f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: FAIL (corrects my 09:0x PASS-COND; autopilot "
             f"abc must not route). Measured\n")
        self.assertEqual(L.geom_verdicts(t, "PROTO-KITS", "slice_station__t5", "")[0], "FAIL")

    def held_on_pass_cond(self, row):
        self.ap.canary_wave_gate = lambda r: (False, "canary unbound")
        self.queue(row)
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 plan "
                  f"PASS-COND\n")
        (j,) = self.tick().values()
        self.assertEqual((j["status"], j["geom"]), ("WAIT-CANARY", "PASS-COND"))

    def test_later_fail_demotes_held_row_and_it_never_routes(self):
        self.held_on_pass_cond(self.REQ_ROW)
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 plan "
                  f"PASS-COND\n{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 post-CTS: FAIL, no route\n")
        (j,) = self.tick().values()
        self.assertEqual((j["status"], j["geom"]), ("WAIT-GEOM", "FAIL"))
        self.assertIn("DEMOTE", self.log())
        self.assertIn("PASS-COND -> FAIL", self.log())
        self.ap.canary_wave_gate = lambda r: (True, "bound")
        (j,) = self.tick().values()
        self.assertEqual((j["status"], self.f.launched), ("WAIT-GEOM", []))

    def test_hand_pass_cond_row_is_demoted_by_later_fail_never_promoted(self):
        hand = ROW[:4] + ["PASS-COND", "GEOM-REVIEW [PROTO-KITS] reply"] + ROW[6:]
        self.held_on_pass_cond(hand)
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: FAIL\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-GEOM")

    def test_hand_fail_row_demotes_canary_hold(self):
        self.held_on_pass_cond(self.REQ_ROW)
        self.queue(self.REQ_ROW, ROW[:4] + ["FAIL", ""] + ROW[6:])         # the coordinator's 10:1x hand demotion
        (j,) = self.tick().values()
        self.assertEqual((j["status"], j["geom"]), ("WAIT-GEOM", "FAIL"))
        self.assertIn("DEMOTE", self.log())

    def test_fail_after_submit_warns_never_demotes(self):
        self.queue(self.REQ_ROW)
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS\n"
                  f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 corrected: FAIL\n")
        (j,) = self.tick().values()
        self.tick()
        self.assertEqual((j["status"], len(self.f.launched)), ("RUNNING", 1))
        self.assertEqual(self.log().count("WARN GEOM-FAIL-AFTER-SUBMIT"), 1)
        alerts = (Path(self.tmp.name) / "geom_alerts.tsv").read_text().splitlines()
        self.assertEqual(len(alerts), 2)
        self.assertIn("GEOM-FAIL-AFTER-SUBMIT", (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text())


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


class TestOwnership(TickBase):
    """OWNERS.tsv + OWNERSHIP summary + UNOWNED-ITEM gaps (ownership.py) from fake origin/main + coord files"""
    def setUp(self):
        super().setUp()
        p = Path(self.tmp.name)
        repo = p / "repo"
        os.environ["AP_REPO_FILES"] = str(repo)
        self.ap = importlib.reload(self.ap)                # re-read the env (REPO_FILES)
        self.ap.canary_wave_gate = lambda row: (True, "fixture reference PASS")
        self.f = FakeHosts(self.ap)
        self.ap.rpy, self.ap.launch_unit = self.f.rpy, self.f.launch
        self.ap.unit_active = lambda u: u in self.f.active
        self.ap.rbash = lambda host, script, timeout=0: (0, "", "")
        self.ap.hub_procs = lambda path: []
        self.ps = ""
        self.ap.sh = lambda cmd, timeout=0, input=None: (0, self.ps, "") if cmd[0] == "ps" else (0, "", "")
        s81 = {"partition_types": {
            "slice_station__t5": {"module": "s81p_slice_station__t5", "hard_cores": [{"module": "dsfd_qbank_N"}]},
            "slice_station__t6": {"module": "s81p_slice_station__t6"},
            "slice_station__t7": {"module": "s81p_slice_station__t7"},
            "ot_s81sl_leaf__t1": {"module": "s81p_leaf__t1"},
            "ot_s81sl_leaf__t10": {"module": "s81p_leaf__t10"},
            "eng__t1": {"module": "s81p_eng__t1", "hard_cores": [{"module": "dsdv_eng_rr_h0"}, {"module": "dsdv_gunit_l1"}]}}}
        head = {"partition_types": {"hd_turn_a": {"module": "ot_s81hd_turn_a"},
                                    "hd_tile": {"module": "ot_s81hd_tile_p", "hard_cores": [{"module": "ot_s81hd_elemB_cv"}]}}}
        qc = {"partition_types": {"coll_ft": {"module": "qfd_coll_ft"},
                                  "sle_sc": {"module": "qfd_sle_sc", "hard_cores": [{"module": "qfd_dv_s8x_vmr"}]}}}
        kv = {"partition_types": {"kv3_hg": {"module": "kv3_hg_part"}, "kv3_hg_v2": {"module": "kv3_hg_v2_part"}}}
        hbm = {"partition_types": {"q_b000": {"module": "hbm_arch_q_b000", "hard_cores": [{"module": "ot_hbm_x_core"}]},
                                   "root": {"module": "hbm_arch_root"}}}
        for d, P in (("s81", s81), ("s81_head", head), ("qwen_compute", qc), ("qwen_kvsys", kv), ("hbm_arch/B2n", hbm)):
            (repo / "physical/die_plan" / d).mkdir(parents=True)
            (repo / "physical/die_plan" / d / "die_plan.json").write_text(json.dumps(P))
        (repo / "results/proto_1025/geom").mkdir(parents=True)
        (repo / "results/proto_1025/g2").mkdir(parents=True)
        (repo / "results/proto_1025/geom/B2n.json").write_text(json.dumps(
            {"plan": "x", "types": {"q_b000": {"verdict": "FAIL"}, "root": {"verdict": "PASS"}}}))
        (repo / "results/proto_1025/g2/res_qwen_kvsys.json").write_text(json.dumps(
            {"kv3_hg": {"classify": {"cls": "STRUCTURAL", "why": "GRT ov 5000"}}, "kv3_hg_v2": {"classify": {"cls": "CLEAN"}}}))
        (p / "release_cache.json").write_text(json.dumps({"plans": {"s81": {"signed_types": {"slice_station__t7": ["x"]},
                                                                            "signed_cores": {}}},
                                                          "signed_records": [{"name": "kr_dsdv_gunit_l1_lfp", "top": None,
                                                                              "path": "/a/signoff.json", "scan_host": "epyc1"}]}))

    def lane(self, name, text):
        (Path(self.tmp.name) / "coord" / "lanes" / f"{name}.md").write_text(text)

    def owners(self):
        lines = (Path(self.tmp.name) / "OWNERS.tsv").read_text().splitlines()
        head = lines[1].split("\t")
        return {(r["die"], r["item"]): r for r in (dict(zip(head, l.split("\t"))) for l in lines[2:])}

    def test_matcher_longest_prefix_and_aliases(self):
        import ownership as O
        items = O.plan_items("qwen_kvsys", {"partition_types": {"kv3_hg": {"module": "kv3_hg_part"},
                                                                "kv3_hg_v2": {}, "glue": {"module": "qfd_glue"}}})
        items += O.plan_items("s81_head", {"partition_types": {"hd_tile": {"hard_cores": [{"module": "ot_s81hd_elemB_cv"}]}}})
        M = O.Matcher(items)
        self.assertEqual(M.text("kv3_hg_v2__190.08x181.44"), {("qwen_kvsys", "kv3_hg_v2")})
        self.assertEqual(M.text("gen/qwen_kvsys/part_kv3_hg"), {("qwen_kvsys", "kv3_hg")})
        self.assertEqual(M.text("kits/elemB_rb hd_elemB_rb__s2_c60"), {("s81_head", "ot_s81hd_elemB_cv")})
        self.assertEqual(M.text("glue logic in the kv3_hgx tile"), set())          # short key / no boundary
        self.assertEqual(O.default_owner("qwen_compute", "core", "qfd_dv_s8x_vmr"), "QC-CQB")
        self.assertEqual(O.default_owner("s81", "core", "x"), "S81-CORES")
        self.assertEqual(O.default_owner("hbm", "type", "x"), "HBM-PLAN")

    def test_states_owners_and_unowned_gap(self):
        p = Path(self.tmp.name)
        self.lane("S81", f"{ts(30)} S81: slice_station__t6 kit regenerated, GEOM REQ next\n")
        self.lane("PROTO", f"{ts(200)} PROTO: hd_tile kit waits\n")
        (p / "coord" / "lanes" / "GEOM-REVIEW.md").write_text(
            f"{ts(90)} S81-CORES: GEOM REQ [S81-CORES/X] dsdv_eng_rr_h0_c placed\n"
            f"{ts(80)} QC: GEOM REQ [QC-A] coll_ft kit\n{ts(70)} GEOM-REVIEW: REPLY [QC-A] coll_ft: PASS -> route\n"
            f"{ts(65)} PROTO: GEOM REQ [PROTO kv] kv3_hg_v2 skeleton prototypes\n"
            f"{ts(60)} GEOM-REVIEW: REPLY [PROTO kv] kv3_hg_v2 skeleton PASS\n")
        old = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(time.time() - 7200))
        (p / "review.tsv").write_text(self.ap.TSV_HEAD["review.tsv"] + "\n" + "\t".join(
            [old, "abc123", "s81_head", "hd_turn_a", "x@1234567", "epyc1", KIT, "NEAR-MISS", "r", "/rv/abc123", "", "",
             "PROTO-KITS"]) + "\n")
        self.ps = ("4242 300 python3 /home/ubuntu/.local/bin/ot-run --mem 24 --dir /srv/opentallas-scratch2/claude/x/"
                   "ot_s81sl_leaf__t1 -- bash /srv/x/run_kit.sh /srv/x route 24 8\n"
                   "4243 30 python3 /home/ubuntu/.local/bin/ot-run --mem 40 --dir /srv/opentallas-scratch2/claude/proto/"
                   "gen/B2n/part_root -- bash run.sh\n")
        self.tick()
        o = self.owners()
        st = lambda k: o[k]["state"]
        self.assertEqual(st(("s81", "slice_station__t7")), "SIGNED")              # cache per-plan list
        self.assertEqual(st(("s81", "dsdv_gunit_l1")), "SIGNED")                  # cache record, kr_/_lfp rule
        self.assertEqual(st(("s81", "ot_s81sl_leaf__t1")), "ROUTING")             # live ot-run route, not t10
        self.assertEqual(st(("s81", "ot_s81sl_leaf__t10")), "NEEDS-KIT")
        self.assertEqual(st(("s81", "dsdv_eng_rr_h0")), "GEOM-REQ")
        self.assertEqual(st(("qwen_compute", "coll_ft")), "KIT-PLACED")
        self.assertEqual(st(("s81_head", "hd_turn_a")), "REVIEW")
        self.assertEqual(o[("s81_head", "hd_turn_a")]["owner"], "PROTO-KITS")
        self.assertEqual(st(("qwen_kvsys", "kv3_hg")), "PLAN-STRUCTURAL")          # G2 STRUCTURAL
        self.assertEqual(st(("qwen_kvsys", "kv3_hg_v2")), "NEEDS-KIT")            # skeleton review is not a kit event
        self.assertEqual(st(("hbm", "q_b000")), "PLAN-STRUCTURAL")                # PROTO geom FAIL
        self.assertEqual(st(("hbm", "root")), "NEEDS-KIT")                        # G2 probe live: state kept
        self.assertIn("ot-run pid 4243", o[("hbm", "root")]["live_job"])
        self.assertEqual(o[("s81", "slice_station__t6")]["owner"], "S81")
        self.assertEqual(o[("s81", "slice_station__t5")]["owner"], "S81-PLAN")
        self.assertEqual(o[("s81", "dsfd_qbank_N")]["owner"], "S81-CORES")
        self.assertEqual(o[("qwen_compute", "qfd_dv_s8x_vmr")]["owner"], "QC-CQB")
        g = (p / "LOOP-GAPS.txt").read_text()
        self.assertIn("# OWNERSHIP", g)
        self.assertRegex(g, r"#   s81 +\d+: .*SIGNED 2 \| UNOWNED \d+")
        self.assertIn("UNOWNED-ITEM s81 -> S81-PLAN", g)
        self.assertIn("slice_station__t5", g)
        unowned = [l for l in g.splitlines() if "UNOWNED-ITEM" in l]
        self.assertFalse(any("slice_station__t6" in l or "slice_station__t7" in l or "ot_s81sl_leaf__t1 " in l
                             or " root" in l for l in unowned))
        self.assertIn("hd_tile(PROTO)", g)                                         # 200 min ago: unowned, last lane shown

    def test_ownership_failure_never_stops_the_gap_report(self):
        import ownership as O
        orig = O.build
        O.build = lambda inp, now=None: 1 / 0
        try:
            self.tick()
        finally:
            O.build = orig
        g = (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text()
        self.assertIn("OWNERSHIP unavailable", g)


class TestDistinctDesigns(unittest.TestCase):
    """OWNERS items are distinct designs: cores by RTL master + outline + pin table, types by RTL + outline + pins"""
    @staticmethod
    def pins(*xy):
        return json.dumps([{"name": f"p{i}", "layer": "M5", "x": x, "y": y} for i, (x, y) in enumerate(xy)])

    def hbm(self):
        hc = lambda m, pf: {"inst": "u", "module": m, "outline_um": [10.0, 20.0], "pins_file": pf}
        plan = {"partition_types": {
            "q_a": {"module": "pa", "hard_cores": [hc("piece__r0", "cores/r0.json"), hc("piece__r1", "cores/r1.json"),
                                                   hc("pc_ctrl", "cores/pc_x.json")]},
            "q_b": {"module": "pb", "hard_cores": [hc("piece__r2", "cores/r2.json"), hc("pc_ctrl", "cores/pc_y.json"),
                                                   hc("pc_ctrl", "cores/pc_x2.json")]}},
            "partitions": [{"type": "q_a"}, {"type": "q_a"}, {"type": "q_b"}]}
        same, other = self.pins((0, 1), (2, 3)), self.pins((0, 1), (2, 4))
        pins = {"cores/r0.json": same, "cores/r1.json": same, "cores/r2.json": same,
                "cores/pc_x.json": same, "cores/pc_x2.json": same + " ", "cores/pc_y.json": other}
        canonical = {"types": {"hcol_h0": {"top": "ot_hidx_score_hcol", "type_ids": {
            f"piece__r{i}__10x20": {} for i in range(3)}}}}
        return plan, pins, canonical

    def test_core_replicas_and_multi_table_modules(self):
        import ownership as O
        plan, pins, canonical = self.hbm()
        items = O.plan_items("hbm", plan, pins, O.canonical_masters(canonical))
        cores = {it["item"]: it for it in items if it["kind"] == "core"}
        piece = cores["piece__r0"]                         # 3 piece modules, one master + table: ONE design
        self.assertEqual(piece["members"], ["piece__r0", "piece__r1", "piece__r2"])
        self.assertEqual(piece["replicas"], 5)            # placed: r0 in q_a x2 + r1 in q_a x2 + r2 in q_b x1
        pc = sorted(k for k in cores if k.startswith("pc_ctrl"))
        self.assertEqual(len(pc), 2)                       # 2 pin tables (pc_x2 = pc_x content) -> 2 designs
        self.assertTrue(all(re.fullmatch(r"pc_ctrl_[0-9a-f]{12}", k) for k in pc))
        self.assertEqual(sorted(cores[k]["replicas"] for k in pc), [1, 3])

    def test_one_signoff_clears_every_replica_but_not_other_tables(self):
        import ownership as O
        plan, pins, canonical = self.hbm()
        sha_y = O.pin_sig(pins["cores/pc_y.json"])[0]
        cache = {"plans": {"hbm_arch/B2n": {"signed_types": {}, "signed_cores": {
                     "piece__r1": ["host:/k/piece__r1/signoff.json"],
                     "pc_ctrl": [f"host:/kits/pc_ctrl_{sha_y}/signoff.json"]}}},
                 "signed_records": [{"name": "kl_pc_ctrl_c", "top": "pc_ctrl", "path": "/k/unknown/signoff.json"}]}
        rows, _, head = O.build(dict(plans={"hbm": plan}, core_pins={"hbm": pins}, canonical=canonical, cache=cache),
                                now=time.time())
        st = {r["item"]: r for r in rows if r["die"] == "hbm"}
        self.assertEqual(st["piece__r0"]["state"], "SIGNED")          # r1 signed -> r0 / r2 replicas cleared
        self.assertEqual(st["piece__r0"]["replicas"], 5)
        self.assertIn("3: piece__r0 piece__r1 piece__r2", st["piece__r0"]["members"])
        self.assertEqual(st[f"pc_ctrl_{sha_y}"]["state"], "SIGNED")   # the table named by the kit dir sha
        other = [k for k in st if k.startswith("pc_ctrl") and k != f"pc_ctrl_{sha_y}"]
        self.assertEqual([st[k]["state"] for k in other], ["NEEDS-KIT"])   # module-level record: table unknown
        self.assertTrue(any("types 2 cores 3" in h for h in head))

    def test_job_of_one_table_routes_only_that_design(self):
        import ownership as O
        plan, pins, canonical = self.hbm()
        sha_y = O.pin_sig(pins["cores/pc_y.json"])[0]
        jobs = [{"id": "j1", "status": "RUNNING", "die": "hbm", "type": "pc_ctrl", "lane": "HBM-KITS",
                 "kit": f"epyc2:/srv/x/pc_ctrl_{sha_y}", "updated": time.time()}]
        rows, _, _ = O.build(dict(plans={"hbm": plan}, core_pins={"hbm": pins}, canonical=canonical, jobs=jobs))
        st = {r["item"]: r["state"] for r in rows if r["die"] == "hbm"}
        self.assertEqual(st[f"pc_ctrl_{sha_y}"], "ROUTING")
        self.assertEqual(sorted(v for k, v in st.items() if k.startswith("pc_ctrl")), ["NEEDS-KIT", "ROUTING"])

    def test_types_merge_on_identical_rtl_outline_pins_only(self):
        import ownership as O
        bus = lambda face: {"name": "a", "dir": "in", "width": 8, "kind": "data", "face": face, "window_um": [0, 5]}
        t = lambda mod, face="N", w=100.0: {"module": mod, "outline_um": [w, 50.0], "buses": [bus(face)],
                                             "contents": [{"inst": "u", "module": "core_x", "origin_um": [1, 1]}]}
        plan = {"partition_types": {"a1": t("m_a1"), "a2": t("m_a2"), "a3": t("m_a3"), "b": t("m_b", face="S"),
                                    "c": t("m_c", w=90.0)},
                "partitions": [{"type": "a1"}, {"type": "a2"}, {"type": "a2"}, {"type": "a3"}, {"type": "b"}]}
        paths = O.bound_rtl_paths("kv", plan)
        self.assertEqual(sorted(paths), ["a1", "a2", "a3"])
        self.assertEqual(paths["a1"][0], "physical/die_plan/kv/bind/bound_r8/rtl/m_a1.sv")
        rtl = lambda mod, pad: f"// gen\nmodule {mod} (input a);\n  dly #({pad}) u();\nendmodule\n"
        items = O.plan_items("kv", plan, bound={"a1": rtl("m_a1", 2), "a2": rtl("m_a2", 2), "a3": rtl("m_a3", 7)})
        ty = {it["item"]: it for it in items if it["kind"] == "type"}
        self.assertEqual(sorted(ty), ["a2", "a3", "b", "c"])   # a1+a2 one design (rep = most instances)
        self.assertEqual((ty["a2"]["members"], ty["a2"]["replicas"]), (["a1", "a2"], 3))
        items = O.plan_items("kv", plan)                          # bound RTL unreadable: nothing merges
        self.assertEqual(len([it for it in items if it["kind"] == "type"]), 5)
        M = O.Matcher(O.plan_items("kv", plan, bound={"a1": rtl("m_a1", 2), "a2": rtl("m_a2", 2)}))
        self.assertEqual(M.text("gen/kv/part_a1"), {("kv", "a2")})   # a lane line naming a1 counts for the design

    def test_netlist_key_matches_dedup(self):
        import ownership as O
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
        try:
            import dedup
        except ImportError:
            self.skipTest("tools/die_plan not present")
        t = {"outline_um": [10, 20], "hard": True, "reset": {"sync_stages": 2}, "sources": ["b", "a"],
             "buses": [{"name": "x", "dir": "in", "width": 3, "face": "N", "note": "n"}],
             "ft_slots": [{"name": "s", "width": 4, "stations": 1, "in_face": "W", "regs_um": [1]}],
             "contents": [{"inst": "u", "module": "m", "params": {"P": 1}, "origin_um": [0, 0]}],
             "hard_cores": [{"inst": "h", "module": "c", "origin_um": [1, 1]}]}
        self.assertEqual(O.netlist_key(t), dedup.netlist_key(t))


class TestChainSafety(Base):
    def test_parent_staging_client_and_spill_are_busy(self):
        k = "/srv/opentallas-scratch2/claude/kv/heads/e2/kit"
        for flag in ("--dir", "--stage"):
            self.assertTrue(self.ap.process_uses_kit("python3 /home/ubuntu/.local/bin/ot-run " + flag +
                " /srv/opentallas-scratch2/claude/kv/heads/e2 -- bash /srv/opentallas-scratch2/claude/kv/heads/e2/go.sh", k))
        self.assertFalse(self.ap.process_uses_kit("ot-run --dir /srv/opentallas-scratch2/claude/kv/heads/e20", k))

    def test_signoff_does_not_finish_busy_adopted_chain(self):
        self.ap.hub_procs = lambda path: []
        self.ap.probe_job = lambda j: so()
        self.ap.rpy = lambda *a, **kw: {"busy": True, "log_age_s": 3000}
        self.ap.finish = lambda *a: self.fail("finished a live chain")
        self.ap.poll_adopted({}, {"host": "epyc2", "path": "/kit"})


class TestReviewIdentity(unittest.TestCase):
    def test_batches_never_share_clearance(self):
        import loopgaps as L
        text = "2026-10-25 05:20 GEOM REQ [PROTO-KITS/S81-178 B1] t12 @0123456789ab\n" \
               "2026-10-25 05:21 GEOM REQ [PROTO-KITS/S81-178 B2] t25 @0123456789ab\n" \
               "2026-10-25 05:44 GEOM-REVIEW: REPLY [PROTO-KITS/S81-178 B2] PASS-COND route t25 @0123456789ab\n"
        self.assertIsNone(L.geom_verdicts(text, "PROTO-KITS/S81-178 B1", "slice_station__t12", "0123456789ab"))
        self.assertEqual(L.geom_verdicts(text, "PROTO-KITS/S81-178 B2", "slice_station__t25", "0123456789ab")[0], "PASS-COND")

    def test_continuation_verdict_names_are_retained(self):
        import loopgaps as L
        text = "2026-10-25 05:20 GEOM REQ [BATCH B1] t12 t18\n" \
               "2026-10-25 05:44 GEOM-REVIEW: REPLY [BATCH B1] reviewed:\n" \
               "  t12 PASS-COND route; t18 FAIL pins\n"
        self.assertEqual(L.geom_verdicts(text, "BATCH B1", "slice_station__t12", "")[0], "PASS-COND")
        self.assertEqual(L.geom_verdicts(text, "BATCH B1", "slice_station__t18", "")[0], "FAIL")


class TestSharedShaRows(Base):
    """2026-10-25 10:30 [PATH-QC-SRAMIF-S7]: btab_s7 and prog_s7 share tag + branch sha; a PASS-COND for btab_s7 that
    quotes the sha must never clear prog_s7"""
    SRC = "claude/path-qc-sramif-1025@90bf56dfa"
    REQ = ("2026-10-25 10:27 PDT PATH-QC-SRAMIF: GEOM REQ [PATH-QC-SRAMIF-S7] shared QC SRAM-IF fix. src "
           "claude/path-qc-sramif-1025@90bf56dfa\n  btab_s7 intel1:/x/btab_s7: S6_GRT_GATE PASS -> enqueued --geom REQ.\n"
           "2026-10-25 10:28 PDT PATH-QC-SRAMIF: GEOM REQ [PATH-QC-SRAMIF-S7] update: prog_s7 enqueued\n")

    def rows(self, *types):
        return self.ap.parse_queue("\n".join("\t".join(
            ["qwen_compute", f"qfd_dv_s8x_{t}__s7", f"intel1:/srv/opentallas-scratch2/claude/path-qc-sramif/{t}_s7",
             self.SRC, "REQ", "PATH-QC-SRAMIF-S7", "24", "30000", "PATH-QC"]) for t in types))

    def geom(self, rows):
        return {r["type"]: r["geom"] for r in rows.values()}

    def test_btab_reply_quoting_shared_sha_clears_btab_only(self):
        reply = ("2026-10-25 10:30 PDT GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] qfd_dv_s8x_btab__s7 (btab_s7, "
                 "claude/path-qc-sramif-1025@90bf56dfa): PASS-COND -> route (autopilot row, 1 variant).\n"
                 "  Not covered by this reply (no route token): prog_s7 routes after it posts its own hold-gate line.\n")
        rows = self.rows("btab", "prog")
        self.ap.resolve_geom(rows, self.REQ + reply)
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "PASS-COND", "qfd_dv_s8x_prog__s7": "REQ"})
        # the kit dir basename names the row too; the shared suffix 's7' does not
        rows = self.rows("btab", "prog")
        self.ap.resolve_geom(rows, self.REQ + "2026-10-25 10:31 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] btab_s7 "
                                              "@90bf56dfa PASS-COND route; s7 viewed\n")
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "PASS-COND", "qfd_dv_s8x_prog__s7": "REQ"})
        self.assertEqual(self.ap.LG.gaps_geom_ambiguous(self.REQ + reply, self.ap.geom_groups(rows), 0), [])

    def test_single_row_tag_sha_only_still_resolves(self):
        rows = self.rows("btab")
        self.ap.resolve_geom(rows, self.REQ + "2026-10-25 10:31 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] "
                                              "claude/path-qc-sramif-1025@90bf56dfa: PASS-COND route\n")
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "PASS-COND"})

    def test_sha_only_reply_on_shared_tag_is_ambiguous(self):
        reply = ("2026-10-25 10:31 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] claude/path-qc-sramif-1025@90bf56dfa: "
                 "PASS-COND route\n")
        rows = self.rows("btab", "prog")
        self.ap.resolve_geom(rows, self.REQ + reply)
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "REQ", "qfd_dv_s8x_prog__s7": "REQ"})
        now = time.mktime(time.strptime("2026-10-25 11:00", "%Y-%m-%d %H:%M"))
        (g,) = self.ap.LG.gaps_geom_ambiguous(self.REQ + reply, self.ap.geom_groups(rows), now)
        self.assertIn("AMBIGUOUS-GEOM [PATH-QC-SRAMIF-S7]", g[1])

    def test_later_per_row_repost_clears_ambiguous(self):
        """2026-10-25 S81-CORES/LEGACY b1 + HBM-KITS/B2: the reviewer re-posted per row after a sha-only reply; a row
        named by a LATER reply (type, kit dir or row id) is no longer AMBIGUOUS-GEOM, an unnamed one still is"""
        sha_only = ("2026-10-25 10:31 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] claude/path-qc-sramif-1025@90bf56dfa: "
                    "PASS-COND route\n")
        now = time.mktime(time.strptime("2026-10-25 11:00", "%Y-%m-%d %H:%M"))
        rows = self.rows("btab", "prog")
        groups = self.ap.geom_groups(rows)
        repost = ("2026-10-25 10:40 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] (re-post per row)\n"
                  "    REPLY [PATH-QC-SRAMIF-S7] btab_s7: PASS-COND route\n")
        (g,) = self.ap.LG.gaps_geom_ambiguous(self.REQ + sha_only + repost, groups, now)
        self.assertIn("reply reaches qfd_dv_s8x_prog__s7 only", g[1])
        repost += "    REPLY [PATH-QC-SRAMIF-S7] qfd_dv_s8x_prog__s7: FAIL outline\n"
        self.assertEqual(self.ap.LG.gaps_geom_ambiguous(self.REQ + sha_only + repost, groups, now), [])
        # a reply naming the row BEFORE the sha-only one does not clear it
        self.assertEqual(len(self.ap.LG.gaps_geom_ambiguous(
            self.REQ + repost.replace("10:40", "10:30") + sha_only, groups, now)), 1)

    def test_later_fail_naming_type_demotes_and_mixed_reads_fail(self):
        t = (self.REQ + "2026-10-25 10:30 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] btab_s7 PASS-COND route; "
             "prog_s7 PASS-COND route\n2026-10-25 10:40 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] prog_s7 FAIL "
             "(corrects my PASS-COND) @90bf56dfa\n")
        rows = self.rows("btab", "prog")
        self.ap.resolve_geom(rows, t)
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "PASS-COND", "qfd_dv_s8x_prog__s7": "FAIL"})

    def test_kit_hash_names_row_and_reconcile_withdraw_reads_fail(self):
        import loopgaps as L
        hb = [("ot_hbm_idx_qctl_static_324c16535028", "epyc2:/k/a", "aea2ae39b3", "r1"),
              ("ot_hbm_static_cfg_collar_6ca949259674", "epyc2:/k/b", "aea2ae39b3", "r2")]
        t = ("2026-10-25 07:17 HBM-KITS: GEOM REQ [HBM-KITS/B2 07:17] 2 kits @aea2ae39b3\n"
             "2026-10-25 07:24 CODEX GEOM-REVIEW: REPLY [HBM-KITS/B2 07:17] claude/hbm-kits-1025r@aea2ae39b3:\n"
             "  (1) idx_qctl 324c16535028: FAIL outline; (2) cfg_collar 6ca949259674: placement PASS-COND\n")
        self.assertEqual(L.geom_verdicts(t, "HBM-KITS/B2", *hb[0][:1], hb[0][2], kit=hb[0][1], others=hb[1:])[0], "FAIL")
        self.assertEqual(L.geom_verdicts(t, "HBM-KITS/B2", *hb[1][:1], hb[1][2], kit=hb[1][1], others=hb[:1])[0],
                         "PASS-COND")
        w = (self.REQ + "2026-10-25 10:30 GEOM-REVIEW-2: REPLY [PATH-QC-SRAMIF-S7] btab_s7: PASS-COND -> route\n"
             "2026-10-25 10:45 GEOM-REVIEW-2: RECONCILE [PATH-QC-SRAMIF-S7] btab_s7: this WITHDRAWS my 10:30 route "
             "PASS-COND\n")
        rows = self.rows("btab", "prog")
        self.ap.resolve_geom(rows, w)
        self.assertEqual(self.geom(rows), {"qfd_dv_s8x_btab__s7": "FAIL", "qfd_dv_s8x_prog__s7": "REQ"})


if __name__ == "__main__":
    unittest.main()
