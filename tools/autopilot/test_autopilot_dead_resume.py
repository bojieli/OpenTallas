#!/usr/bin/env python3
"""KW-FIX-35-O 11-08: a client-less job with no process and no container on any fleet host for DEAD_IDLE_S is DEAD and
resumes its run dir at once; a job alive anywhere (an ot-run SPILL copy on another host) is never resumed, even when
the kit host's own logs are hours old (the 14 QC "orphans" of 11-08 07:19 ran on intel2/epyc4 spill copies)."""
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_autopilot import Base, ROW  # noqa: E402

KITPATH = "/srv/opentallas-scratch2/claude/s81/kits/slice_station__t5"


class DeadResume(Base):
    def job(self, log_text="ot-run: -> epyc5\n"):
        (j,) = self.ap.parse_queue("\t".join(ROW)).values()
        logf = Path(self.tmp.name) / "a1.log"
        logf.write_text(log_text)
        j.update(status="RUNNING", history=[], unit="ap-x-a1", client_log=str(logf), started=time.time() - 8 * 3600,
                 mem_gb=24, path=KITPATH, host="epyc2")
        self.st = {"jobs": {j["id"]: j}}
        self.ap.unit_active = lambda u: False
        self.ap.poll_physical_completion = lambda st, job: False
        self.ap.poll_pending_proofs = lambda st: None
        self.ap.signals_cancel = lambda job: None
        self.ap.wave_superseded = lambda job: ""
        self.ap.after_class = lambda st, job: None
        self.ap.released_cleanup = lambda: None
        self.ap.log = lambda m: None
        self.submits = []
        self.ap.submit = lambda st, job, note="": (self.submits.append(note), job.update(status="RUNNING"))
        # kit-host logs: 10 min old (inside ORPHAN_IDLE_S), so only the DEAD rule can resume it
        self.ap.probe_job = lambda job: {"kit": KITPATH, "exists": True, "last_log_mtime": time.time() - 600,
                                          "last_log": "4_1_cts.log", "runlog_tail": "...", "probe_host": "epyc2"}
        return j

    def test_kit_tail(self):
        self.assertEqual(self.ap.kit_tail("/srv/a/b/items/t5/attempt_3/gen/t5"), "t5/attempt_3/gen/t5")
        self.assertEqual(self.ap.kit_tail("/a/b"), "")

    def test_dead_30min_resumes_once_from_run_dir(self):
        j = self.job()
        self.ap.fleet_alive = lambda job, hosts=None: False
        self.ap.poll_running(self.st)                       # first sight: dead_since set, still ORPHAN
        self.assertEqual(j["status"], "ORPHAN")
        self.assertEqual(self.submits, [])
        j["dead_since"] -= self.ap.DEAD_IDLE_S + 1
        self.ap.poll_running(self.st)
        self.assertEqual(len(self.submits), 1)
        self.assertIn("DEAD 1/2", self.submits[0])
        self.assertIn("resumes the run dir", self.submits[0])
        self.assertEqual(j["kind"], "infra-dead")
        self.assertNotIn("dead_since", j)

    def test_alive_on_spill_host_never_resumed_even_with_old_kit_logs(self):
        j = self.job()
        self.ap.probe_job = lambda job: {"kit": KITPATH, "exists": True, "last_log_mtime": time.time() - 6 * 3600,
                                          "last_log": "3_5_place_dp.log", "probe_host": "epyc2"}
        self.ap.fleet_alive = lambda job, hosts=None: True
        self.ap.finish = lambda *a: self.fail("a job alive on another host must not be classified or resubmitted")
        self.ap.poll_running(self.st)
        self.assertEqual(j["status"], "ORPHAN")
        self.assertEqual(self.submits, [])

    def test_unknown_liveness_is_not_dead(self):
        j = self.job()
        self.ap.fleet_alive = lambda job, hosts=None: None
        for _ in range(2):
            self.ap.poll_running(self.st)
        self.assertEqual(j["status"], "ORPHAN")
        self.assertNotIn("dead_since", j)
        self.assertEqual(self.submits, [])

    def test_alive_again_clears_dead_clock(self):
        j = self.job()
        self.ap.fleet_alive = lambda job, hosts=None: False
        self.ap.poll_running(self.st)
        self.assertIn("dead_since", j)
        self.ap.fleet_alive = lambda job, hosts=None: True
        self.ap.poll_running(self.st)
        self.assertNotIn("dead_since", j)

    def test_not_completed_dead_resumes(self):
        j = self.job("ot-run: NOT COMPLETED on epyc4 (unit oth-1)\n")
        self.ap.fleet_alive = lambda job, hosts=None: False
        self.ap.poll_running(self.st)
        self.assertEqual(self.submits, [])
        j["dead_since"] -= self.ap.DEAD_IDLE_S + 1
        self.ap.poll_running(self.st)
        self.assertEqual(len(self.submits), 1)
        self.assertEqual(j["kind"], "infra-dead")

    def test_budget_exhausted_is_a_failure_row(self):
        j = self.job()
        j["dead_resumes"] = self.ap.MAX_DEAD_RESUME
        j["infra_retry"] = True
        self.ap.fleet_alive = lambda job, hosts=None: False
        self.ap.poll_running(self.st)
        j["dead_since"] -= self.ap.DEAD_IDLE_S + 1
        self.ap.poll_running(self.st)
        self.assertEqual(self.submits, [])
        self.assertEqual(j["status"], "CRASH")
        self.assertEqual(j["kind"], "infra-dead")

    def test_probe_finds_process_by_tail_and_skips_itself(self):
        tail = "kw35o_t/attempt_9/gen/kw35o_t"
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "/srv/x/" + tail])
        try:
            time.sleep(0.3)
            r = subprocess.run([sys.executable, "-I", "-", json.dumps({"tail": tail, "marker": "AP_PROBE_ALIVE"})],
                               input=self.ap.PROBE_ALIVE, capture_output=True, text=True, timeout=120)
            out = json.loads([l for l in r.stdout.splitlines() if l.startswith("AP_JSON ")][-1][8:])
            self.assertEqual(out["procs"], [str(p.pid)])
        finally:
            p.kill()
            p.wait()
        r = subprocess.run([sys.executable, "-I", "-", json.dumps({"tail": tail, "marker": "AP_PROBE_ALIVE"})],
                           input=self.ap.PROBE_ALIVE, capture_output=True, text=True, timeout=120)
        out = json.loads([l for l in r.stdout.splitlines() if l.startswith("AP_JSON ")][-1][8:])
        self.assertEqual(out["procs"], [])

    def test_fleet_alive_unknown_when_a_host_fails(self):
        j = self.job()
        answers = {"h1": {"procs": [], "containers": []}, "h2": {"error": "probe rc 255"}}
        self.ap.rpy = lambda h, code, args, timeout=0: answers[h]
        self.assertIsNone(self.ap.fleet_alive(j, hosts=("h1", "h2")))
        answers["h2"] = {"procs": [], "containers": []}
        self.assertIs(self.ap.fleet_alive(j, hosts=("h1", "h2")), False)
        answers["h2"] = {"procs": [], "containers": ["dpkit-slice_station__t5-1"]}
        self.assertIs(self.ap.fleet_alive(j, hosts=("h1", "h2")), True)
        self.assertEqual(j["alive_on"]["host"], "h2")


if __name__ == "__main__":
    unittest.main()
