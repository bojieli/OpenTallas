#!/usr/bin/env python3
"""tests for tools/autopilot (no ssh, no ot-run, no systemd: the host / unit layer is faked)"""
import importlib
import datetime
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


def so(verdict="NOT SIGNED", tt=5.0, ff=-3.0, fails=("hold_ff",), drc=0, pg="PASS"):
    return {"signoff": {"path": "/k/signoff/signoff.json", "verdict": verdict, "reasons": ["r"], "fails": list(fails),
                        "tt_wns": tt, "ff_wns": ff, "drc": drc, "odb": "/k/run/x/6_final.odb", "base": "/k/run/x",
                        "pg": pg},
            "grt_overflow": 0, "chain": {"started": time.time(), "verdict": "PASS", "lec_verdict": "EQUIVALENT", "lec_exit": 0,
                                          "lec_all_shown": True, "gates": {"setup_tt": "PASS", "routed_lec": "PASS"}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AP_DIR"] = self.tmp.name
        os.environ["AP_QUEUE_FILE"] = str(Path(self.tmp.name) / "queue.tsv")
        os.environ["AP_COORD_FILES"] = str(Path(self.tmp.name) / "coord")
        os.environ["AP_RELEASE_CACHE"] = str(Path(self.tmp.name) / "release_cache.json")
        os.environ["AP_OT_RUN_SIGNALS"] = str(Path(self.tmp.name) / "no_signals.log")   # never the host's real log
        os.environ["AP_WATCHDOG_LOG"] = str(Path(self.tmp.name) / "no_watchdog.log")    # never the hub's real log
        (Path(self.tmp.name) / "coord" / "lanes").mkdir(parents=True)
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.DRY = False
        self.ap.stage_admission_tools = lambda: dict(dir="/srv/opentallas-scratch2/claude/ap-tools/v1",
            chain="/srv/opentallas-scratch2/claude/ap-tools/v1/signoff_chain.py",
            preflight="/srv/opentallas-scratch2/claude/ap-tools/v1/die_plan/kit_preflight.py", sha256="tools-v1")

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("AP_DIR", "AP_QUEUE_FILE", "AP_COORD_FILES", "AP_RELEASE_CACHE", "AP_REPO_FILES", "AP_OT_RUN_SIGNALS",
                  "AP_WATCHDOG_LOG"):
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

    def test_cts_requires_explicit_runner_and_preserves_goal(self):
        (j,) = self.ap.parse_queue("\t".join(ROW + ["cts"])).values()
        self.assertIn("explicit CTS-only runner", j["error"])
        (j,) = self.ap.parse_queue("\t".join(ROW + ["cts", "/srv/opentallas-scratch2/claude/run_cts_only.sh"])).values()
        self.assertEqual(j["error"], "")
        seen = []
        self.ap.launch_unit = lambda unit, logfile, argv: seen.append(argv) or True
        self.ap.submit({}, j)
        pos = seen[0].index("--")
        self.assertEqual(seen[0][pos + 4], "cts")

    def test_cell_cap_and_mem_and_paths(self):
        bad = {6: "517001", 5: "lots"}
        r = list(self.ap.parse_queue("\t".join(ROW[:7] + ["517001"] + ROW[8:])).values())[0]
        self.assertIn("517000", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:7] + ["517000"] + ROW[8:])).values())[0]
        self.assertEqual(r["error"], "")
        r = list(self.ap.parse_queue("\t".join(ROW[:6] + ["lots"] + ROW[7:])).values())[0]
        self.assertIn("mem_gb", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:2] + ["epyc2:/home/ubuntu/kit"] + ROW[3:])).values())[0]
        self.assertIn("kit must be", r["error"])
        r = list(self.ap.parse_queue("\t".join(ROW[:2] + [KIT + "/../x"] + ROW[3:])).values())[0]
        self.assertIn("kit must be", r["error"])
        # any numbered scratch root is a kit root (kw21 wave on epyc5 scratch3)
        k3 = "epyc5:/srv/opentallas-scratch3/claude/kw21-wave-1106/runs/s81/kit"
        r = list(self.ap.parse_queue("	".join(ROW[:2] + [k3] + ROW[3:])).values())[0]
        self.assertEqual(r["error"], "")
        self.assertEqual((r["host"], r["path"]), ("epyc5", k3.split(":", 1)[1]))
        r = list(self.ap.parse_queue("	".join(ROW[:2] + ["epyc5:/srv/opentallas-scratchx/claude/k"] + ROW[3:])).values())[0]
        self.assertIn("kit must be", r["error"])
        self.assertTrue(bad)

    def test_last_row_wins_and_comments(self):
        t = "# comment\n" + "\t".join(["die"] + ROW[1:]) + "\n" + "\t".join(ROW[:4] + ["PENDING", ""] + ROW[6:]) + \
            "\n" + "\t".join(ROW) + "\n"
        rows = self.ap.parse_queue(t)
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows.values())[0]["geom"], "PASS")


class TestAdmissionBundle(unittest.TestCase):
    def test_cached_bundle_bootstrap_executes_its_checker_and_helpers(self):
        import autopilot,base64,subprocess
        ap=importlib.reload(autopilot);ap.DRY=False
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);tools=root/"source";tools.mkdir()
            chain=root/"chain.py"
            chain.write_text("import subprocess,sys\nassert sys.argv[1]=='--preflight'\nsubprocess.run([sys.executable,sys.argv[2]],check=True)\nprint('CHAIN_PASS')\n")
            (tools/"helper.py").write_text("message='HELPER_PASS'\n")
            (tools/"kit_preflight.py").write_text("from helper import message\nprint(message)\n")
            bundle=ap.stage_admission_tools(chain,tools,root/"scratch")
            bundle["source_host"]="not-used-for-cached-bundle"
            meta=base64.b64encode(json.dumps(bundle).encode()).decode()
            result=subprocess.run([sys.executable,"-c",ap.ADMISSION_BOOTSTRAP,meta],capture_output=True,text=True,check=True)
            self.assertIn("ADMISSION_TOOLS READY",result.stdout)
            self.assertIn("HELPER_PASS",result.stdout)
            self.assertIn("CHAIN_PASS",result.stdout)

    def test_bootstrap_names_no_srv_path_so_otrun_can_spill(self):
        # KW-FIX-1 11-02: ot-run --stage SPILL refused every wave route ("command names /srv/opentallas-scratch outside
        # the --stage paths") because this script carried that literal; jobs then queued on intel1 only
        import autopilot
        ap=importlib.reload(autopilot)
        self.assertEqual(re.findall(r"/srv/[^\s'\";|&()<>]*", ap.ADMISSION_BOOTSTRAP), [])

    def test_shared_clock_family_is_pinned_inside_standalone_bundle(self):
        import autopilot
        ap=importlib.reload(autopilot);ap.DRY=False
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);tools=root/"repo/tools/die_plan";tools.mkdir(parents=True)
            common=root/"repo/physical/common_flow";common.mkdir(parents=True)
            chain=root/"chain.py";chain.write_text("# chain")
            (tools/"signoff.py").write_text("# checker")
            family=common/"clock_family.tcl";family.write_text("# physical family1")
            first=ap.stage_admission_tools(chain,tools,root/"scratch")
            old=Path(first["dir"])/"die_plan/clock_family.tcl"
            self.assertEqual(old.read_bytes(),family.read_bytes())
            family.write_text("# physical family2")
            second=ap.stage_admission_tools(chain,tools,root/"scratch")
            self.assertNotEqual(first["dir"],second["dir"])
            self.assertEqual(old.read_text(),"# physical family1")
            self.assertEqual((Path(second["dir"])/"die_plan/clock_family.tcl").read_text(),"# physical family2")

    def test_source_changes_create_new_immutable_own_scratch_bundle(self):
        import autopilot
        ap = importlib.reload(autopilot)
        ap.DRY = False
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chain=root/"chain.py"; chain.write_text("# chain")
            tools=root/"source"; tools.mkdir()
            (tools/"kit_preflight.py").write_text("# checker")
            (tools/"helper.py").write_text("# helper1")
            first=ap.stage_admission_tools(chain, tools, root/"own-scratch")
            before=Path(first["dir"])/"die_plan/helper.py"
            (tools/"helper.py").write_text("# helper2")
            second=ap.stage_admission_tools(chain, tools, root/"own-scratch")
            self.assertNotEqual(first["dir"],second["dir"])
            self.assertEqual(before.read_text(),"# helper1")
            self.assertEqual((tools/"helper.py").read_text(),"# helper2")
            self.assertEqual(Path(second["preflight"]).read_text(),"# checker")
            self.assertNotEqual(Path(second["preflight"]).parent,tools)


class TestAdmissionFailure(Base):
    def test_preflight_and_transport_failures_are_diagnosed_from_client_stdout(self):
        for message, expected in (("ADMISSION_TOOLS FAIL: ssh transfer failed", ("CRASH","admission-tools")),
                                  ("KIT_PREFLIGHT FAIL issues 1\n  - staged_tools: missing pins.json", ("STRUCTURAL","preflight"))):
            client=self.ap.parse_client_log(message+"\not-run: RAN on epyc2 (unit x): exit 1\nAP_RC=1\n")
            cls,kind,reason=self.ap.classify({},client)
            self.assertEqual((cls,kind),expected)
            self.assertIn(message.splitlines()[0],reason)


