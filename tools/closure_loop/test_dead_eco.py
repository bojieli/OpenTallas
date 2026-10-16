"""DEAD-ECO (drive-1010 2026-10-10): an unfinished ECO output dir is moved aside; a finished one is preserved."""
import pathlib
import re
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent


def guard(script):
    s = (HERE / script).read_text()
    i = s.index('if [ -e "$OUT" ]; then')
    return s[i:s.index("\nfi", i) + 3]


class DeadEco(unittest.TestCase):
    def run_guard(self, script, finished):
        d = pathlib.Path(tempfile.mkdtemp()); out = d / "eco-x"; out.mkdir()
        if finished:
            (out / "result.json").write_text("{}")
        r = subprocess.run(["bash", "-c", f'OUT={out}\n' + guard(script) + "\necho CONTINUE"], capture_output=True, text=True)
        return r, out, d

    def test_both_scripts(self):
        for s in ("hold_eco.sh", "vtswap_eco.sh"):
            r, out, d = self.run_guard(s, finished=False)
            self.assertIn("CONTINUE", r.stdout)
            self.assertFalse(out.exists())
            self.assertEqual(len([p for p in d.iterdir() if p.name.startswith("eco-x.dead-")]), 1)
            r, out, d = self.run_guard(s, finished=True)
            self.assertEqual(r.returncode, 10)
            self.assertTrue((out / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
