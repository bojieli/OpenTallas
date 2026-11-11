"""ot-heavy (fleet rule 2026-10-10): a capped command is killed at its MemoryMax; big slots are exclusive."""
import os
import pathlib
import subprocess
import time
import unittest

T = str(pathlib.Path(__file__).with_name("ot-heavy"))
# LOADCAP_1101: these tests are about memory; the host load cap is tested in test_ot_heavy_crit.py
# LOADGATE_1110: the gate reads the REAL host load1 (1.25 x nproc), so on a busy host these timing tests would be held; off here, tested in test_ot_heavy_crit.py
ENV = dict(os.environ, LOAD_CAP_FACTOR="0", LOAD_GATE_FACTOR="0")


class OtHeavy(unittest.TestCase):
    def test_cap_kills_the_command_not_the_host(self):
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "x=bytearray(2*1024**3); print('leak')"],
                           capture_output=True, text=True, env=ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("leak", r.stdout)
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "print('ok')"], capture_output=True, text=True, env=ENV)
        self.assertEqual(r.stdout.strip(), "ok")

    def test_usage(self):
        self.assertEqual(subprocess.run([T, "--", "true"], capture_output=True, env=ENV).returncode, 2)

    def test_no_fixed_slots(self):
        # ot-heavy v2+ (owner 2026-10-12): no fixed slot counts -- memory alone admits, so three small concurrent
        # requests all run at once (the v1 BIG_SLOTS=2 test expected the third to wait for a "slots busy" slot).
        t0 = time.time()
        ps = [subprocess.Popen([T, "--mem", "1", "--", "sleep", "3"], stderr=subprocess.PIPE, text=True, env=ENV) for _ in range(3)]
        errs = [p.communicate()[1] for p in ps]
        self.assertEqual([p.returncode for p in ps], [0, 0, 0], errs)
        self.assertLess(time.time() - t0, 9)
        self.assertFalse(any("slots busy" in e for e in errs))

if __name__ == "__main__":
    unittest.main()
