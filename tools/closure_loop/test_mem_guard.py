"""MEM-GUARD (drive-1010 2026-10-10): EPYC2/EPYC4 hung at 6-7 GB available; the loop stops its own youngest stage."""
import datetime as dt
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="memguard_"))
import closure_loop as cl  # noqa: E402


def iso(h):
    return dt.datetime.fromtimestamp(time.time() - h * 3600).astimezone().isoformat()


class F:
    def __init__(self, mem):
        self.last_good = {"hx": (time.time(), {"mem_gb": mem, "load1": 10})}


class MemGuard(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp()); (d / "jobs").mkdir()
        for p in (patch.object(cl, "STATE", d), patch.object(cl, "hosts_table", return_value=[{"name": "hx", "ram_gb": 1000}]),
                  patch.object(cl, "host_cfg", return_value={"label": "HX"}), patch.object(cl, "log")):
            p.start(); self.addCleanup(p.stop)
        cl._MEM_GUARD_LAST.clear()
        mk = lambda n, h, ram, **kw: dict(dict(name=n, status="RUNNING", host="hx", stage_tag="route.a1", stage_key="route",
                                               stage_started=iso(h), run=f"/r/{n}", events=[],
                                               spec={"name": n, "peak_ram_gb": ram, "source": {}}), **kw)
        self.jobs = [mk("old_big", 20, 200), mk("young_small", 0.2, 16), mk("young_big", 0.3, 128),
                     mk("die_x", 0.1, 300, run="/x/die-evidence-2/die_x"), mk("eco_j", 0.1, 64, status="ECO")]
        for j in self.jobs:
            cl.save_job(j)

    def test_stops_youngest_biggest_once(self):
        with patch.object(cl, "kill_own_stage") as k:
            done = cl.mem_guard(cl.all_jobs(), F(10))
            self.assertEqual(done, [("hx", "young_big")])
            self.assertEqual(cl.load_job("young_big")["status"], "READY")
            self.assertIn("MEM-GUARD", cl.load_job("young_big")["wait"])
            self.assertEqual(cl.mem_guard(cl.all_jobs(), F(10)), [])      # rate limited
            k.assert_called_once()

    def test_no_action_with_headroom(self):
        with patch.object(cl, "kill_own_stage") as k:
            self.assertEqual(cl.mem_guard(cl.all_jobs(), F(200)), [])
            k.assert_not_called()


if __name__ == "__main__":
    unittest.main()
