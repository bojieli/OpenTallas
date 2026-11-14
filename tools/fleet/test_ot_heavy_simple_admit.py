"""ADMIT-TUNE-1 (OWNER 11-14): SIMPLE_ADMIT = MemAvailable - INV_HEADROOM_GB >= class measured RSS (16 GB if unknown)."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import pathlib
import unittest
from unittest.mock import patch

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile", loader))
loader.exec_module(R)
T = {"run_sim.sh:sim": dict(n=3, live=0, proved=0, peak_gb=30.0, req_gb=96)}


def gate(avail, cls, env):
    with patch.dict(os.environ, env), patch.object(R, "classify", return_value=cls), patch.object(R, "sizes", return_value=T), \
            patch.object(R, "meminfo", return_value=(1000.0, float(avail))), patch.object(R, "read_units", side_effect=AssertionError("books read")):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            R.gate_locked(96, ["x"])
    return out.getvalue()


class SimpleAdmit(unittest.TestCase):
    env = {"SIMPLE_ADMIT": "1", "INV_HEADROOM_GB": "16"}

    def test_measured_class_needs_its_peak_plus_headroom(self):
        self.assertTrue(gate(46, "run_sim.sh:sim", self.env).startswith("OK 30 "))
        self.assertTrue(gate(45, "run_sim.sh:sim", self.env).startswith("NO 30 "))

    def test_unknown_class_needs_16_gb(self):
        self.assertTrue(gate(32, "never.sh:x", self.env).startswith("OK 16 "))
        self.assertTrue(gate(31, "never.sh:x", self.env).startswith("NO 16 "))

    def test_young_window_is_configurable_default_300(self):
        self.assertIn(R.YOUNG_S, (300,))  # no /etc/ot-heavy.conf YOUNG_S in the test env

    def test_free_is_light_and_never_reads_the_unit_books(self):
        # FREE_LIGHT_1114: --free under SIMPLE_ADMIT must not call read_units (one systemctl per unit; 326 piled-up probes hung epyc10)
        with patch.dict(os.environ, self.env), patch.object(R, "sizes", return_value=T), patch.object(R, "meminfo", return_value=(1000.0, 300.0)), \
                patch.object(R, "waiters", return_value=([10], [10])), patch.object(R, "read_units", side_effect=AssertionError("books read")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                R.free("/")
        import json
        j = json.loads(out.getvalue())
        self.assertEqual((j["admit_gb"], j["free_gb"], j["waiting"]), (284, 274, 1))


if __name__ == "__main__":
    unittest.main()