class TestRoutedChainGate(Base):
    def test_proof_oom_is_distinct_and_never_retries_route(self):
        j = {"id": "chain", "die": "s81", "type": "t", "chain_required": True, "started": time.time()}
        c = so("SIGNED", 3, 2, ())
        c["chain"] = {"started": time.time(), "verdict": "LEC_OOM", "reason": "24GB proof stopped; route retained"}
        self.ap.after_class = lambda st, j: None
        self.ap.submit = lambda *a, **kw: self.fail("proof OOM must not reroute")
        self.ap.finish({"jobs": {}}, j, c, {"exit": 137})
        self.assertEqual((j["status"], j["kind"]), ("CRASH", "proof-oom"))

    def test_new_proof_only_receipt_resumes_publication(self):
        j = {"id": "chain", "path": "/kit", "status": "DONE-CRASH", "kind": "proof-oom", "finished": 10}
        c = so("SIGNED", 3, 2, ())
        c["chain"]["started"] = 20
        seen = []
        self.ap.failure_resolutions = lambda: {}
        self.ap.hub_procs = lambda path: []
        self.ap.probe_job = lambda job: c
        self.ap.finish = lambda st, job, probe, client: seen.append(client)
        self.ap.retry_pending({"jobs": {"chain": j}})
        self.assertEqual(seen, [{"proof_only_resume": True}])

    def test_signed_record_without_current_equivalence_is_not_archived(self):
        for proof in (None, {"started": time.time(), "verdict": "PASS", "lec_verdict": "NOT EQUIVALENT", "lec_exit": 0},
                      {"started": 1, "verdict": "PASS", "lec_verdict": "EQUIVALENT", "lec_exit": 0}):
            j = {"id": "chain", "die": "s81", "type": "t", "chain_required": True, "started": time.time()}
            c = so("SIGNED", 3, 2, ())
            c["chain"] = proof
            self.ap.after_class = lambda st, j: None
            self.ap.finish({"jobs": {}}, j, c, {"exit": 0})
            self.assertEqual(j["status"], "STRUCTURAL")
            self.assertEqual(j["kind"], "routed-lec")
            self.assertEqual(c["signoff"]["verdict"], "SIGNED")


class TestMissingAdopted(Base):
    def test_missing_kit_is_orphan_not_running_or_physical_failure(self):
        (j,)=self.ap.parse_queue("\t".join(ROW)).values()
        j.update(status="RUNNING",adopted=True,history=[])
        st={"jobs":{j["id"]:j}}
        self.ap.hub_procs=lambda path:[]
        self.ap.probe_job=lambda job:None
        self.ap.rpy=lambda *a,**kw:{"exists":False}
        self.ap.finish=lambda *a:self.fail("missing inputs are not a physical verdict")
        self.ap.poll_adopted(st,j)
        self.assertEqual(j["status"],"ORPHAN")
        self.assertEqual(j["orphan_kind"],"kit-missing")
        count=len(j["history"])
        self.ap.poll_adopted(st,j)
        self.assertEqual(len(j["history"]),count)
        self.assertNotIn("cls",j)

    def test_live_client_is_preserved_without_missing_probe(self):
        (j,)=self.ap.parse_queue("\t".join(ROW)).values()
        j.update(status="RUNNING",adopted=True,history=[])
        self.ap.hub_procs=lambda path:[(123,99)]
        self.ap.probe_job=lambda job:self.fail("live adopted client must be left alone")
        self.ap.poll_adopted({"jobs":{j["id"]:j}},j)
        self.assertEqual(j["status"],"RUNNING")
        self.assertEqual(j["history"],[])


class TestAdoptedRunnerReceipt(Base):
    def check_receipt(self, start, end, rc, job_start):
        self.ap.hub_procs = lambda path: []
        self.ap.probe_job = lambda job: {"goal": "cts", "cts_odb": "4_cts.odb"}
        self.ap.rpy = lambda *args, **kwargs: {"exists": True, "busy": False, "log_age_s": 1000,
            "runner_exit": {"start": start, "end": end, "rc": rc, "path": "/own/image.txt"}}
        got = []
        self.ap.finish = lambda st, j, c, client: got.append(client)
        self.ap.poll_adopted({}, {"host": "intel2", "path": "/own", "started": self.ap.iso_epoch(job_start)})
        return got[0]

    def test_fresh_success_and_failure_keep_actual_runner_exit(self):
        for rc in (0, 8):
            client = self.check_receipt("2026-11-01T06:00:00-08:00", "2026-11-01T06:10:00-08:00", rc,
                                        "2026-11-01T05:59:00-08:00")
            self.assertEqual(client["exit"], rc)
            self.assertEqual(client["receipt"], "/own/image.txt")

    def test_stale_invocation_cannot_complete_new_adoption(self):
        client = self.check_receipt("2026-11-01T06:00:00-08:00", "2026-11-01T06:10:00-08:00", 0,
                                    "2026-11-01T06:15:00-08:00")
        self.assertNotIn("exit", client)

    def test_incomplete_or_reversed_receipt_is_not_success(self):
        for start, end in (("", ""), ("2026-11-01T06:10:00-08:00", "2026-11-01T06:00:00-08:00")):
            self.assertNotIn("exit", self.check_receipt(start, end, 0, "2026-11-01T05:59:00-08:00"))


class TestAppendWithdrawal(Base):
    def row(self):
        (r,) = self.ap.parse_queue("\t".join(ROW + ["route", "/srv/opentallas-scratch2/claude/run.sh", "8", "withdraw"])).values()
        r["geom_ref"] = "OWNER withdrawal: superseded source; preserve evidence"
        return r

    def test_waiting_withdrawal_is_idempotent_and_never_probes_or_launches(self):
        r=self.row();self.assertEqual(r["error"], "")
        j=dict(r, status="WAIT-CANARY", history=[])
        st={"jobs":{r["id"]:j}}
        self.ap.rpy=lambda *a,**k:self.fail("withdrawal must not probe a kit")
        self.ap.canary_wave_gate=lambda *a:self.fail("withdrawal cannot admit work")
        self.ap.admit_new(st,{r["id"]:r})
        self.assertEqual(j["status"],"WITHDRAWN")
        self.assertNotIn("unit",j)
        count=len(j["history"])
        self.ap.admit_new(st,{r["id"]:r})
        self.assertEqual(len(j["history"]),count)
        self.assertEqual(self.ap.geom_groups({r["id"]:r}),{})

    def test_running_or_terminal_verdicts_are_preserved(self):
        for status in ["RUNNING","ORPHAN","ARCHIVED","DONE-STRUCTURAL"]:
            with self.subTest(status=status):
                r=self.row();j=dict(r,status=status,unit="existing-unit",history=[])
                self.ap.admit_new({"jobs":{r["id"]:j}},{r["id"]:r})
                self.assertEqual(j["status"],status)
                self.assertEqual(j["unit"],"existing-unit")
                self.assertEqual(j["history"],[])
                self.assertIn("withdraw_requested",j)

    def test_requeue_reenters_geometry_gate(self):
        r=self.row();j=dict(r,status="WITHDRAWN",history=[])
        r.update(mode="submit",geom="REQ")
        self.ap.admit_new({"jobs":{r["id"]:j}},{r["id"]:r})
        self.assertEqual(j["status"],"WAIT-GEOM")


class TestClassify(Base):
    def test_signed(self):
        self.assertEqual(self.ap.classify(so("SIGNED", 1, 1, ()), {"exit": 0})[0], "SIGNED")

    def test_signed_needs_pg_census(self):
        # FLOW 10-26: a kit signoff.py without the PG census (or with open supply terminals) is not a sign-off
        for pg in (None, "NOT RUN", "FAIL"):
            self.assertEqual(self.ap.classify(so("SIGNED", 1, 1, (), pg=pg), {"exit": 0})[:2], ("STRUCTURAL", "pg-unbound"), pg)
        self.assertEqual(self.ap.classify(so("NOT SIGNED", 1, 1, ("pg",), pg="FAIL"), {})[0], "STRUCTURAL")

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
        self.assertEqual(self.ap.classify({"cells": 517001}, {"exit": 2})[1], "cell-cap")

    def test_cell_cap_after_infra_and_on_native_count(self):
        C = self.ap.classify
        # NOT RUN (disk floor) with an old placed kit of 522k placed cells is infra, not a cell-cap verdict
        self.assertEqual(C({"cells": 522340, "native_cells": 315910}, {"not_run": True, "msg": "NOT RUN"})[1], "infra-notrun")
        self.assertEqual(C({"cells": 522340}, {"not_run": True, "msg": "NOT RUN"})[1], "infra-notrun")
        # placed count incl. TAPCELL/endcaps above the cap, native count below: no cell-cap
        self.assertNotEqual(C({"cells": 522340, "native_cells": 315910}, {"exit": 2})[1], "cell-cap")
        self.assertEqual(C({"cells": 100, "native_cells": 517001}, {"exit": 2})[1], "cell-cap")

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

    def test_review_render_goes_direct(self):
        # KW-FIX-44 11-10 (COORD): review renders sat behind 30-50 heavy waiters for hours; they run --direct
        seen = []
        self.ap.rbash = lambda host, script, timeout=60: (0, "", "")
        self.ap.sh = lambda cmd, timeout=300, input=None: (0, "", "")
        self.ap.launch_unit = lambda unit, logfile, argv: seen.append(argv) or True
        self.ap.set_status = lambda st, j, s, why="": j.update(status=s)
        j = {"id": "f45a6c60e141", "host": "epyc7", "die": "hbm", "type": "q_spt1", "status": "STRUCTURAL", "src": "x",
             "path": "/srv/k", "signoff": {"odb": "/srv/k/run/6_final.odb", "path": "/srv/k/signoff", "odb_bytes": 3192478288}}
        self.ap.start_review({"jobs": {}}, j)
        (argv,) = seen
        pre = argv[:argv.index("--")]
        self.assertIn("--direct", pre)
        self.assertEqual(pre[pre.index("--mem") + 1], "34")           # the honest request stays
        self.assertEqual(pre[pre.index("--threads") + 1], "2")
        self.assertIn("--no-spill", pre)
        self.assertEqual(j["status"], "REVIEW-STRUCTURAL")
        os.environ["AP_REVIEW_DIRECT"] = "0"
        try:
            seen.clear()
            self.ap.start_review({"jobs": {}}, dict(j, status="STRUCTURAL"))
            self.assertNotIn("--direct", seen[0][:seen[0].index("--")])
        finally:
            os.environ.pop("AP_REVIEW_DIRECT", None)

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
                    "log_age_s": k.get("log_age_s"), "runner": "/srv/opentallas-scratch2/claude/s81/kits/run_kit.sh",
                    **{x: k[x] for x in ("signoff_missing", "signoff_goals", "gds_gap", "route_runs_finish", "flow_log_age_s") if x in k}}
        if code is self.ap.PROBE_CLASSIFY:
            return dict(k.get("classify", {}), last_log_mtime=k.get("mtime", 0))
        if code is self.ap.PROBE_DELETE:
            return {"deleted": [args["kit"] + "/run/results"], "errors": []}
        if code is self.ap.PROBE_ARCHIVE:
            self.archived = args
            return {"files": 12, "errors": [], "view": args["dest"] + "/view/" + str((args.get("view") or {}).get("module"))}
        if code is self.ap.PROBE_VIEW_READ:
            return k.get("view_read", {"module": "slice_station", "core": {"module": "slice_station",
                    "outline_um": [10.0, 8.0]}, "pins": {"pins": [{"name": "a", "x": 0.0, "y": 1.0, "layer": "M5"}]},
                    "files": {"slice_station.lef": "/k/x.lef", "slice_station_tt.lib": "/k/tt.lib",
                              "slice_station_ff.lib": "/k/ff.lib"}})
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
        self.ap.resolve_provenance = lambda src, flow="", die=None: {"src_commit": "0123456789ab" + "0" * 28,
                                                           "flow_tag": "flow-20261025-a"}

    def tick(self):
        self.ap.tick(type("A", (), {"dry_run": False})())
        return json.loads((Path(self.tmp.name) / "state.json").read_text())["jobs"]

    def finish_client(self, unit, text):
        self.f.active.discard(unit)
        st = json.loads((Path(self.tmp.name) / "state.json").read_text())
        j = [j for j in st["jobs"].values() if j.get("unit") == unit][0]
        Path(j["client_log"]).write_text(text)


