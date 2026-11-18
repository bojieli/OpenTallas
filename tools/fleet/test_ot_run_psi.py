"""ot-run FLOW-HEALTH-1 11-15 (FABLE-FLOW-0815 item 3): plan / direct placement takes the lowest CPU pressure, not the most MemAvailable"""
import os
import unittest
from test_ot_run_load_gate import load, row


class Psi(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.m.THREADS = 8
        self.m.HOST_RESERVE = {}

    def hosts(self):
        return {"epyc9": row(291, 96, avail_gb=900, cpu_psi=60.0), "epyc7": row(2, 96, avail_gb=500, cpu_psi=1.0),
                "intel1": row(5, 112, avail_gb=400, cpu_psi=3.0)}

    def test_plan_job_leaves_the_loaded_host(self):
        os.environ["OT_RUN_PRIO_ENV"] = "OT_HEAVY_PRIO=plan"
        try:
            self.m.PRIO_ENV = None
            h, q = self.m.choose(self.hosts(), 64, 8)
        finally:
            os.environ.pop("OT_RUN_PRIO_ENV", None)
        self.assertEqual((h, q), ("epyc7", False))

    def test_load_over_cores_without_psi(self):
        r = {"epyc9": row(291, 96, avail_gb=900), "epyc7": row(2, 96, avail_gb=500)}
        self.assertGreater(self.m.cpu_pressure(r["epyc9"], 8), self.m.cpu_pressure(r["epyc7"], 8))
        self.assertEqual(self.m.least_pressure(r, list(r), 8), "epyc7")

    def test_memory_is_still_required(self):
        r = {"a": row(1, 96, avail_gb=10, cpu_psi=0.0), "b": row(40, 96, avail_gb=500, cpu_psi=20.0)}
        os.environ["OT_RUN_PRIO_ENV"] = "OT_HEAVY_PRIO=plan"
        try:
            self.assertEqual(self.m.choose(r, 64, 8)[0], "b")
        finally:
            os.environ.pop("OT_RUN_PRIO_ENV", None)

    def test_psi_line_parsed(self):
        self.assertEqual(self.m.psi_of("x\nOT_PSI 3.25\n{}"), 3.25)
        self.assertIsNone(self.m.psi_of("OT_PSI\n"))
        self.assertIsNone(self.m.psi_of("nothing"))


if __name__ == "__main__":
    unittest.main()
