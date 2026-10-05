"""Per-die memory system (ot_gpu_memsys): image-placement helper checks and the committed record (fast); with
GPU_SYS_RTL=1, the full lint + Verilator bench runner (USE_W2=0 and 1, >= 20,000 random transactions)."""
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
import mem_image as M  # noqa: E402

RECORD = ROOT / "results/rtl/hbm_system_rtl_20261003/memsys.json"


class MemImageTest(unittest.TestCase):
    def test_self_check(self):
        self.assertEqual(M.self_check(), [])

    def test_placement_rule(self):
        # 128-byte interleave over 2 slices: bytes 0..127 slice 0, 128..255 slice 1, 256.. slice 0 local 128
        self.assertEqual(M.placement(0, 2, 1024), (0, 0, 0, 0))
        self.assertEqual(M.placement(127, 2, 1024), (0, 3, 3, 31))
        self.assertEqual(M.placement(128, 2, 1024), (1, 0, 0, 0))
        self.assertEqual(M.placement(256 + 33, 2, 1024), (0, 5, 5, 1))
        self.assertEqual(M.placement(5 * 32, 1, 4), (0, 5, 1, 0))

    def test_images_round_trip(self):
        rng = np.random.default_rng(3)
        data = rng.integers(0, 256, 5000, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as d:
            files = M.write_images({4096 + 7: data, 0: b"\x11\x22"}, 4, 256, d, "die0")
            self.assertEqual([Path(f).name for f in files], [f"die0_p{s}.hex" for s in range(4)])
            words = [[bytes.fromhex(ln)[::-1] for ln in Path(f).read_text().split()] for f in files]
            self.assertTrue(all(len(w) == 256 for w in words))
            for i in (0, 1, 999, 4999):
                s, _, w, lane = M.placement(4096 + 7 + i, 4, 256)
                self.assertEqual(words[s][w][lane], data[i])
            self.assertEqual(words[0][0][:3], b"\x11\x22\x00")

    def test_die_naming(self):
        with tempfile.TemporaryDirectory() as d:
            files = M.write_images({0: b"\x01"}, 2, 4, d, "mem", die=3)
            self.assertEqual([Path(f).name for f in files], ["mem_d3_p0.hex", "mem_d3_p1.hex"])

    def test_alias_refused(self):
        with self.assertRaises(ValueError):
            M.build_arrays({2 * 32 * 64: b"\x01"}, 2, 64)


@unittest.skipUnless(RECORD.exists(), "no committed memsys record")
class MemsysRecordTest(unittest.TestCase):
    def test_record(self):
        rec = json.loads(RECORD.read_text())
        self.assertEqual(rec["schema"], "opentallas.gpu_sys.memsys.v1")
        self.assertEqual(rec["verdict"], "PASS")
        self.assertTrue(all(L["pass"] for L in rec["lint"]))
        for use_w2 in (0, 1):
            runs = [s for s in rec["simulations"] if s["use_w2"] == use_w2]
            self.assertTrue(runs and all(s["pass"] and s["random_requests"] >= 20000 for s in runs))

    def test_record_sources_current(self):
        rec = json.loads(RECORD.read_text())
        for rel, digest in rec["sources"].items():
            if rel.startswith(("rtl/gpu_sys/", "rtl/hdc/kv/", "rtl/experimental/")):
                self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)


@unittest.skipUnless(os.environ.get("GPU_SYS_RTL") == "1", "set GPU_SYS_RTL=1 to run the RTL bench")
class MemsysRtlTest(unittest.TestCase):
    def test_rtl_runner(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_memsys.py"),
                                "--out", str(Path(d) / "memsys.json"), "--build-dir", str(Path(d) / "b")],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
