#!/usr/bin/env python3
"""reset_taps.tcl: only the shallowest .rst_n nets are the partition's leaf alias (DIE-QC-73 11-05, QC st_a)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

TCL = Path(__file__).with_name("reset_taps.tcl").read_text()
BLOCK = re.search(r"if \{\[llength \$rt_zero_aliases\] > 1\} \{\n.*?\n\}\n", TCL, re.S).group(0)


@unittest.skipIf(shutil.which("tclsh") is None, "tclsh not installed")
class Alias(unittest.TestCase):
    def run_block(self, names):
        code = ""
        for n in names:
            code += f'proc net{len(code)} {{getName}} {{return {{{n}}}}}\n'
        cmds = re.findall(r"proc (net\d+)", code)
        script = code + f"set rt_zero_aliases {{{' '.join(cmds)}}}\n" + BLOCK + \
            'puts [lmap a $rt_zero_aliases {$a getName}]\n'
        return subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True).stdout.strip()

    def test_child_nets_dropped(self):
        got = self.run_block(["u_bound.rst_n", "u_bound.u_u_r0.g_ws[0].u_d.u_r.rst_n", "u_bound.u_x.rst_n"])
        self.assertEqual(got, "u_bound.rst_n")

    def test_single_alias_unchanged(self):
        self.assertEqual(self.run_block(["u_bound.rst_n"]), "u_bound.rst_n")

    def test_equal_depth_stays_ambiguous(self):
        self.assertEqual(self.run_block(["u_a.rst_n", "u_b.rst_n"]), "u_a.rst_n u_b.rst_n")


if __name__ == "__main__":
    unittest.main()
