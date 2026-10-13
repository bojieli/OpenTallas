"""ot-heavy v4 / reconcile v3 (owner 2026-10-13): a request over 2x the measured class peak is charged the class size."""
import importlib.machinery
import importlib.util
import pathlib
import unittest

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile", loader))
loader.exec_module(R)

T = {"run_sim.sh": dict(n=2, live=0, proved=0, peak_gb=5.0, req_gb=96),
     "big.sh": dict(n=1, live=0, proved=0, peak_gb=60.0, req_gb=96),
     "liveonly.sh": dict(n=0, live=3, proved=0, peak_gb=5.0, req_gb=96),
     "proved.sh": dict(n=0, live=1, proved=1, peak_gb=30.0, req_gb=96),
     "cd": dict(n=5, live=0, proved=0, peak_gb=1.0, req_gb=72)}


class Admit(unittest.TestCase):
    def test_oversized_request_is_charged_the_class_size(self):
        self.assertEqual(R.admit_size(96, "run_sim.sh", T)[0], 13)          # max(1.5 x 5, 5 + 8)
        self.assertEqual(R.admit_size(96, "proved.sh", T)[0], 45)           # max(1.5 x 30, 30 + 8)

    def test_request_within_2x_or_unknown_keeps_its_request(self):
        self.assertIsNone(R.admit_size(96, "big.sh", T))                    # 96 <= 2 x 60
        self.assertIsNone(R.admit_size(96, "never_seen.sh", T))
        self.assertIsNone(R.admit_size(96, "liveonly.sh", T))               # no finished or proved-past-peak job
        self.assertIsNone(R.admit_size(72, "cd", T))                        # not a class
        self.assertIsNone(R.admit_size(12, "run_sim.sh", T))                # charge would not be below the request

    def test_classify_matches_between_argv_forms(self):
        self.assertEqual(R.classify(["bash", "/tmp/ref_gate_vm_cp_fe0_cx_20261013-035404.sh"]), "ref_gate_vm_cp_fe#_cx_#-#.sh")


if __name__ == "__main__":
    unittest.main()