class TestTick(TickBase):
    def test_commented_out_waiting_row_is_withdrawn_and_comes_back(self):
        self.ap.canary_wave_gate = lambda row: (False, "canary failed")
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-CANARY")
        self.queue(["# WITHDRAWN superseded: " + "\t".join(ROW)], ROW[:2] + [KIT + "x"] + ROW[3:4] + ["FAIL", "GR"] + ROW[6:])
        jobs = self.tick()
        self.assertEqual(jobs[j["id"]]["status"], "WITHDRAWN")
        self.assertIn("WITHDRAWN", (Path(self.tmp.name) / "log.txt").read_text())
        self.queue()                                       # unreadable/empty queue never withdraws
        self.assertEqual(self.tick()[j["id"]]["status"], "WITHDRAWN")
        self.queue(ROW)                                    # put back -> admitted again
        self.assertEqual(self.tick()[j["id"]]["status"], "WAIT-CANARY")
        self.assertEqual(self.f.launched, [])

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

    def test_chain_dispatch_is_self_contained_for_existing_data_host(self):
        self.queue(ROW)
        self.tick()
        argv=self.f.launched[0][1]
        command=argv[argv.index("--")+1:]
        self.assertEqual(command[:2],["python3","-c"])
        # The portable bootstrap now fetches the immutable chain on the chosen worker.
        self.assertIn("ADMISSION_TOOLS READY",command[2])
        self.assertIn("os.execv",command[2])
        compile(command[2],"<inline-chain>","exec")
        self.assertFalse(any(p.endswith("/signoff_chain.py") for p in argv))

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

    def test_near_miss_rendered_then_stopped_and_deleted(self):
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
        # AUTOPILOT-SIGNOFF-2: a chain job's failed run data is deleted once the review bundle exists (logs kept)
        self.assertTrue(any(c[1] == self.ap.PROBE_DELETE[:40] for c in self.f.calls))
        self.assertTrue(j["data_deleted"])
        self.tick()
        self.assertEqual(len(self.f.launched), 2)        # never retried

    def test_signed_view_published_with_canon_pins_and_gates(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": so("SIGNED", 3.0, 2.0, ()), "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        self.assertEqual(list(self.tick().values())[0]["status"], "ARCHIVED")
        v = self.f.archived["view"]
        sys.path.insert(0, str(HERE.parent / "die_plan"))
        import die_sta_related as DSR
        doc = {"pins": [{"name": "a", "x": 0.0, "y": 1.0, "layer": "M5"}]}
        self.assertEqual(v["provenance"]["kit"]["pins_canon_sha256"], DSR.canon_sha256(DSR.canon_pins(doc, [10.0, 8.0])))
        self.assertEqual(v["provenance"]["views_status"], "signoff")
        self.assertEqual(v["gates"]["routed_lec_all_shown"], True)
        self.assertEqual(v["gates"]["gates"]["routed_lec"], "PASS")

    def test_kit_pin_list_with_bus_bit_is_canonicalised(self):
        doc = self.ap.pins_doc([{"bus": "addr", "bit": 0, "layer": "M4", "x": 0.042, "y": 1.0}, {"bus": "ck", "bit": None,
                                "layer": "M5", "x": 1.0, "y": 0.0}])
        self.assertEqual([p["name"] for p in doc["pins"]], ["addr[0]", "ck"])
        self.assertEqual(len(self.ap.pins_canon(doc, [2.0, 2.0])), 64)

    def test_chain_without_all_shown_is_not_archived(self):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        c = so("SIGNED", 3.0, 2.0, ())
        c["chain"]["lec_all_shown"] = None
        self.f.kits[path] = {"classify": c, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        j = list(self.tick().values())[0]
        self.assertNotIn(j["status"], ("ARCHIVED", "SIGNED"))
        self.assertEqual(j["kind"], "routed-lec")

    def test_failure_notice_goes_to_lane_and_coord_queue(self):
        lines = []
        self.ap.coord_append = lambda rel, line: lines.append((rel, line))
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": {"FAIL_POSTCTS": "FF structural hold gate"}, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 1\nAP_RC=1\n")
        j = list(self.tick().values())[0]
        self.assertEqual(j["status"], "DONE-STRUCTURAL")
        self.assertEqual([r for r, _ in lines], ["lanes/S81.md", "lanes/COORD-REVIEW-QUEUE.md"])
        self.assertIn("FAILED", lines[0][1])
        self.assertTrue(j["data_deleted"])

    def test_job_from_earlier_chain_is_never_demoted_or_deleted(self):
        lines = []
        self.ap.coord_append = lambda rel, line: lines.append((rel, line))
        self.queue(ROW)
        self.tick()
        st = json.loads((Path(self.tmp.name) / "state.json").read_text())
        (j,) = st["jobs"].values()
        self.assertEqual(j["chain_version"], 2)
        j.pop("chain_version")                           # launched before AUTOPILOT-SIGNOFF-2
        (Path(self.tmp.name) / "state.json").write_text(json.dumps(st))
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        c = so("SIGNED", 3.0, 2.0, ())
        c["chain"].pop("lec_all_shown")
        self.f.kits[path] = {"classify": c, "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        j = list(self.tick().values())[0]
        self.assertEqual(j["status"], "ARCHIVED")
        self.assertEqual(self.f.archived["view"], {})
        self.assertEqual(lines, [])
        self.assertFalse(any(c[1] == self.ap.PROBE_DELETE[:40] for c in self.f.calls))

    def test_admission_priority_kv_qc_head_s81_hbm(self):
        rows = []
        for i, die in enumerate(("hbm", "s81", "s81_head", "qwen_compute", "kv")):
            rows.append([die, f"t{i}", KIT + f"_{i}"] + ROW[3:])
        self.queue(*rows)
        self.tick()
        order = [a[a.index("--dir") + 1].rsplit("_", 1)[1] for _, a in self.f.launched]
        self.assertEqual(order, ["4", "3", "2", "1", "0"])

    def test_infra_oom_resubmits_twice_with_more_mem_then_marks(self):
        # KW-FIX-46 11-12: MAX_OOM_RESUBMITS = 2 (hbm q_mcb_ne peaked > 75 GB: 48 and 72 both OOM)
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
        self.assertEqual(len(self.f.launched), 3)
        argv = self.f.launched[2][1]
        self.assertEqual(argv[argv.index("--mem") + 1], "54")
        self.finish_client(self.f.launched[2][0], "ot-run: RAN on epyc2: exit 2\nAP_RC=2\n")
        jobs = self.tick()
        self.assertEqual(len(self.f.launched), 3)        # two OOM resubmits only
        self.assertEqual(list(jobs.values())[0]["status"], "DONE-CRASH")
        self.assertIn("CRASH/infra-oom", (Path(self.tmp.name) / "structural.tsv").read_text())

    CANCEL = ("ot-run: interrupted (signal 15 from pid 111446 (python3 /home/ubuntu/.local/bin/ot-run --cancel "
              "s81/kits/slice_station__t5; parent 111442 (bash))); the command is STILL RUNNING on localhost "
              "(unit oth-ubuntu-1-2): NOT COMPLETED\nAP_RC=143\n")

    def _cancel_case(self, client_text, signals=None):
        self.queue(ROW)
        self.tick()
        path = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"
        self.f.kits[path] = {"classify": {}, "mtime": 9e9}
        if signals is not None:
            sl = Path(self.tmp.name) / "signals.log"
            sl.write_text(signals(path))
            self.ap.OT_RUN_SIGNALS = sl
        self.finish_client(self.f.launched[0][0], client_text)
        return self.tick()

    def test_explicit_cancel_in_client_log_is_cancelled_not_resubmitted(self):
        # FLOW-GEN-1 10-28: AP 5474a1c7a4cf was cancelled 07:44 and resubmitted at 48 GB as "infra-oom" (exit 143)
        jobs = self._cancel_case(self.CANCEL)
        (j,) = jobs.values()
        self.assertEqual((j["status"], j["kind"]), ("CANCELLED", "cancelled"))
        self.assertEqual(len(self.f.launched), 1)
        jobs = self.tick()                                   # stays cancelled on later ticks
        self.assertEqual((list(jobs.values())[0]["status"], len(self.f.launched)), ("CANCELLED", 1))

    def test_cancel_recorded_only_in_signals_log_is_cancelled(self):
        now = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        sig = lambda path: (f"{now} --cancel 'slice_station__t5' by pid 9 parent 8 (bash): [7]\n"
                            f"{now} signal 15 from pid 9 (python3 ot-run --cancel slice_station__t5; parent 8 (bash)) "
                            f"-> ot-run pid 7 host localhost tag t STARTED unit u dir {path}: bash run.sh\n")
        (j,) = self._cancel_case("ot-run: RAN on localhost (unit u): exit 143\nAP_RC=143\n", sig).values()
        self.assertEqual(j["status"], "CANCELLED")
        self.assertEqual(len(self.f.launched), 1)

    def test_old_or_other_dir_cancel_does_not_hide_an_oom(self):
        old = "2026-01-01T00:00:00-0800"
        sig = lambda path: (f"{old} signal 15 from pid 9 (python3 ot-run --cancel x; parent 8 (bash)) -> ot-run pid 7 "
                            f"host h tag t STARTED unit u dir {path}: bash\n"
                            f"{datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')} signal 15 from pid 9 "
                            f"(python3 ot-run --cancel y; parent 8 (bash)) -> ot-run pid 7 host h tag t STARTED unit u "
                            f"dir {path}_other: bash\n")
        self._cancel_case("ot-run: RAN on epyc2: exit 143\nAP_RC=143\n", sig)
        self.assertEqual(len(self.f.launched), 1)            # exit 143, no matching cancel, no OOM line: stopped, no retry

    def test_outside_stop_is_not_retried_real_oom_is(self):
        C = lambda c, cl: self.ap.classify(c, cl)[:2]
        for rc in (137, 143):
            self.assertEqual(C({}, {"exit": rc}), ("CRASH", "infra-stopped"))
            self.assertNotIn("infra-stopped", self.ap.INFRA_KINDS)
            self.assertEqual(C({"oom": "make: *** [x] Error 137"}, {"exit": rc}), ("CRASH", "infra-oom"))

    def test_watchdog_stop_names_the_sender_of_143(self):
        """KW-FIX-44 11-09: e1aed29fd563 (slw_su_l1, 09:22) ended 143 "stopped from outside"; the hub WATCHDOG had
        stopped its unit at 09:13 as SUPERSEDED.  The unit from the client log finds the STOP line."""
        txt = "ot-run: RAN on localhost (unit oth-ubuntu-3999380-1794228726): exit 143\nAP_RC=143\n"
        cl = self.ap.parse_client_log(txt)
        self.assertEqual((cl["ran_on"], cl["exit"], cl["unit"]), ("localhost", 143, "oth-ubuntu-3999380-1794228726"))
        self.assertNotIn("unit", self.ap.parse_client_log("ot-run: RAN on epyc2: exit 143\nAP_RC=143\n"))
        now = datetime.datetime.now()
        ts = lambda dt: dt.strftime("%Y-%m-%d %H:%M PST")
        log = Path(os.environ["AP_WATCHDOG_LOG"])
        log.write_text(f"{ts(now)} STOP intel2 None oth-ubuntu-1-2.scope [dpkit-x] idle 2m lane ? kit k rc 0 why SUPERSEDED: other\n"
                       f"{ts(now)} STOP intel2 None oth-ubuntu-3999380-1794228726.scope [dpkit-slw_su_l1-4001845] idle 2h53 "
                       f"lane ? kit k rc 0 why SUPERSEDED: qwen_compute/slw_su_l1@12 row efdb36e864@12: older than live "
                       f"attempt_14 on the current plan\n{ts(now)} TICK 0 ACT 0 FIX 1 STOP 25 REPORT\n")
        self.ap.WATCHDOG_LOG = log
        w = self.ap.watchdog_stop("oth-ubuntu-3999380-1794228726", time.time() - 3600)
        self.assertIn("dpkit-slw_su_l1", w)
        self.assertIsNone(self.ap.watchdog_stop("oth-ubuntu-3999380-1794228726", time.time() + 3600))  # older stop
        self.assertIsNone(self.ap.watchdog_stop("oth-ubuntu-9-9", 0))
        cls, kind, why = self.ap.classify({}, dict(cl, watchdog=w))
        self.assertEqual((cls, kind), ("CRASH", "watchdog-superseded"))
        self.assertIn("older than live attempt_14", why)
        self.assertNotIn(kind, self.ap.INFRA_KINDS)                                # no retry, as before
        old = w.split(" why ")[0]                                                  # a line from before this change
        self.assertEqual(self.ap.classify({}, dict(cl, watchdog=old))[1], "watchdog-stopped")
        self.assertEqual(self.ap.classify({}, cl)[1], "infra-stopped")             # no STOP line: unchanged

    def test_signoff_bundle_gap_rejected_before_route(self):
        self.f.kits["/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"] = {"signoff_missing": ["pair_skew.tcl"]}
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "REJECTED")
        self.assertIn("pair_skew.tcl", j["history"][-1][2])
        self.assertEqual(self.f.launched, [])

    def test_goal_follows_runner_signoff_contract(self):
        self.f.kits["/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"] = {"signoff_goals": ["finish", "post"]}
        self.queue(ROW + ["route"])
        self.tick()
        argv = self.f.launched[0][1]
        self.assertEqual(argv[argv.index("--") + 7], "finish")

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


class TestAdmitAfterWave(TickBase):
    """FLOW-TIME-1 11-07: a row the wave step enqueues is admitted in the same tick"""

    def wave_enqueues(self, *rows):
        self.ap.KW = type("KW", (), {"step": staticmethod(lambda AP: self.queue(*rows))})
        self.addCleanup(setattr, self.ap, "KW", self.real_kw)

    def setUp(self):
        super().setUp()
        self.real_kw = self.ap.KW
        os.environ.pop("AP_ADMIT_AFTER_WAVE", None)
        self.addCleanup(os.environ.pop, "AP_ADMIT_AFTER_WAVE", None)

    def test_row_enqueued_by_the_wave_submits_in_the_same_tick(self):
        self.queue()
        self.wave_enqueues(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertEqual(len(self.f.launched), 1)

    def test_off_switch_waits_for_the_next_tick(self):
        os.environ["AP_ADMIT_AFTER_WAVE"] = "0"
        self.queue()
        self.wave_enqueues(ROW)
        self.assertEqual(self.tick(), {})
        self.assertEqual(self.f.launched, [])
        self.assertEqual(len(self.tick()), 1)
        self.assertEqual(len(self.f.launched), 1)

    def test_all_gates_still_apply(self):
        self.ap.canary_wave_gate = lambda row: (False, "canary failed")
        self.queue()
        self.wave_enqueues(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-CANARY")
        self.assertEqual(self.f.launched, [])
        self.ap.canary_wave_gate = lambda row: (True, "ok")
        self.f.kits[ROW[2].split(":")[-1]] = {"busy": True}
        self.wave_enqueues(ROW)                            # held row is re-judged by the normal pass only
        calls = len(self.f.calls)
        self.tick()
        self.assertEqual(len([c for c in self.f.calls[calls:] if c[1] == self.ap.PROBE_KIT[:40]]), 1)
        self.assertEqual(self.f.launched, [])

    def test_held_row_is_not_probed_twice(self):
        self.f.kits[ROW[2].split(":")[-1]] = {"busy": True}
        self.queue(ROW)
        self.wave_enqueues(ROW)
        self.tick()
        self.assertEqual(len([c for c in self.f.calls if c[1] == self.ap.PROBE_KIT[:40]]), 1)

    def test_shared_submit_budget(self):
        rows = lambda n: [ROW[:1] + [f"slice_station__t{i}", KIT.replace("t5", f"t{i}")] + ROW[3:] for i in range(n)]
        self.ap.MAX_SUBMIT_PER_TICK = 2
        self.addCleanup(setattr, self.ap, "MAX_SUBMIT_PER_TICK", 12)
        self.queue(*rows(1))
        self.wave_enqueues(*rows(5))
        self.tick()
        self.assertEqual(len(self.f.launched), 2)

    def test_a_queue_row_gone_after_the_wave_is_not_withdrawn_by_this_pass(self):
        self.ap.canary_wave_gate = lambda row: (False, "canary failed")
        self.queue(ROW)
        other = ROW[:1] + ["slice_station__t6", KIT.replace("t5", "t6")] + ROW[3:]
        self.wave_enqueues(other)
        jobs = self.tick()
        self.assertEqual(sorted(j["status"] for j in jobs.values()), ["WAIT-CANARY", "WAIT-CANARY"])


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

    def running_on_pass(self):
        self.queue(self.REQ_ROW)
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        return j

    def gaps(self):
        return (Path(self.tmp.name) / "LOOP-GAPS.txt").read_text()

    def test_hand_withdrawn_queue_fail_is_not_a_geom_fail_after_submit(self):
        """2026-10-25 e0cca96daff3: queue line 389 'FAIL<TAB>WITHDRAWN obsolete PROTO 05:00 recipe; row e0cca96daff3;
        ... existing live job preserved' fired 'line 389 geom FAIL' though GEOM-REVIEW never failed t29"""
        self.running_on_pass()
        withdrawn = ROW[:4] + ["FAIL", "WITHDRAWN obsolete PROTO 05:00 recipe; existing live job preserved"] + ROW[6:]
        self.queue(self.REQ_ROW, withdrawn)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertNotIn("WARN GEOM-FAIL-AFTER-SUBMIT", self.log())
        self.assertNotIn("GEOM-FAIL-AFTER-SUBMIT", self.gaps())
        # a PASS-COND list naming the type is not a FAIL either
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS\n"
                  f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] Verdicts below.\n  PASS-COND (route via autopilot):\n"
                  f"    t7, slice_station__t5, t29\n  t8_m0 is NOT passed: reset hop 448 > 405.\n")
        self.queue(self.REQ_ROW)
        self.tick()
        self.assertNotIn("WARN GEOM-FAIL-AFTER-SUBMIT", self.log())

    def test_stale_hand_fail_alert_is_dropped(self):
        j = self.running_on_pass()
        st = json.loads((Path(self.tmp.name) / "state.json").read_text())
        st["jobs"][j["id"]].update(geom_fail_alert="line 389 geom FAIL", geom_fail_alert_t=time.time() - 600)
        (Path(self.tmp.name) / "state.json").write_text(json.dumps(st))
        self.queue(self.REQ_ROW, ROW[:4] + ["FAIL", "WITHDRAWN row; existing live job preserved"] + ROW[6:])
        (j,) = self.tick().values()
        self.assertNotIn("geom_fail_alert", j)
        self.assertIn("CLEAR GEOM-FAIL-AFTER-SUBMIT", self.log())
        self.assertNotIn("GEOM-FAIL-AFTER-SUBMIT " + j["id"], self.gaps())

    def fail_alert(self):
        j = self.running_on_pass()
        self.geom(f"{ts(60)} LANE: {self.REQ}{ts(30)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5: PASS\n"
                  f"{ts(5)} GEOM-REVIEW: REPLY [PROTO-KITS] slice_station__t5 corrected: FAIL\n")
        self.tick()
        self.assertIn("GEOM-FAIL-AFTER-SUBMIT " + j["id"], self.gaps())
        return j

    def test_coord_keep_line_clears_the_gap(self):
        j = self.fail_alert()
        q = Path(self.tmp.name) / "coord" / "lanes" / "COORD-REVIEW-QUEUE.md"
        later = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 120))
        q.write_text(f"[COORD {later} PDT] GEOM-FAIL-AFTER-SUBMIT {j['id']} slice_station__t5: KEEP. parser misread\n")
        self.tick()
        self.assertNotIn("GEOM-FAIL-AFTER-SUBMIT " + j["id"], self.gaps())

    def test_old_coord_keep_does_not_clear_a_newer_alert(self):
        j = self.fail_alert()
        q = Path(self.tmp.name) / "coord" / "lanes" / "COORD-REVIEW-QUEUE.md"
        q.write_text(f"[COORD {ts(240)}] GEOM-FAIL-AFTER-SUBMIT {j['id']} x: KEEP\n")
        self.tick()
        self.assertIn("GEOM-FAIL-AFTER-SUBMIT " + j["id"], self.gaps())

    def test_resolved_tsv_row_clears_the_gap(self):
        j = self.fail_alert()
        (Path(self.tmp.name) / "coord" / "autopilot").mkdir(exist_ok=True)
        (Path(self.tmp.name) / "coord" / "autopilot" / "resolved.tsv").write_text(
            f"GEOM-FAIL-AFTER-SUBMIT {j['id']}\t\tKEEP\tslice_station__t5\tCOORD\tnow\tCOORD ruled keep\n")
        self.tick()
        self.assertNotIn("GEOM-FAIL-AFTER-SUBMIT " + j["id"], self.gaps())


