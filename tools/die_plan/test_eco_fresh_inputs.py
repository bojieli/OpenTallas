"""fresh_inputs stamps a pass dir's kit inputs and leaves run/ alone, so a spill back-copy takes the inputs."""
import os
import tempfile
import unittest
from pathlib import Path

import eco_loop as E


class FreshInputs(unittest.TestCase):
    def test_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "run" / "x").mkdir(parents=True)
            (d / "sub").mkdir()
            for f in (d / "config.mk", d / "sub" / "a.tcl", d / "run" / "x" / "6_final.odb"):
                f.write_text("x")
                os.utime(f, (1000, 1000))
            E.fresh_inputs(d)
            self.assertGreater((d / "config.mk").stat().st_mtime, 1000)
            self.assertGreater((d / "sub" / "a.tcl").stat().st_mtime, 1000)
            self.assertEqual((d / "run" / "x" / "6_final.odb").stat().st_mtime, 1000)


if __name__ == "__main__":
    unittest.main()
