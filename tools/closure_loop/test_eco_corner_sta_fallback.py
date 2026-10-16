"""drive-1010 2026-10-10: ECO sign-off STA falls back to the shipped corner_sta.py for a pre option-B snapshot."""
import pathlib
import subprocess
import tempfile
import unittest

import closure_loop as cl

HERE = pathlib.Path(__file__).resolve().parent


def csta(script, has_setup_tt, helper=True):
    line = next(l for l in (HERE / script).read_text().splitlines() if l.startswith("CSTA="))
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "src/tools/w18").mkdir(parents=True)
    (d / "src/tools/w18/corner_sta.py").write_text("x = 'setup_tt'\n" if has_setup_tt else "x = 'setup_ss'\n")
    (d / "cl").mkdir()
    if helper:
        (d / "cl/corner_sta.py").write_text("x = 'setup_tt'\n")
    (d / "cl/probe.sh").write_text(line + '\necho "$CSTA"\n')
    return subprocess.run(["bash", str(d / "cl/probe.sh")], cwd=d / "src", capture_output=True, text=True).stdout.strip(), d


class CornerStaFallback(unittest.TestCase):
    def test_scripts(self):
        for s in ("hold_eco.sh", "vtswap_eco.sh"):
            out, _ = csta(s, True)
            self.assertEqual(out, "tools/w18/corner_sta.py")
            out, d = csta(s, False)
            self.assertEqual(out, str(d / "cl/corner_sta.py"))
            out, _ = csta(s, False, helper=False)
            self.assertEqual(out, "tools/w18/corner_sta.py")
            self.assertNotIn("python3 tools/w18/corner_sta.py", (HERE / s).read_text())

    def test_helper_shipped(self):
        self.assertIn("../w18/corner_sta.py", cl.HELPERS)
        self.assertTrue((HERE / "../w18/corner_sta.py").exists())


if __name__ == "__main__":
    unittest.main()