class TestProbeKitRouted(unittest.TestCase):
    """2026-10-25: results/.../base/5_hold_batch_*.odb (GRT hold step checkpoints) made the autopilot REJECT placed kits
    as 'already routed'; only real route outputs count"""

    def probe(self, names):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "run" / "results" / "asap7" / "x" / "base"
            b.mkdir(parents=True)
            (Path(d) / "config.mk").write_text("")
            for n in names:
                (b / n).write_text("")
            import autopilot as ap
            o = subprocess.run([sys.executable, "-c", ap.PROBE_KIT, json.dumps({"kit": d, "runner": ""})],
                               capture_output=True, text=True, env={"PATH": ""}, timeout=60).stdout
            return json.loads(o.split("AP_JSON ", 1)[1])["routed"]

    def test_hold_batches_and_grt_are_not_routed(self):
        self.assertEqual(self.probe(["2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb",
                                     "5_hold_batch_0.odb", "5_hold_batch_12.odb"]), [])

    def test_route_outputs_are_routed(self):
        self.assertEqual(self.probe(["5_1_grt.odb", "5_hold_batch_1.odb", "5_2_route.odb", "5_3_fillcell.odb",
                                     "6_1_fill.odb", "6_final.odb"]),
                         ["5_2_route.odb", "5_3_fillcell.odb", "6_1_fill.odb", "6_final.odb"])
        self.assertEqual(self.probe(["5_route.odb"]), ["5_route.odb"])


