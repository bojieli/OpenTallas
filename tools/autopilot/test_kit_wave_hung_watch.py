#!/usr/bin/env python3
"""KIT-OPS-1 11-13 HUNG-WATCH: a silent but alive row is cancelled (CANCELLED class HUNG) only when both its stage logs and the CPU
time of its processes stopped growing for hung_watch_min; any CPU progress keeps it report-only."""
import glob
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

ROOT = "/srv/kw/a"


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, cpu=500.0, log=0.0, containers=("dpkit-a-1",), probe_rc=0, alive=True):
        self.active, self.cmds, self.logs = {"u-a"}, [], []
        self.cpu, self.log_t, self.containers, self.probe_rc, self.alive = cpu, log, list(containers), probe_rc, alive

    def unit_active(self, u):
        return u in self.active

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        if input and "# HUNG_PROBE" in input:
            host = cmd[cmd.index("ControlPath=none") + 1] if "ControlPath=none" in cmd else "intel2"
            got = {ROOT: {"log": self.log_t, "cpu": self.cpu if host == "epyc9" else 0.5, "pids": 3,
                          "containers": self.containers if host == "epyc9" else []}}
            return self.probe_rc, json.dumps({"HUNG_PROBE": got}) + "\n", ""
        if input and "me = str(os.getpid())" in input:
            return 0, json.dumps({ROOT: ["4242"]} if self.alive else {}) + "\n", ""
        return 0, '{"containers": [], "scopes": []}\n', ""

    def log(self, m):
        self.logs.append(m)


CFG = {"dies": {"s81": {"event": "e", "hosts": ["epyc9"]}}, "infra_attempts": 3}


def silent_rec(d, silent_min):
    jd = Path(d) / "a"
    jd.mkdir(exist_ok=True)
    (jd / "spec.json").write_text(json.dumps({"work": ROOT}))
    lg = jd / "place.live.log"
    lg.write_text("x")
    old = time.time() - silent_min * 60
    os.utime(lg, (old, old))
    return dict(die="s81", item="a", kind="type", event="e", attempt=2, status="RUNNING", unit="u-a", dir=str(jd),
                started=old - 600, updated=old - 600)


class Judge(unittest.TestCase):
    def test_first_sample_never_hung(self):
        hung, w, _ = KW.hung_judge(None, {"cpu": 10, "log": 0}, 0, 10_000.0, 120)
        self.assertFalse(hung)
        self.assertEqual((w["cpu"], w["t"]), (10, 10_000.0))

    def test_both_stalled_is_hung(self):
        t0 = 100_000.0
        hung, w, why = KW.hung_judge({"cpu": 10, "t": t0}, {"cpu": 30, "log": t0 - 60}, t0 - 60, t0 + 121 * 60, 120)
        self.assertTrue(hung)                                  # +20 s CPU (< 60 s) is not progress
        self.assertEqual(w["t"], t0)
        self.assertIn("not grown", why)

    def test_cpu_progress_resets_mark(self):
        t0 = 100_000.0
        hung, w, _ = KW.hung_judge({"cpu": 10, "t": t0}, {"cpu": 4000, "log": 0}, 0, t0 + 300 * 60, 120)
        self.assertFalse(hung)
        self.assertEqual((w["cpu"], w["t"]), (4000, t0 + 300 * 60))

    def test_recent_stage_log_is_progress(self):
        t0 = 100_000.0
        hung, _, _ = KW.hung_judge({"cpu": 10, "t": t0}, {"cpu": 10, "log": t0 + 200 * 60}, 0, t0 + 250 * 60, 120)
        self.assertFalse(hung)

    def test_restarted_process_resets_mark(self):
        hung, w, _ = KW.hung_judge({"cpu": 900, "t": 0.0}, {"cpu": 5, "log": 0}, 0, 50_000.0, 120)
        self.assertFalse(hung)
        self.assertEqual(w["t"], 50_000.0)


