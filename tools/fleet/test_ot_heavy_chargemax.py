"""CHARGEMAX_1111 (KW-FIX-44, COORD 11-11 on DIE-S81-85 20:19): admission charges max(--mem request, learned class
peak); a class with < 3 finished samples never lowers a declared request (epyc7: lec.py:kit n=1 1.7 GB charged 10 GB
against --mem 96)."""
import importlib.machinery
import importlib.util
import os
import unittest
from pathlib import Path

ld = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_cm", str(Path(__file__).with_name("ot-heavy-reconcile")))
R = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
ld.exec_module(R)


class ChargeMax(unittest.TestCase):
    def setUp(self):
        self.env = {k: os.environ.get(k) for k in ("REAL_ADMIT", "CLASS_LOWER_MIN_N")}
        for k in self.env:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_lec_n1_keeps_request(self):
        self.assertIsNone(R.admit_size(96, "lec.py:kit", {"lec.py:kit": dict(n=1, proved=0, peak_gb=1.7)}))

    def test_real_admit_path_also_guarded(self):
        os.environ["REAL_ADMIT"] = "1"
        self.assertIsNone(R.admit_size(96, "lec.py:kit", {"lec.py:kit": dict(n=2, proved=5, peak_gb=1.7)}))
        self.assertEqual(R.admit_size(96, "lec.py:kit", {"lec.py:kit": dict(n=3, proved=0, peak_gb=1.7)})[0], 4)

    def test_three_samples_may_lower(self):
        self.assertEqual(R.admit_size(96, "lec.py:kit", {"lec.py:kit": dict(n=3, proved=0, peak_gb=1.7)})[0], 10)

    def test_raise_only_specific_uncapped_n3(self):
        dock = ["/usr/bin/docker", "run", "--rm", "img", "bash", "x.sh"]
        self.assertIsNone(R.admit_size(8, "x.sh:k", {"x.sh:k": dict(n=3, proved=0, peak_gb=20.4)},
                                       ["docker", "run", "img"]))                       # PATH docker = shim: capped
        t3 = {"x.sh:k": dict(n=3, proved=0, peak_gb=20.4), "x.sh": dict(n=50, proved=0, peak_gb=178.0)}
        a = R.admit_size(8, "x.sh:k", t3, dock)
        self.assertEqual(a[0], 21)
        self.assertIn("max(request, peak)", a[1])
        self.assertIsNone(R.admit_size(8, "x.sh:k", t3, ["bash", "x.sh"]))                 # scope MemoryMax: clamp
        self.assertIsNone(R.admit_size(8, "x.sh:k", t3, dock[:2] + ["-m", "8g"] + dock[2:]))  # container cap: clamp
        self.assertIsNone(R.admit_size(8, "x.sh:k", t3))                                 # no argv: capped
        self.assertIsNone(R.admit_size(96, "x.sh", t3, dock))                            # bare fleet class never raises
        self.assertIsNone(R.admit_size(8, "x.sh:k", {"x.sh:k": dict(n=2, proved=0, peak_gb=20.4)}, dock))  # n < 3

    def test_epyc7_lec_96_charged_96(self):
        t = {"lec.py": dict(n=54, proved=0, peak_gb=178.1), "lec.py:kit": dict(n=1, proved=0, peak_gb=1.7)}
        self.assertIsNone(R.admit_size(96, "lec.py:kit", t, ["python3", "/work/lec.py", "kit"]))
        self.assertIsNone(R.admit_size(96, "lec.py", t, ["python3", "/work/lec.py", "/work/kit"]))

    def test_unmeasured_and_seed_keep_request(self):
        self.assertIsNone(R.admit_size(96, "never.sh", {}))
        self.assertIsNone(R.admit_size(192, "ref_gate_new.sh", {}))       # the 10 GB family seed no longer lowers


if __name__ == "__main__":
    unittest.main()
