#!/usr/bin/env python3
"""KIT-OPS-1 11-13 HUNG-WATCH: a silent but alive row is cancelled (CANCELLED class HUNG) only when both its stage logs and the CPU
time of its processes stopped growing for hung_watch_min; any CPU progress keeps it report-only."""
import json
import os
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
            self.assertEqual((r["status"], r["class"]), ("CANCELLED", "HUNG"))
            self.assertTrue(r["reason"].startswith("CANCELLED-HUNG"))
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
            st["items"]["a"]["hung_watch"] = {"cpu": 500.0 + 0.5 * len(KW.WJ.FLEET), "t": now - 500 * 60}
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


class Probe(unittest.TestCase):
    def test_probe_counts_processes_and_stage_log(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "items" / "a" / "attempt_2"
            (root / "gen" / "a" / "run" / "logs").mkdir(parents=True)
            lg = root / "gen" / "a" / "run" / "logs" / "3_3_place_gp.tmp.log"
            lg.write_text("x")
            p = subprocess.Popen(["sleep", "30"], cwd=str(root))
            try:
                o = subprocess.run([sys.executable, "-I", "-", json.dumps([str(root)])], input=KW.HUNG_PROBE,
                                   capture_output=True, text=True, timeout=120).stdout
            finally:
                p.kill()
            got = json.loads(o.strip().splitlines()[-1])["HUNG_PROBE"][str(root)]
            self.assertGreaterEqual(got["pids"], 1)
            self.assertAlmostEqual(got["log"], lg.stat().st_mtime, places=3)


if __name__ == "__main__":
    unittest.main()
