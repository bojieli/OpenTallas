"""STALE-24H (owner 2026-10-10): stages > 24 h and READY/QUEUED holds > 24 h are cancelled through the cancel path."""
import datetime as dt
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="stale24_"))
import closure_loop as cl  # noqa: E402


def iso(h_ago):
    return dt.datetime.fromtimestamp(time.time() - h_ago * 3600).astimezone().isoformat()


def job(name, status, **kw):
    j = dict(name=name, status=status, spec={"name": name, "block": "b", "owner": "Claude:x", "source": {}},
             created=iso(60), events=[], host="h", run=f"/r/{name}")
    j.update(kw)
    return j


class Stale24(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.p = [patch.object(cl, "STATE", self.d), patch.object(cl, "STALE24_LOG", self.d / "stale24.log")]
        for p in self.p:
            p.start()
            self.addCleanup(p.stop)
        (self.d / "jobs").mkdir()

    def jobs(self):
        return [
            job("route_old", "RUNNING", stage_started=iso(30), stage_key="route", stage_tag="route.a1"),
            job("route_new", "RUNNING", stage_started=iso(3), stage_key="route", stage_tag="route.a2"),
            job("eco_old", "ECO", eco={"started": iso(26)}, stage_tag="hold_eco.a1"),
            job("eco_new", "ECO", eco={"started": iso(5)}, stage_tag="hold_eco.a1"),
            job("held_old", "QUEUED", reason="HELD (redundant ...)"),
            job("adopt_old", "READY", wait="adoption hold: diagnostic", stage_started=iso(50)),
            job("capacity_wait", "READY", wait="waiting for capacity", stage_started=iso(30)),
            job("die_x", "RUNNING", stage_started=iso(40), run="/srv/x/die-evidence-2/die_x"),
            job("allowed", "RUNNING", stage_started=iso(40), spec={"name": "allowed", "block": "b", "source": {},
                                                                    "allow_over_24h": "owner: 3-day DRT"}),
            job("closed", "CLOSED", stage_started=iso(90)),
        ]

    def test_candidates(self):
        names = {j["name"] for j, _ in cl.stale24_candidates(self.jobs())}
        self.assertEqual(names, {"route_old", "eco_old", "held_old", "adopt_old"})

    def test_sweep_cancels_through_kill_path_and_logs(self):
        for j in self.jobs():
            cl.save_job(j)
        with patch.object(cl, "kill_own_stage") as kill, patch.object(cl, "ledger"), patch.object(cl, "log"), \
                patch.object(cl, "experiment", create=True):
            done = cl.stale24_sweep(cl.all_jobs(), force=True)
        self.assertEqual(set(done), {"route_old", "eco_old", "held_old", "adopt_old"})
        self.assertEqual({c.args[0]["name"] for c in kill.call_args_list}, {"route_old", "eco_old"})
        for n in done:
            j = cl.load_job(n)
            self.assertEqual(j["status"], "CANCELLED")
            self.assertIn(">24h stale", j["reason"])
        self.assertEqual(cl.load_job("route_new")["status"], "RUNNING")
        self.assertEqual(cl.load_job("capacity_wait")["status"], "READY")
        self.assertEqual(len((self.d / "stale24.log").read_text().splitlines()), 4)

    def test_rate_limited(self):
        with patch.object(cl, "stale24_candidates", return_value=[]) as c:
            cl._STALE24_LAST[0] = 0.0
            cl.stale24_sweep([], now=1000.0)
            cl.stale24_sweep([], now=1100.0)
            self.assertEqual(c.call_count, 1)


if __name__ == "__main__":
    unittest.main()
