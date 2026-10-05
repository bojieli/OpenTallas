"""CDC FIFO sizing model self-checks (fast) and, with GPU_SYS_RTL=1, the RTL bench runner."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "gpu_sys"))
import cdc_sizing as M  # noqa: E402


class CdcSizingTest(unittest.TestCase):
    def test_self_check(self):
        self.assertEqual(M.self_check(), [])

    def test_boundary_depths(self):
        depths = {r["boundary"]: r["depth"] for r in M.boundary_table()}
        self.assertEqual(depths, {"sm_to_mem_request": 8, "mem_to_sm_response": 8, "sm_to_link_collective": 8,
                                  "link_to_sm_collective": 8, "host_to_sm_doorbell": 4, "sm_to_host_completion": 4})

    def test_full_shape_is_labelled_not_adopted(self):
        fs = M.full_shape()
        self.assertIn("NOT ADOPTED", fs["label"])
        self.assertAlmostEqual(fs["priced_fraction_of_ceiling"], 1024 / 2763, places=4)


@unittest.skipUnless(os.environ.get("GPU_SYS_RTL") == "1", "set GPU_SYS_RTL=1 to run the RTL bench")
class CdcFifoRtlTest(unittest.TestCase):
    def test_rtl_runner(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_cdc_fifo.py"),
                                "--out", str(Path(d) / "cdc_fifo.json"), "--build-dir", str(Path(d) / "b")],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