class TestProofOnly(unittest.TestCase):
    """FLOW-TIME-1 11-07: a kit whose only live container is its pre-route LEC is not a busy flow"""
    OWNER = "dpkit-t-1"

    def probe(self, names, files=None, rc=0):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            kit = Path(d) / "kit"
            (kit / "physical_completion").mkdir(parents=True)
            base = {"config.mk": "", "lec_async.owner": self.OWNER, "lec_async.ready": "1\ncmd", "lec_async.identity": "abc",
                    "lec_async.sh": "echo LEC_ASYNC reuse proof", f"physical_completion/{self.OWNER}.json": json.dumps({"rc": rc})}
            base.update(files or {})
            for n, t in base.items():
                if t is not None:
                    (kit / n).write_text(t)
            bin_ = Path(d) / "bin"
            bin_.mkdir()
            info = [{"Name": "/" + n, "State": {"StartedAt": "x"}, "Mounts": [{"Source": str(kit)}]} for n in names]
            (Path(d) / "inspect.json").write_text(json.dumps(info))
            (bin_ / "docker").write_text("#!/bin/sh\nif [ \"$1\" = ps ]; then echo id1; else cat %s/inspect.json; fi\n" % d)
            (bin_ / "docker").chmod(0o755)
            import autopilot as ap
            o = subprocess.run([sys.executable, "-c", ap.PROBE_KIT, json.dumps({"kit": str(kit), "runner": ""})],
                               capture_output=True, text=True, env={"PATH": f"{bin_}:/bin:/usr/bin"}, timeout=60).stdout
            return json.loads(o.split("AP_JSON ", 1)[1])

    def test_lec_unit_alone(self):
        p = self.probe([self.OWNER + "-lec"])
        self.assertIs(p["busy"], True)
        self.assertIs(p["proof_only"], True)

    def test_exec_form_owner_waiting_after_published_place(self):
        self.assertIs(self.probe([self.OWNER])["proof_only"], True)

    def test_owner_still_running_its_flow(self):
        self.assertIs(self.probe([self.OWNER], {f"physical_completion/{self.OWNER}.json": None})["proof_only"], False)

    def test_failed_phase_or_other_container(self):
        self.assertIs(self.probe([self.OWNER], rc=1)["proof_only"], False)
        self.assertIs(self.probe([self.OWNER + "-lec", "dpkit-t-2"])["proof_only"], False)

    def test_no_reuse_path_in_kit_or_verdict_or_stop(self):
        lec = [self.OWNER + "-lec"]
        self.assertIs(self.probe(lec, {"lec_async.sh": "old"})["proof_only"], False)
        self.assertIs(self.probe(lec, {"lec_async.ready": None})["proof_only"], False)
        self.assertIs(self.probe(lec, {"lec_async.identity": None})["proof_only"], False)
        self.assertIs(self.probe(lec, {"lec_async.done": ""})["proof_only"], False)
        self.assertIs(self.probe(lec, {"lec_async.rc": "1"})["proof_only"], False)
        self.assertIs(self.probe(lec, {"lec_async.stop": ""})["proof_only"], False)


class TestRouteBesideProof(TickBase):
    def setUp(self):
        super().setUp()
        self.addCleanup(os.environ.pop, "AP_ROUTE_BESIDE_PROOF", None)
        real = self.f.rpy

        def rpy(host, code, args, timeout=600):
            p = real(host, code, args, timeout)
            if code is self.ap.PROBE_KIT:
                p.update(busy=True, proof_only=self.proof_only)
            return p
        self.ap.rpy = rpy

    def test_only_the_proof_alive_submits(self):
        self.proof_only = True
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertIn("BESIDE-PROOF", (Path(self.tmp.name) / "log.txt").read_text())

    def test_any_other_container_holds(self):
        self.proof_only = False
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])

    def test_off_switch_holds(self):
        os.environ["AP_ROUTE_BESIDE_PROOF"] = "0"
        self.proof_only = True
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])

    def test_recent_logs_still_hold(self):
        self.proof_only = True
        self.f.kits[ROW[2].split(":")[-1]] = {"log_age_s": 60}
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])

    # KW-FIX-30 11-07: on real ticks the kit's PLACE client sits on the hub in lec_async.sh finish and the running
    # proof keeps K/lec*.log fresh, so BESIDE-PROOF never fired (0 lines 10:59-13:2x, 31 rows "kit busy")
    def test_own_place_client_on_the_hub_does_not_hold(self):
        self.proof_only = True
        self.ap.hub_procs = lambda path: [(4242, 3000)]
        self.ap.place_client = lambda pid, path: pid == 4242
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertIn("BESIDE-PROOF", (Path(self.tmp.name) / "log.txt").read_text())

    def test_other_hub_process_holds(self):
        self.proof_only = True
        self.ap.hub_procs = lambda path: [(4242, 3000), (4243, 10)]
        self.ap.place_client = lambda pid, path: pid == 4242
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])

    def test_place_client_holds_without_proof_only(self):
        self.proof_only = False
        self.ap.hub_procs = lambda path: [(4242, 3000)]
        self.ap.place_client = lambda pid, path: True
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])

    def test_lec_logs_do_not_hold_beside_proof(self):
        self.proof_only = True
        self.f.kits[ROW[2].split(":")[-1]] = {"log_age_s": 60, "flow_log_age_s": 5000}
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")

    def test_fresh_flow_log_still_holds(self):
        self.proof_only = True
        self.f.kits[ROW[2].split(":")[-1]] = {"log_age_s": 60, "flow_log_age_s": 60}
        self.queue(ROW)
        self.tick()
        self.assertEqual(self.f.launched, [])


