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

    def test_books_selftest(self):          # v6: charge per unit, the 25 % rule, the floor, the two hosts as measured
        self.assertEqual(R.selftest(), 0)

    def test_books_follow_available_memory(self):
        # a busy host: 26 units, half of them old; the growth charged stays within 15 % of RAM
        rows = [dict(unit=f"u{i}", res=64, active=True, file="", file_age=0, req=64.0, now=12.0, obs=14.0,
                     age=200.0 + 400 * i, cls="?") for i in range(26)]
        b = R.books(rows, 1133, 600, {})
        self.assertLessEqual(b["grow"], 0.15 * 1133)
        self.assertGreaterEqual(R.admissible(1133, 600, b, 64, 226.6), 300)


if __name__ == "__main__":
    unittest.main()


class DieFirst(unittest.TestCase):
    """DIE-FIRST (owner 2026-10-15 23:50): a waiting die trial's charge is held against non-die requests."""
    def test_hold_only_for_a_die_trial_that_fits_the_host(self):
        from unittest.mock import patch
        with patch.object(R, "prio_waiters", return_value=[(10, 400), (20, 100)]):
            self.assertEqual(R.die_hold(1024, 300, 32, 205, {}), 400)        # oldest waiter, fits 1024-205-32
        with patch.object(R, "prio_waiters", return_value=[(10, 900), (20, 100)]):
            self.assertEqual(R.die_hold(1024, 300, 32, 205, {}), 100)        # 900 can never start here: skipped
        with patch.object(R, "prio_waiters", return_value=[]):
            self.assertEqual(R.die_hold(1024, 300, 32, 205, {}), 0)

    def test_prio_waiters_reads_environ(self):
        import os
        from unittest.mock import patch
        files = {"/proc/7/cmdline": "/bin/bash\x00/usr/local/bin/ot-heavy\x00--mem\x00400\x00--\x00bash\x00die.sh\x00",
                 "/proc/7/environ": "PATH=/bin\x00OT_HEAVY_PRIO=die\x00",
                 "/proc/7/stat": "7 (bash) S 1 7 7 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 555 0 0",
                 "/proc/8/cmdline": "/bin/bash\x00/usr/local/bin/ot-heavy\x00--mem\x00300\x00--\x00bash\x00route.sh\x00",
                 "/proc/8/environ": "PATH=/bin\x00", "/proc/8/stat": "8 (bash) S 1 8 8 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 444 0 0"}
        with patch.object(os, "listdir", return_value=["7", "8", "self"]), \
                patch.object(R, "rd", side_effect=lambda p: files.get(p, "")):
            self.assertEqual(R.prio_waiters({}), [(555, 400)])
