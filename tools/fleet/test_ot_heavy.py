"""ot-heavy (fleet rule 2026-10-10): a capped command is killed at its MemoryMax; big slots are exclusive."""
import pathlib
import subprocess
import time
import unittest

T = str(pathlib.Path(__file__).with_name("ot-heavy"))


class OtHeavy(unittest.TestCase):
    def test_cap_kills_the_command_not_the_host(self):
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "x=bytearray(2*1024**3); print('leak')"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("leak", r.stdout)
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "print('ok')"], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "ok")

    def test_usage(self):
        self.assertEqual(subprocess.run([T, "--", "true"], capture_output=True).returncode, 2)

    def test_big_slots_bound_concurrency(self):
        t0 = time.time()
        ps = [subprocess.Popen([T, "--mem", "40", "--", "sleep", "3"], stderr=subprocess.PIPE, text=True) for _ in range(3)]
        errs = [p.communicate()[1] for p in ps]
        self.assertGreaterEqual(time.time() - t0, 5)            # the third waited for a slot (BIG_SLOTS=2)
        self.assertTrue(any("slots busy" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
