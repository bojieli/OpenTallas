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

    def test_infinite_or_unknown_arrival_refused(self):
        for value in (float("inf"), float("nan"), None):
            p = self.path()
            p["ss"]["capture_clock"] = [1000, value]
            with self.assertRaises(ValueError): subject.path_slacks(p)

    def contract(self):
        c = {name: self.path() for name in subject.INPUT_GROUPS + subject.OUTPUT_GROUPS}
        for name in subject.OUTPUT_GROUPS:
            c[name].update(output_load_sta_units=1.0, load_library_sha256="c"*64)
        return c

    def test_complete_source_io_translation(self):
        s = subject.parent_io_sdc(self.contract())
        self.assertIn("set_input_delay -max 1250 -clock clk [get_ports {res_in*}]", s)
        self.assertIn("set_input_delay -min 1085 -clock clk [get_ports {res_in*}]", s)
        self.assertIn("set_output_delay -max -790 -clock clk [get_ports {tw_v}]", s)
        self.assertIn("set_output_delay -min -1000 -clock clk [get_ports {tw_v}]", s)
        self.assertIn("set_clock_uncertainty -setup 60", s)
        self.assertIn("set_clock_uncertainty -hold 25", s)
        self.assertIn("set_min_delay -ignore_clock_latency 0", s)
        self.assertNotIn("166.667", s)

    def test_partial_io_cannot_hide_other_failures(self):
        c = self.contract()
        del c["p_*"]
        with self.assertRaises(ValueError): subject.parent_io_sdc(c)

    def test_failed_prospective_budget_refused(self):
        c = self.contract()
        c["res_in*"]["ff"]["launch_clock"] = [0, 0]
        with self.assertRaises(ValueError): subject.parent_io_sdc(c)

    def test_ideal_receiver_load_refused(self):
        c = self.contract()
        c["tw_v"]["output_load_sta_units"] = 0
        with self.assertRaises(ValueError): subject.parent_io_sdc(c)

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