class StageOutput(unittest.TestCase):
    def test_native_place_report_progress_prevents_early_hang_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            now = 20_000.0
            stdout = root / "place.log"
            stdout.write_text("Report metrics stage 3, global place...\n")
            log_time = now - 131 * 60
            os.utime(stdout, (log_time, log_time))

            reports = root / "gen" / "hub_c" / "run" / "reports" / "asap7" / "dp_hub_c" / "base"
            reports.mkdir(parents=True)
            unrelated = reports / "3_unrelated.rpt"
            unrelated.write_text("not native stage output")
            os.utime(unrelated, (now, now))
            report = reports / "3_global_place.rpt"
            report.touch()

            # Exercise the actual fleet probe's file scanner without scanning host processes.
            scanner = KW.HUNG_PROBE.split("def newest_log(top):", 1)[1].split("\nprocs = {}", 1)[0]
            probe = {"glob": glob, "os": os, "stat": stat}
            exec("def newest_log(top):" + scanner, probe)
            self.assertEqual(probe["newest_log"](str(root)), log_time)

            report.write_text("global place report_clock_min_period\nvclk period_min = 0.00\n")
            report_time = now - 38 * 60
            os.utime(report, (report_time, report_time))
            progress = probe["newest_log"](str(root))
            self.assertEqual(progress, report_time)
            rec = {"stage": "place", "hang_reported": [now - 33 * 60, log_time]}
            self.assertEqual(KW.hang_judge(rec, {"log": log_time}, now)[0], "cancel")
            self.assertIsNone(KW.hang_judge(rec, {"log": progress}, now)[0])

            resizer = reports / "3_resizer.rpt"
            resizer.write_text("resizer report_clock_min_period\nvclk period_min = 0.00\n")
            resizer_time = now - 28 * 60
            os.utime(resizer, (resizer_time, resizer_time))
            self.assertEqual(probe["newest_log"](str(root)), resizer_time)


