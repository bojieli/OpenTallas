"""Collective path (ot_gpu_coll_endpoint + ot_gpu_coll_fabric): record and stimulus self-checks (fast) and, with
GPU_SYS_RTL=1, the RTL bench runner tools/gpu_sys/run_coll.py."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "gpu_sys"))
import run_coll as M  # noqa: E402

RECORD = ROOT / "results/rtl/hbm_system_rtl_20261003/coll.json"


class CollStimulusTest(unittest.TestCase):
    def test_reduce_expectation_is_canonical_rne(self):
        a = np.array([0x80000000, 0x3F800000, 0x00000001, 0x7E800000], dtype=np.uint32)
        b = np.array([0x80000000, 0xBF800000, 0x00000001, 0x7E800000], dtype=np.uint32)
        c = dict(mode=0, count=4, measure=False, data=[np.pad(a, (0, M.NL - 4)), np.pad(b, (0, M.NL - 4))])
        e = M.expected(c)
        self.assertEqual([int(x) for x in e[:4]], [0, 0, 2, 0x7F000000])
        self.assertTrue(all(int(x) == 0 for x in e[4:]))

    def test_gather_placement(self):
        d = [np.arange(M.NL, dtype=np.uint32) + 1000 * (r + 1) for r in range(M.R)]
        e = M.expected(dict(mode=1, count=5, measure=False, data=d))
        self.assertEqual([int(x) for x in e[:10]], [1000, 1001, 1002, 1003, 1004, 2000, 2001, 2002, 2003, 2004])
        self.assertTrue(all(int(x) == 0 for x in e[10:]))

    def test_cases_cover_specials_and_stay_finite(self):
        cases = M.make_cases(40, 1)
        red = [c for c in cases if c["mode"] == 0]
        negz = sub = 0
        for c in red:
            s = c["data"][0][:c["count"]].view(np.float32) + c["data"][1][:c["count"]].view(np.float32)
            self.assertTrue(np.all(np.isfinite(s)))
            u = s.view(np.uint32)
            negz += int((u == 0x80000000).sum())
            sub += int(((((u >> 23) & 0xFF) == 0) & ((u & 0x7FFFFF) != 0)).sum())
        self.assertGreater(negz, 0)
        self.assertGreater(sub, 0)
        self.assertTrue(any(c["count"] == M.NL for c in red))


@unittest.skipUnless(RECORD.exists(), "no committed coll.json")
class CollRecordTest(unittest.TestCase):
    def test_record(self):
        rec = json.loads(RECORD.read_text())
        self.assertEqual(rec["schema"], M.SCHEMA)
        self.assertEqual(rec["verdict"], "PASS")
        self.assertEqual(rec["bench"]["n_fail"], 0)
        self.assertIn("ALL_REDUCE_count128", rec["latency"])
        for path in ("rtl/gpu_sys/ot_gpu_coll_endpoint.sv", "rtl/gpu_sys/ot_gpu_coll_fabric.sv",
                     "rtl/link/ot_link_nvls_switch.sv"):
            self.assertIn(path, rec["sources"])

    def test_record_is_source_current(self):
        rec = json.loads(RECORD.read_text())
        for path, digest in rec["sources"].items():
            if path.startswith(("rtl/", "tools/gpu_sys/run_coll.py")):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)


@unittest.skipUnless(os.environ.get("GPU_SYS_RTL") == "1", "set GPU_SYS_RTL=1 to run the RTL bench")
class CollRtlTest(unittest.TestCase):
    def test_rtl_runner(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_coll.py"), "--nt", "60", "--seed", "7",
                                "--out", str(Path(d) / "coll.json"), "--build-dir", str(Path(d) / "b")],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
