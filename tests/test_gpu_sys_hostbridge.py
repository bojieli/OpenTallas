"""Host path of the GPU-organised HBM comparator system: record sanity (fast) and, with GPU_SYS_RTL=1, the RTL bench
(tools/gpu_sys/run_host_bridge.py under Icarus, one seed)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hbm_system_rtl_20261003/host_bridge.json"
sys.path.insert(0, str(ROOT / "tools" / "gpu_sys"))
import run_host_bridge as R  # noqa: E402


class HostBridgeRecordTest(unittest.TestCase):
    def test_record_passes_every_check(self):
        rec = json.loads(RECORD.read_text())
        self.assertEqual(rec["schema"], R.SCHEMA)
        self.assertEqual(rec["verdict"], "PASS")
        self.assertEqual(sorted(rec["checks"]), sorted(R.CHECKS))
        self.assertTrue(all(c["pass"] for c in rec["checks"].values()))
        for key in ("eng_start_to_first_launch", "last_done_to_eng_done"):
            self.assertGreater(rec["latency_ps"][key]["mean_ps"], 0)

    def test_record_pins_sources(self):
        rec = json.loads(RECORD.read_text())
        for rel in [R.BENCH, *R.RTL]:
            self.assertIn(rel, rec["sources"])
            self.assertEqual(len(rec["sources"][rel]), 64)

    def test_parse(self):
        p = R.parse("PASS stream_order launches=3\nFAIL sm_fault x\n"
                    "LAT last_done_to_eng_done_ps n=2 min=1 max=3 mean=2.0\nTB_GPU_HOST_BRIDGE FAIL fails=1\n")
        self.assertEqual(p["checks"], {"stream_order": True, "sm_fault": False})
        self.assertEqual(p["latency"]["last_done_to_eng_done"]["max_ps"], 3.0)
        self.assertFalse(p["bench_pass"])


@unittest.skipUnless(os.environ.get("GPU_SYS_RTL") == "1", "set GPU_SYS_RTL=1 to run the RTL bench")
class HostBridgeRtlTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("iverilog"), "iverilog not installed")
    def test_rtl_runner(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_host_bridge.py"), "--sims", "icarus",
                                "--seeds", "1", "--out", str(Path(d) / "host_bridge.json"),
                                "--build-dir", str(Path(d) / "b")], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
