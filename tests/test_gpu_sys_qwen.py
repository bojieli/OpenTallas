"""Gates of the GPU-organised HBM comparator software stack (tools/gpu_sys): the OTG-1 lane semantics against the
golden primitives, and the Qwen3 HBM lowering against tools/hdc_golden.py on the functional machine.
The RTL runs (SIMT SM unit gate, end-to-end system) execute only with GPU_SYS_RTL=1."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gpu_sys"))
sys.path.insert(0, str(ROOT / "tools"))


class LaneSemantics(unittest.TestCase):
    def test_conversions_match_golden(self):
        import hdc_golden as G
        import isa
        rng = np.random.default_rng(7)
        x = (rng.standard_normal(20000) * np.exp2(rng.integers(-14, 12, 20000))).astype(np.float32)
        b = x.view(np.uint32)
        self.assertTrue(np.array_equal(isa.cvt_bf16(b), G.bits(G.to_bf16(x))))
        self.assertTrue(np.array_equal(isa.cvt_e4m3(b), G.bits(G.to_fp8(x))))
        enc = isa.e4m3_encode(isa.cvt_e4m3(b))
        self.assertTrue(np.array_equal(isa.e4m3_decode(enc), isa.cvt_e4m3(b)))

    def test_fp_ops_are_golden_add_mul(self):
        import hdc_golden as G
        import isa
        rng = np.random.default_rng(8)
        a = (rng.standard_normal(5000) * 3).astype(np.float32)
        c = (rng.standard_normal(5000) * 3).astype(np.float32)
        self.assertTrue(np.array_equal(isa.fadd(a.view(np.uint32), c.view(np.uint32)), G.bits(G.add(a, c))))
        self.assertTrue(np.array_equal(isa.fmul(a.view(np.uint32), c.view(np.uint32)), G.bits(G.mul(a, c))))


class QwenLowering(unittest.TestCase):
    def test_two_positions_bit_exact(self):
        if not (ROOT / "build/models/qwen3-reduced-v1").exists():
            self.skipTest("reduced Qwen3 checkpoint not present in build/")
        import qwen_hbm
        self.assertTrue(qwen_hbm.check(2))


@unittest.skipUnless(os.environ.get("GPU_SYS_RTL") == "1", "RTL runs need GPU_SYS_RTL=1")
class Rtl(unittest.TestCase):
    def test_simt_sm(self):
        subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_simt_sm.py"), "--cases", "3"], check=True)

    def test_system_qwen(self):
        subprocess.run([sys.executable, str(ROOT / "tools/gpu_sys/run_system.py"), "--model", "qwen"], check=True)


if __name__ == "__main__":
    unittest.main()
