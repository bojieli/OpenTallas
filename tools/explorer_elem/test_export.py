"""explorer_elem_export: the STA preamble is cut from the job's own script (SS libs swapped to TT only on request),
and auto() never raises: a failure lands in its marker."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import explorer_elem_export as X  # noqa: E402

TCL = """read_lef /p/tech.lef
read_liberty /p/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /src/m/rom_ss.lib
read_db /work/results/asap7/x/base/6_final.odb
read_sdc /work/results/asap7/x/base/6_final.sdc
read_spef /work/results/asap7/x/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/signoff.sdc
puts "OT_CORNER ss"
report_checks -path_delay max
"""


class Preamble(unittest.TestCase):
    def test_cut_and_swap(self):
        p = X.preamble(TCL)
        self.assertIn("read_sdc /src/physical/signoff.sdc", p)
        self.assertNotIn("report_checks", p)
        self.assertIn("SS_nldm", p)
        t = X.preamble(TCL, ss2tt=True)
        self.assertIn("RVT_TT_nldm", t)
        self.assertIn("rom_tt.lib", t)

    def test_needs_db_and_spef(self):
        with self.assertRaises(SystemExit):
            X.preamble("read_lef a\nread_db b\nputs x\n")


class AutoNeverRaises(unittest.TestCase):
    def test_missing_job(self):
        d = pathlib.Path(tempfile.mkdtemp())
        with patch.object(X, "MARKS", d / "m"), patch.object(X, "STATE", d / "s"):
            self.assertFalse(X.auto("nojob", dest=d / "out", log=lambda s: None))
            m = json.loads((d / "m" / "nojob.json").read_text())
        self.assertEqual(m["state"], "failed")
        self.assertIn("FileNotFoundError", m["error"])


if __name__ == "__main__":
    unittest.main()
