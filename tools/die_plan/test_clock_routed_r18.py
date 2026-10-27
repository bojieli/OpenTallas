#!/usr/bin/env python3
"""INFRA-FIRST-QC-R18 clock_routed: explicit-cell (ckt_*) STA dump, tap-port leaves, RCX rules width guard."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_routed as CR  # noqa: E402

RULES = """Metal 7 RESOVER
WIDTH Table 1 entries:  0.032

Metal 8 RESOVER
WIDTH Table 2 entries:  0.04 {w}

Metal 9 RESOVER
WIDTH Table 2 entries:  0.04 {w}
"""


class R18Test(unittest.TestCase):
    def test_sta_tcl_dumps_explicit_cells_and_taps(self):
        s = CR.STA_TCL
        self.assertIn("get_cells -quiet ckt_*", s)
        self.assertIn('puts $fh "A A:$n', s)
        self.assertIn("ckm_d_*", s)                      # mesh builds unchanged
        self.assertIn("/out/tap_loads.tcl", s)

    def test_width_check_flags_016_rules_on_16w(self):
        c = CR.rules_width_check(RULES.format(w="0.16"), "16w")
        self.assertFalse(c["ok"])
        self.assertEqual(c["selected_width_um"], {8: 0.16, 9: 0.16})
        self.assertTrue(CR.rules_width_check(RULES.format(w="0.64"), "16w")["ok"])
        self.assertTrue(CR.rules_width_check(RULES.format(w="0.16"), "4w")["ok"])
        self.assertTrue(CR.rules_width_check(RULES.format(w="0.16"), None)["ok"])

    def test_read_tree_keeps_a_and_t_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.txt"
            p.write_text("N ckt_0_0 10 9 5\nA A:ckt_0_0 8 7 4\nT t_g1 20 19 6\nX t_g2 NA\n")
            T = CR.read_tree(p)
            self.assertEqual(T["ckt_0_0"], (10.0, 9.0, 5.0))
            self.assertEqual(T["A:ckt_0_0"], (8.0, 7.0, 4.0))
            self.assertEqual(T["t_g1"], (20.0, 19.0, 6.0))
            self.assertNotIn("t_g2", T)


if __name__ == "__main__":
    unittest.main()