class Reap(unittest.TestCase):
    def test_cancel_only_after_window_without_cpu_growth(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            now = time.time()
            ap = AP(cpu=500.0)
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}, now=now), 0)        # first sample: mark only
            r = st["items"]["a"]
            self.assertEqual(r["status"], "RUNNING")
            self.assertGreaterEqual(r["hung_watch"]["cpu"], 500.0)                # summed over the fleet hosts
            # WF-1 11-14 (owner #H): a row silent 400 min with busy CPU is never cancelled; at >= 360 min it is posted once
            self.assertTrue(any("HUNG-WATCH POST" in m for m in ap.logs))
            ap = AP(cpu=520.0)                                                 # +20 s CPU in 130 min: hung
            n = {}
            self.assertEqual(KW.reap_dead(ap, CFG, st, n, now=now + 130 * 60), 1)
            # FABLE-FLOW-0555 F: the first hang of an item is cancelled by its exact units and relaunched as a free infra retry
            self.assertEqual((r["status"], r["class"]), ("RETRY-INFRA", "INFRA"))
            self.assertTrue(r["reason"].startswith("HUNG-WATCH cancel, free infra retry"))
            self.assertIn("a", {k.split("|")[-1] for k in st["hung_retried"]} | {"a"})
            self.assertIn(["systemctl", "--user", "stop", "u-a"], ap.cmds)
            self.assertTrue(any(c[-5:] == ["docker", "stop", "-t", "30", "dpkit-a-1"] and "epyc9" in c for c in ap.cmds))
            self.assertNotIn("hung_watch", r)
            self.assertIn("CANCELLED-HUNG", n["s81"][0])

    def test_cpu_progress_stays_report_only(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            now = time.time()
            KW.reap_dead(AP(cpu=500.0), CFG, st, {}, now=now)
            for i, cpu in enumerate((900.0, 5000.0, 9000.0), 1):               # a busy global_place: never cancelled
                ap = AP(cpu=cpu)
                self.assertEqual(KW.reap_dead(ap, CFG, st, {}, now=now + i * 130 * 60), 0)
                self.assertEqual(st["items"]["a"]["status"], "RUNNING")
                self.assertFalse(any(c[:3] == ["systemctl", "--user", "stop"] for c in ap.cmds))

    def test_off_and_unreadable_and_dry(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            now = time.time()
            st["items"]["a"]["hung_watch"] = {"cpu": 500.0 + 0.5 * (len(set(KW.WJ.FLEET) | {"epyc9"}) - 1), "t": now - 500 * 60}   # probed hosts: the fleet plus the die hosts
            self.assertEqual(KW.reap_dead(AP(cpu=500.0), dict(CFG, hung_watch_min=0), st, {}, now=now), 0)   # off
            self.assertEqual(KW.reap_dead(AP(cpu=500.0, probe_rc=1), CFG, st, {}, now=now), 0)               # unreadable
            ap = AP(cpu=500.0)
            ap.DRY = True
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}, now=now), 0)
            self.assertTrue(any("would reap" in m and "HUNG" in m for m in ap.logs))
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")

    def test_nothing_alive_is_still_r2(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            self.assertEqual(KW.reap_dead(AP(alive=False), CFG, st, {}), 1)
            self.assertEqual((st["items"]["a"]["status"], st["items"]["a"]["class"]), ("FAIL", "INFRA"))


class AdmissionWait(unittest.TestCase):
    """FLEET-WATCH-1400: a row with no container on any host is an ot-run waiter; its wait is never counted, and the CPU-liveness window follows hung_watch_min"""

    def test_waiter_is_never_judged_however_long_it_is_silent(self):
        prog = {"cpu": 150.0, "log": 0, "containers": [], "pids": 4}
        hung, w, why = KW.hung_judge({"cpu": 150.0, "t": 0.0, "dcpu": 150.0, "dt": 0.0}, prog, 0, 50_000.0, 120, dead_min=30)
        self.assertFalse(hung)
        self.assertEqual((w["t"], w["dt"]), (50_000.0, 50_000.0))       # both clocks restart: the waiting time is not counted
        self.assertIn("waiting for admission", why)

    def test_clock_starts_when_the_container_appears(self):
        t0 = 100_000.0
        _, w, _ = KW.hung_judge({}, {"cpu": 150.0, "log": 0, "containers": [], "pids": 4}, 0, t0, 120, dead_min=30)
        run = {"cpu": 150.0, "log": 0, "containers": ["epyc9:dpkit-a-1"], "pids": 9}
        h1, w, _ = KW.hung_judge(w, run, 0, t0 + 60, 120, dead_min=30)
        self.assertFalse(h1)
        h2, _, _ = KW.hung_judge(w, run, 0, t0 + 60 + 121 * 60, 120, dead_min=30)
        self.assertTrue(h2)                                              # judged from the start of the container, 120 min

    def test_waiting_row_survives_reap_dead(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            now = time.time()
            for i in range(3):
                ap = AP(cpu=150.0, containers=())
                self.assertEqual(KW.reap_dead(ap, CFG, st, {}, now=now + i * 200 * 60), 0)
                self.assertEqual(st["items"]["a"]["status"], "RUNNING")
                self.assertFalse(any(c[:3] == ["systemctl", "--user", "stop"] for c in ap.cmds))

    def test_dead_window_follows_hung_watch_min_unless_configured(self):
        with tempfile.TemporaryDirectory() as d:
            st = {"items": {"a": silent_rec(d, 400)}}
            now = time.time()
            KW.reap_dead(AP(cpu=500.0), CFG, st, {}, now=now)
            ap = AP(cpu=501.0)
            self.assertEqual(KW.reap_dead(ap, CFG, st, {}, now=now + 40 * 60), 0)        # 40 min flat with a container: not cancelled at 30
            self.assertEqual(st["items"]["a"]["status"], "RUNNING")


class Probe(unittest.TestCase):
    def test_probe_counts_processes_and_stage_log(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "items" / "a" / "attempt_2"
            (root / "gen" / "a" / "run" / "logs").mkdir(parents=True)
            lg = root / "gen" / "a" / "run" / "logs" / "3_3_place_gp.tmp.log"
            lg.write_text("x")
            # This fixture probes a host process and its stage log. Keep the
            # container census independent of concurrent Docker activity.
            docker = Path(d) / "docker"
            docker.write_text("#!/bin/sh\nexit 0\n")
            docker.chmod(0o700)
            p = subprocess.Popen(["sleep", "300"], cwd=str(root))
            try:
                o = subprocess.run([sys.executable, "-I", "-", json.dumps([str(root)])], input=KW.HUNG_PROBE,
                                   capture_output=True, text=True, timeout=120, check=True,
                                   env=dict(os.environ, PATH=d)).stdout
            finally:
                p.kill()
                p.wait()
            got = json.loads(o.strip().splitlines()[-1])["HUNG_PROBE"][str(root)]
            self.assertGreaterEqual(got["pids"], 1)
            self.assertAlmostEqual(got["log"], lg.stat().st_mtime, places=3)


if __name__ == "__main__":
    unittest.main()
