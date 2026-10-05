import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_slab_capture_contract as subject

class CaptureContract(unittest.TestCase):
    def path(self):
        return dict(source_identity="parent.lq", capture_identity="slab.res_q",
                    ss_evidence_sha256="a"*64, ff_evidence_sha256="b"*64,
                    ss=dict(launch_clock=[1000, 1020], capture_clock=[1000, 1020],
                            clk_q=[45, 80], wire=[20, 150], setup=60),
                    ff=dict(launch_clock=[1000, 1020], capture_clock=[1000, 1020],
                            clk_q=[45, 80], wire=[40, 150], hold=20))

    def test_same_region_finite_paths(self):
        self.assertTrue(subject.path_slacks(self.path())["pass_path"])

    def test_ideal_external_launch_fails_hold(self):
        p = self.path()
        p["ff"]["launch_clock"] = [0, 0]
        self.assertFalse(subject.path_slacks(p)["pass_path"])

    def test_late_slab_output_fails_setup(self):
        p = self.path()
        p["ss"]["launch_clock"] = [2000, 2100]
        self.assertFalse(subject.path_slacks(p)["pass_path"])

    def test_missing_evidence_refused(self):
        p = self.path()
        del p["ss_evidence_sha256"]
        with self.assertRaises(ValueError): subject.path_slacks(p)

    def test_invalid_interval_refused(self):
        p = self.path()
        p["ss"]["wire"] = [150, 20]
        with self.assertRaises(ValueError): subject.path_slacks(p)

    def test_scope_and_once_only_capture(self):
        r = subject.model()
        self.assertEqual(r["capture"]["new_ff_bits"], 0)
        self.assertEqual(r["capture"]["added_capture_cycles"], 0)
        self.assertEqual(r["capture"]["ff_cell_area_um2_existing"], 149.2992)
        self.assertFalse(r["physical_launch_admitted"])
        self.assertFalse(r["parent"]["native_t_in_has_ready_valid_handshake"])
        self.assertEqual(r["functional_scope"]["historical_1505_arithmetic_gate_BW_FIFO"], 0)
        self.assertEqual(r["selection"]["BW_FIFO"], 1)

if __name__ == "__main__": unittest.main()
