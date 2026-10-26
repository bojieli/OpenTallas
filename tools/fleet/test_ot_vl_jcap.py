"""ot-vl-jcap (VL_JCAP_1022): Verilator build -j cap -- detection, cap arithmetic, opt-out, non-Verilator pass-through."""
import pathlib
import subprocess
import sys
import unittest

T = str(pathlib.Path(__file__).with_name("ot-vl-jcap"))


class OtVlJcap(unittest.TestCase):
    def test_selftest(self):
        r = subprocess.run([sys.executable, T, "--selftest"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