class TestProbeBesideProofRealFixture(unittest.TestCase):
    """KW-FIX-30: the real PROBE_KIT code on a kit laid out as t12 a2 was at 13:1x (place receipt rc 0, ready +
    identity, watcher alive, its own -lec unit still waiting in ot-heavy so NO container), and the real place_client
    on a real process command line"""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import autopilot
        self.ap = autopilot
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.K = t / "gen" / "ot_s81sl_leaf__t12"
        (self.K / "physical_completion").mkdir(parents=True)
        (self.K / "config.mk").write_text("export DESIGN_NAME = x\n")
        (self.K / "lec_async.sh").write_text("# echo LEC_ASYNC reuse proof\n")
        (self.K / "lec_async.owner").write_text("dpkit-ot_s81sl_leaf__t12-2639243\n")
        (self.K / "lec_async.ready").write_text("1\npython3 -I /work/lec.py /work\n")
        (self.K / "lec_async.identity").write_text("abc\n")
        (self.K / "lec_async.pid").write_text(str(os.getpid()) + "\n")
        (self.K / "physical_completion" / "dpkit-ot_s81sl_leaf__t12-2639243.json").write_text('{"goal": "place", "rc": 0}')
        (self.K / "lec_async.log").write_text("waiting\n")
        old = time.time() - 4000
        os.utime(self.K / "config.mk", (old, old))
        bin_ = t / "bin"
        bin_.mkdir()
        (bin_ / "docker").write_text("#!/bin/sh\nexit 0\n")          # no container at all on this host
        (bin_ / "docker").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bin_}:{os.environ.get('PATH', '')}")

    def probe(self):
        import subprocess
        out = subprocess.run([sys.executable, "-I", "-", json.dumps({"kit": str(self.K), "runner": ""})],
                             input=self.ap.PROBE_KIT, capture_output=True, text=True, env=self.env, timeout=120).stdout
        line = [x for x in out.splitlines() if x.startswith("AP_JSON ")][-1]
        return json.loads(line[8:])

    def test_queued_proof_is_proof_only(self):
        p = self.probe()
        self.assertTrue(p["proof_only"])
        self.assertIs(p["busy"], False)
        self.assertLess(p["log_age_s"], 900)            # lec_async.log is fresh ...
        self.assertIsNone(p["flow_log_age_s"])          # ... but no flow log is

    def test_dead_watcher_or_no_receipt_or_done_is_not(self):
        (self.K / "lec_async.pid").write_text("999999999\n")
        self.assertFalse(self.probe()["proof_only"])
        (self.K / "lec_async.pid").write_text(str(os.getpid()) + "\n")
        (self.K / "physical_completion" / "dpkit-ot_s81sl_leaf__t12-2639243.json").write_text('{"goal": "place", "rc": 1}')
        self.assertFalse(self.probe()["proof_only"])
        (self.K / "physical_completion" / "dpkit-ot_s81sl_leaf__t12-2639243.json").write_text('{"goal": "place", "rc": 0}')
        (self.K / "lec_async.done").write_text("")
        self.assertFalse(self.probe()["proof_only"])

    def test_place_client_reads_the_real_command_line(self):
        import subprocess
        k = str(self.K)
        pl = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--", "bash", "-c",
                               f"bash {k.rsplit('/', 1)[0]}/run_kit.sh {k} place 48 8"])
        rt = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--", "runner.sh",
                               f"{k.rsplit('/', 1)[0]}/run_kit.sh", k, "route", "48", "8"])
        try:
            time.sleep(0.3)
            self.assertTrue(self.ap.place_client(pl.pid, k))
            self.assertFalse(self.ap.place_client(rt.pid, k))
            self.assertFalse(self.ap.place_client(pl.pid, k + "_other"))
        finally:
            pl.kill(); rt.kill(); pl.wait(); rt.wait()


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
        for d, P in (("s81", s81), ("s81_head", head), ("qwen_compute", qc), ("qwen_kvsys", kv)):
            (repo / "physical/die_plan" / d).mkdir(parents=True)
            (repo / "physical/die_plan" / d / "die_plan.json").write_text(json.dumps(P))
        # HBM plan of record d44f ships gzipped (AUTOBUILD-PIPE-2: ownership reads die_plan.json.gz)
        import gzip
        (repo / "physical/die_plan/hbm/plan_of_record/d44f").mkdir(parents=True)
        (repo / "physical/die_plan/hbm/plan_of_record/d44f/die_plan.json.gz").write_bytes(gzip.compress(json.dumps(hbm).encode()))
        (repo / "results/proto_1025/geom").mkdir(parents=True)
        (repo / "results/proto_1025/g2").mkdir(parents=True)
        (repo / "results/proto_1025/geom/d44f.json").write_text(json.dumps(
            {"plan": "x", "types": {"q_b000": {"verdict": "FAIL"}, "root": {"verdict": "PASS"}}}))
        (repo / "results/proto_1025/g2/res_qwen_kvsys.json").write_text(json.dumps(
            {"kv3_hg": {"classify": {"cls": "STRUCTURAL", "why": "GRT ov 5000"}}, "kv3_hg_v2": {"classify": {"cls": "CLEAN"}}}))
        (p / "release_cache.json").write_text(json.dumps({"provenance_rule": "v1", "plans": {"s81": {"signed_types": {"slice_station__t7": ["x"]},
                                                                            "signed_cores": {}}},
                                                          "signed_records": [{"name": "kr_dsdv_gunit_l1_lfp", "top": None,
                                                                              "path": "/a/signoff.json", "scan_host": "epyc1",
                                                                              "versioned": True, "src_commit": "ab" * 20,
                                                                              "flow_tag": "flow-20261025-a"}]}))

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
                   "gen/d44f/part_root -- bash run.sh\n")
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
        cache = {"provenance_rule": "v1", "plans": {"hbm/plan_of_record/d44f": {"signed_types": {}, "signed_cores": {
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

    def test_generated_memory_macro_is_never_a_design_to_kit(self):
        import ownership as O
        rom = {"module": "ot_rom_4096x72_m8", "outline_um": [38.04, 62.952], "pins_file": "cores/rom.json",
               "lef": "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef"}
        core = {"module": "q_elem", "outline_um": [10, 10], "lef": "physical/s81_die_views/q/q_elem.lef"}
        plan = {"partition_types": {"col": {"module": "col_m", "hard_cores": [rom, dict(rom), core]}},
                "partitions": [{"type": "col"}, {"type": "col"}]}
        items = {it["item"]: it for it in O.plan_items("s81", plan, {"cores/rom.json": self.pins((0, 1), (2, 3))})}
        self.assertEqual(items["ot_rom_4096x72_m8"]["kind"], "macro")
        self.assertEqual(items["ot_rom_4096x72_m8"]["replicas"], 4)
        self.assertEqual(items["q_elem"]["kind"], "core")
        rows, gaps, head = O.build(dict(plans={"s81": plan}), now=time.time())
        st = {r["item"]: r for r in rows}
        self.assertEqual(st["ot_rom_4096x72_m8"]["state"], "GENERATED")
        self.assertEqual(st["ot_rom_4096x72_m8"]["default_owner"], "ROM-MACRO")
        self.assertEqual(st["q_elem"]["state"], "NEEDS-KIT")
        self.assertFalse(any("ot_rom_4096x72_m8" in str(g) for g in gaps))     # never an UNOWNED-ITEM gap
        self.assertTrue(any("generated macros 1 (placed 4)" in h for h in head))

    def test_retired_rows_leave_the_gap_list_and_default_is_unchanged(self):
        import ownership as O
        core = lambda m: {"module": m, "outline_um": [10, 10], "lef": f"physical/x/{m}.lef"}
        plan = {"partition_types": {"col": {"module": "col_m", "hard_cores": [
                    core("ot_hgi_coll_tkm_m_tp192__tile1"), core("ot_hgi_coll_tkm_m_tp192__tile2"), core("q_keep")]}},
                "partitions": [{"type": "col"}]}
        base, gaps0, _ = O.build(dict(plans={"hbm": plan}), now=time.time())
        self.assertNotIn("RETIRED", {r["state"] for r in base})                  # no file -> nothing retired
        self.assertEqual(O.parse_retired(""), {})
        ret = O.parse_retired("# die item reason\nhbm\tot_hgi_coll_tkm_m_tp192__tile*\tnot a hard core in planS2/planU2\n"
                              "bad line\n")
        rows, gaps, head = O.build(dict(plans={"hbm": plan}, retired=ret), now=time.time())
        st = {r["item"]: r for r in rows}
        self.assertEqual(st["ot_hgi_coll_tkm_m_tp192__tile1"]["state"], "RETIRED")
        self.assertIn("planS2", st["ot_hgi_coll_tkm_m_tp192__tile2"]["evidence"])
        self.assertEqual(st["q_keep"]["state"], "NEEDS-KIT")
        self.assertFalse(any("tile1" in str(g) for g in gaps))
        self.assertTrue(any("tile1" in str(g) for g in gaps0))
        self.assertTrue(any("RETIRED 2" in h for h in head))

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


class LateEcoProvenance(Base):
    # KW-ECO-1: an ECO'd sign-off names the loop in PROVENANCE (kind eco); FAIL reasons carry the ECO evidence
    def test_eco_provenance_only_on_pass(self):
        eco = {"verdict": "PASS", "base_routed_db": "/k/run/b/6_final.odb", "best": {"base": "/k/eco_1/i1/b"},
               "iterations": [{"n": 1, "commands": ["bash prd_mk.sh"]}], "flow": {"tools_sha256": "ab"}, "wall_s": 9}
        p = self.ap.eco_provenance({"chain": {"eco": eco}})
        self.assertEqual(p["kind"], "eco")
        self.assertEqual(p["eco"]["base_routed_db"], "/k/run/b/6_final.odb")
        self.assertEqual(p["eco"]["routed_db"], "/k/eco_1/i1/b")
        self.assertEqual(p["eco"]["iterations"][0]["commands"], ["bash prd_mk.sh"])
        self.assertEqual(self.ap.eco_provenance({"chain": {"eco": dict(eco, verdict="EXHAUSTED")}}), {})
        self.assertEqual(self.ap.eco_provenance({}), {})

    def test_late_eco_cfg_opt_out(self):
        self.assertTrue(self.ap.late_eco_on())
        (Path(self.tmp.name) / "kit_wave.json").write_text(json.dumps({"late_eco": False}))
        self.assertFalse(self.ap.late_eco_on())
        (Path(self.tmp.name) / "kit_wave.json").write_text(json.dumps({"late_eco": True, "enabled": True}))
        self.assertTrue(self.ap.late_eco_on())



class TestEvacNoResumeHost(Base):
    """KW-FIX-24 COORD 17:5x: a kit homed on a kit_wave.json no_resume_hosts host moves to the hub inside its unit"""

    def cfg(self, hosts):
        (Path(self.tmp.name) / "kit_wave.json").write_text(json.dumps({"no_resume_hosts": hosts}))

    def submit(self):
        (j,) = self.ap.parse_queue("\t".join(ROW)).values()
        j["id"] = "evac0001"
        seen = []
        self.ap.launch_unit = lambda unit, logfile, argv: seen.append(argv) or True
        self.ap.submit({"jobs": {}}, j)
        return j, seen[0]

    def test_submit_wraps_only_listed_host(self):
        j, argv = self.submit()
        self.assertNotEqual(argv[:2], ["bash", "-c"])
        self.assertNotIn("evac", j)
        self.cfg({"epyc2": 80})
        j, argv = self.submit()
        self.assertEqual(argv[:2], ["bash", "-c"])
        self.assertEqual(argv[3:5], ["ap-evac", "epyc2"])
        cut = argv.index("--", 7)
        self.assertEqual(argv[7:cut], [j["path"]])
        self.assertEqual(argv[cut + 1], self.ap.OT_RUN)
        self.assertEqual((j["evac"]["from"], j["evac"]["to"]), ("epyc2", self.ap.HUB_NAME))

    def test_apply_evac_rehomes_on_ok_marker_only(self):
        m1, m2 = Path(self.tmp.name) / "m1.json", Path(self.tmp.name) / "m2.json"
        m1.write_text(json.dumps({"ok": True, "from": "epyc6", "bytes": 3e9}))
        m2.write_text(json.dumps({"ok": False, "why": "hub disk"}))
        st = {"jobs": {
            "a": {"id": "a", "host": "epyc6", "kit": "epyc6:/srv/x/a", "path": "/srv/x/a", "probe": "epyc6",
                  "evac": {"from": "epyc6", "mark": str(m1), "t": time.time()}},
            "b": {"id": "b", "host": "epyc6", "kit": "epyc6:/srv/x/b", "path": "/srv/x/b",
                  "evac": {"from": "epyc6", "mark": str(m2), "t": time.time()}},
            "c": {"id": "c", "host": "epyc6", "kit": "epyc6:/srv/x/c", "path": "/srv/x/c",
                  "evac": {"from": "epyc6", "mark": str(Path(self.tmp.name) / "none.json"), "t": time.time()}}}}
        self.assertEqual(self.ap.apply_evac(st), 1)
        a, b, c = st["jobs"]["a"], st["jobs"]["b"], st["jobs"]["c"]
        self.assertEqual((a["host"], a["kit"], a["host_before_evac"]), (self.ap.HUB_NAME, f"{self.ap.HUB_NAME}:/srv/x/a", "epyc6"))
        self.assertNotIn("probe", a)
        self.assertEqual(b["host"], "epyc6")
        self.assertTrue(b["evac"]["applied"].startswith("failed"))
        self.assertNotIn("applied", c["evac"])          # unit still copying: retried next tick
        self.assertEqual(self.ap.apply_evac(st), 0)     # applied once

    def run_sh(self, roots, extra_env=None):
        import subprocess
        t = Path(self.tmp.name)
        fake = t / "fakessh"
        fake.write_text("#!/bin/bash\nwhile [[ $1 == -* ]]; do if [[ $1 == -o ]]; then shift 2; else shift; fi; done\n"
                        "shift\nexec bash -c \"$*\"\n")
        fake.chmod(0o755)
        mark = t / "mark.json"
        env = dict(os.environ, EVAC_SSH=str(fake), EVAC_DST_PREFIX=str(t / "dst"), EVAC_LANE=str(t / "src"))
        env.update(extra_env or {})
        r = subprocess.run(["bash", "-c", self.ap.EVAC_SH, "ap-evac", "epyc6", str(mark), "0"] + roots + ["--", "echo", "RAN"],
                           capture_output=True, text=True, env=env, timeout=120)
        return r, json.loads(mark.read_text())

    def tree(self):
        t = Path(self.tmp.name)
        k = t / "src/claude/w/items/k/gen/k"
        (k / "run/results").mkdir(parents=True)
        (k / "run/results/4_cts.odb").write_bytes(b"x" * 5000)
        (k / "config.mk").write_text("A=1\n")
        os.link(k / "config.mk", k / "run/hard.mk")
        runner = t / "src/claude/w/items/k/gen/run_kit.sh"
        runner.write_text("#!/bin/sh\n")
        return k, runner

    def test_evac_sh_moves_verifies_and_removes_source(self):
        k, runner = self.tree()
        r, m = self.run_sh([str(k), str(runner)])
        self.assertEqual(r.stdout.strip(), "RAN", r.stderr)
        self.assertTrue(m["ok"], m)
        d = Path(self.tmp.name) / "dst" / str(k).lstrip("/")
        self.assertEqual((d / "run/results/4_cts.odb").stat().st_size, 5000)
        self.assertEqual((d / "config.mk").stat().st_ino, (d / "run/hard.mk").stat().st_ino)   # -H kept hardlinks
        self.assertTrue((Path(self.tmp.name) / "dst" / str(runner).lstrip("/")).is_file())
        self.assertFalse(k.exists())
        self.assertFalse(runner.exists())

    def test_evac_sh_refuses_and_keeps_source(self):
        k, runner = self.tree()
        d = Path(self.tmp.name) / "dst" / str(k).lstrip("/")
        d.mkdir(parents=True)
        r, m = self.run_sh([str(k)])
        self.assertEqual(r.stdout.strip(), "RAN")       # fail-open: the job still runs, as before
        self.assertFalse(m["ok"])
        self.assertIn("exists", m["why"])
        self.assertTrue((k / "config.mk").is_file())
        r, m = self.run_sh([str(k)], {"EVAC_LANE": "/nonexistent"})
        self.assertFalse(m["ok"])
        self.assertIn("outside", m["why"])
        self.assertTrue((k / "config.mk").is_file())

if __name__ == "__main__":
    unittest.main()


class TestCrashTriage1025(unittest.TestCase):
    """CRASH-TRIAGE 2026-10-25: signatures of the 48 DONE-CRASH rows"""

    def setUp(self):
        import autopilot
        self.ap = autopilot

    def classify_probe(self, runlog, files=None):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "run_route.log").write_text(runlog)
            for n, txt in (files or {}).items():
                (Path(d) / n).parent.mkdir(parents=True, exist_ok=True)
                (Path(d) / n).write_text(txt)
            o = subprocess.run([sys.executable, "-c", self.ap.PROBE_CLASSIFY, json.dumps({"kit": d, "goal": "route"})],
                               capture_output=True, text=True, env={"PATH": ""}, timeout=60).stdout
            return json.loads(o.split("AP_JSON ", 1)[1])

    def test_gate_fail_after_caught_tool_error_is_the_reported_stop(self):
        c = self.classify_probe("[ERROR RSZ-0060] Max buffer count reached.\nrepair continues\nPIN_AUDIT FAIL 4435/4435 extra 32\n")
        self.assertIn("PIN_AUDIT FAIL", c["orfs_error"])
        self.assertIn("RSZ-0060", c["orfs_errors"][0])
        c = self.classify_probe("PIN_AUDIT FAIL early\n[ERROR DRT-0255] stop\n")
        self.assertIn("DRT-0255", c["orfs_error"])

    def test_clock_source_exception_after_pass_is_infra_without_blind_retry(self):
        files = {
            "FAIL_POSTCTS": "legacy grt gate: TT global-routing insertion gate failed: PASS exit 1\n"
                              "FAIL_POSTCTS final GRT released TT/FF policy (grt_policy.json)\n",
            "postcts_gate_tt.json": json.dumps({"verdict": "PASS", "setup_wns_est_ps": 23.49}),
            "postcts_gate_TT.log": "Error: grt_policy_tt.tcl, 849 clock clk has no unique rise source insertion arrival\n",
        }
        c = self.classify_probe("", files)
        self.assertEqual(self.ap.classify(c, {"exit": 1})[:2], ("CRASH", "infra-clock-source"))
        self.assertNotIn("infra-clock-source", self.ap.INFRA_KINDS)
        # Missing/failed receipts and real data failures remain structural.
        for changes in (
                {"postcts_gate_tt.json": "{}"},
                {"postcts_gate_tt.json": json.dumps({"verdict": "FAIL"})},
                {"postcts_gate_TT.log": "Error: grt_policy_tt.tcl, 849 something else\n"},
                {"FAIL_POSTCTS": "G2 setup_tt failed before pair census: -203.45"},
                {"FAIL_POSTCTS": "FF structural hold gate: -315.56 ps"}):
            c = self.classify_probe("", dict(files, **changes))
            self.assertEqual(self.ap.classify(c, {"exit": 1})[:2], ("STRUCTURAL", "post-cts-hold"))

    def test_caught_hold_chunk_error_does_not_hide_terminal_route_error(self):
        c = self.classify_probe("[ERROR RSZ-0060] maximum buffer chunk reached\n"
                                "OT_HOLD_GATE PASS FF 4.39\n"
                                "[ERROR DRT-0255] No access point for mp_isl0_ck_i\n")
        self.assertIn("DRT-0255", c["orfs_error"])
        self.assertIn("RSZ-0060", c["orfs_errors"][0])
        self.assertIn("DRT-0255", self.ap.classify(c, {"exit": 2})[2])
        c = self.classify_probe("[ERROR RSZ-0060] maximum buffer count\n")
        self.assertIn("RSZ-0060", c["orfs_error"])

    def test_error_247_at_mem_cap_is_infra_oom(self):
        c = self.classify_probe("[INFO PSM-0040] All shapes on net VDD are connected.\n"
                                "make[1]: *** [Makefile:654: do-6_report] Error 247\nmake: *** [Makefile:672: do-finish] Error 2\n")
        self.assertEqual(self.ap.classify(c, {"exit": 2})[:2], ("CRASH", "infra-oom"))
        c = self.classify_probe("make[1]: *** [Makefile:589: do-5_2_route] Error 1\n")
        self.assertEqual(self.ap.classify(c, {"exit": 2})[:2], ("CRASH", "flow-error"))

    def test_printed_gate_fail_is_structural(self):
        for line in ("CORE_PREFLIGHT FAIL /work/x/1_2_yosys.v {'shared': 1716}",
                     "RP1_GATE FAIL: FF hold -2.65 < 0 -- stop before detailed route",
                     "SDC_LINT FAIL /work errors 1 liberty 16"):
            c = self.classify_probe("x\n" + line + "\n")
            self.assertEqual(self.ap.classify(c, {"exit": 1})[:2], ("STRUCTURAL", "gate"), line)
        c = self.classify_probe("SDC_LINT PASS\n")
        self.assertNotIn("gate_fail", c)

    def test_adopted_without_logs_is_infra_lost(self):
        self.assertEqual(self.ap.classify({"last_log": "", "runlog_tail": ""}, {})[:2], ("CRASH", "infra-lost"))

    def probe_kit(self, files):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            for n, txt in files.items():
                (Path(d) / n).write_text(txt)
            o = subprocess.run([sys.executable, "-c", self.ap.PROBE_KIT, json.dumps({"kit": d, "runner": ""})],
                               capture_output=True, text=True, env={"PATH": ""}, timeout=60).stdout
            return json.loads(o.split("AP_JSON ", 1)[1])

    def test_probe_kit_signoff_bundle_and_goals(self):
        so = 'x = HERE / "pair_skew.tcl"\ndef f():\n    import sdc_lint\n    import face_guard\n'
        hbm = ('if { [ "$GOAL" = finish ] || [ "$GOAL" = post ]; } && [ $((rc % 100)) = 0 ]; then\n  SO="$K/signoff"\n'
               '  python3 "$K/signoff.py" run --run-dir "$K/run"\nfi\n')
        p = self.probe_kit({"config.mk": "export ADDITIONAL_LEFS = /work/macros/a.lef\n", "signoff.py": so,
                            "sdc_lint.py": "", "run_kit_hbm.sh": hbm})
        self.assertEqual(p["signoff_missing"], ["face_guard.py", "pair_skew.tcl", "lec.py"])
        self.assertEqual(p["signoff_goals"], ["finish", "post"])
        self.assertTrue(p["gds_gap"])
        self.assertFalse(p["route_runs_finish"])

    def test_runner_goal(self):
        rg = self.ap.runner_goal
        self.assertEqual(rg("route", {"signoff_goals": ["finish", "post"]}), "finish")
        self.assertEqual(rg("finish", {"signoff_goals": ["finish", "route"], "gds_gap": True, "route_runs_finish": True}),
                         "route")
        self.assertEqual(rg("finish", {"signoff_goals": ["finish", "route"], "gds_gap": False}), "finish")
        self.assertEqual(rg("cts", {"signoff_goals": ["finish"]}), "cts")
        self.assertEqual(rg("route", {}), "route")


class TestPhysicalGoalReceipt(Base):
    def state(self):
        r = dict(schema="opentallas.physical_completion.v1",run_id="run2",goal="cts",started=1000.0,
                 ended=1010.0,rc=0,proof_id="proofhash",proof_owner="proofowner",proof_pid="123",
                 proof_scope="oth-original.scope",physical_id="physicalhash",path="/kit/physical_completion/run2.json",
                 checkpoint_current=True,checkpoint=dict(path="run/results/asap7/t/base/4_cts.odb",size=10,mtime_ns=12))
        p = dict(busy=True,active_containers=["proofowner"],physical_completions=[r],
                 physical_identity="physicalhash",physical_starts=[dict(r)],
                 async_proof=dict(identity="proofhash",owner="proofowner",done=False,rc=""))
        j = dict(id="j",host="intel2",path="/kit",goal="cts",started=999.0,status="RUNNING")
        return j,p

    def test_busy_proof_owner_does_not_block_fresh_diagnostic_result(self):
        j,p = self.state()
        self.ap.hub_procs = lambda path:[(123,8000)]
        self.ap.rpy = lambda *a,**kw:p
        self.ap.probe_job = lambda job:dict(goal="cts",cts_odb="4_cts.odb")
        seen=[]
        self.ap.finish = lambda st,job,c,client:seen.append(client)
        self.ap.poll_adopted({},j)
        self.assertEqual(seen[0]["exit"],0)
        self.assertTrue(seen[0]["physical_only"])
        self.assertTrue(j["proof_wait"]["pending"])
        self.assertEqual(j["proof_wait"]["scope"],"oth-original.scope")

    def test_route_and_finish_never_accept_physical_only_receipt(self):
        for goal in ("route","finish"):
            j,p = self.state();j["goal"]=goal
            self.assertIsNone(self.ap.physical_receipt(j,p))

    def test_stale_wrong_goal_hash_or_missing_proof_owner_are_refused(self):
        for change in ({"started":800.0},{"goal":"grt"},{"proof_id":"old"},{"physical_id":"old"}):
            j,p=self.state();p["physical_completions"][0].update(change)
            self.assertIsNone(self.ap.physical_receipt(j,p))
        j,p=self.state();p["physical_completions"][0]["checkpoint_current"]=False
        self.assertIsNone(self.ap.physical_receipt(j,p))
        j,p=self.state();p["active_containers"]=[]
        self.assertIsNone(self.ap.physical_receipt(j,p))
        j,p=self.state();p["physical_starts"].append(dict(run_id="newer",goal="cts",started=1015.0,
                                                       physical_id="physicalhash"))
        self.assertIsNone(self.ap.physical_receipt(j,p))

    def test_pending_proof_completion_is_collected_after_cts_done(self):
        j,p=self.state();j.update(status="CTS-DONE",proof_wait=dict(host="intel2",owner="proofowner",
            identity="proofhash",pending=True));p["async_proof"].update(done=True,rc="1")
        self.ap.rpy=lambda *a,**kw:p
        self.ap.poll_pending_proofs({"jobs":{"j":j}})
        self.assertFalse(j["proof_wait"]["pending"])
        self.assertEqual(j["proof_wait"]["rc"],"1")
        self.assertEqual(j["status"],"CTS-DONE")  # physical diagnostic never claimed SIGNED


    def test_fresh_incremental_rc_can_bind_an_unchanged_older_checkpoint(self):
        j,p=self.state()
        self.ap.rpy=lambda *a,**kw:p
        self.ap.probe_job=lambda job:dict(goal="cts") # old mtime was filtered by ordinary classifier
        seen=[]
        self.ap.finish=lambda st,job,c,client:seen.append((c,client))
        self.assertTrue(self.ap.poll_physical_completion({},j))
        self.assertEqual(seen[0][0]["cts_odb"],"/kit/run/results/asap7/t/base/4_cts.odb")
        self.assertEqual(seen[0][1]["exit"],0)


class SealedWatchdogStopTest(unittest.TestCase):
    """KW-FIX-46 11-12 (hbm PHY_NC 2731c12447d5): a WATCHDOG STOP of a container inside a sealed ot-job names the job dir"""

    def test_stop_line_found_by_sealed_job_dir(self):
        import autopilot as ap
        with tempfile.TemporaryDirectory() as td:
            wl = Path(td) / "WATCHDOG.log"
            wl.write_text("2026-11-12 13:13 PST STOP epyc4 GRT dpkit-PHY_NC-3468881 idle 6h18 lane ? kit epyc4:/srv/x/"
                          "ot-jobs/PHY_NC-route-aware-parakeet-3317157-1794474529/work rc 0 why hung 6h18\n")
            cl = Path(td) / "a1.log"
            cl.write_text("ot-job: SEALED /srv/x/ot-jobs/PHY_NC-route-aware-parakeet-3317157-1794474529: 3 inputs\n")
            old = ap.WATCHDOG_LOG
            ap.WATCHDOG_LOG = wl
            try:
                sj = ap.sealed_job_dir({"client_log": str(cl)})
                self.assertTrue(sj.endswith("/ot-jobs/PHY_NC-route-aware-parakeet-3317157-1794474529"))
                self.assertIsNotNone(ap.watchdog_stop(sj.rsplit("/", 1)[-1] + "/", 0))
                self.assertIsNone(ap.watchdog_stop("PHY_NC-route-aware-parakeet-3317157-17944745/", 0))
                self.assertIsNone(ap.watchdog_stop("oth-ubuntu-1-2", 0))
            finally:
                ap.WATCHDOG_LOG = old
