"""KW-FIX-44 11-10 (COORD): face_flops.tcl skips control ports (reset / clock) and can spread face registers over a
depth band (OT_FF_DEPTH_BAND_UM).  The Tcl pieces run in tclsh (skipped where tclsh is absent)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

FF = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()


def tcl(body):
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, timeout=30).stdout.split()


def piece(pat):
    m = re.search(pat, FF, re.S | re.M)
    assert m, pat
    return m.group(0)


@unittest.skipUnless(shutil.which("tclsh"), "no tclsh")
class Ctl(unittest.TestCase):
    RE = piece(r"^set ff_ctl_re \{.*?\}$")

    def matches(self, names):
        return tcl(self.RE + "\nforeach n {" + " ".join(names) + "} { puts [regexp $ff_ctl_re $n] }\n")

    def test_reset_and_clock_ports_skipped(self):
        names = ["rst_n", "rst", "arst_n", "sys_rst_n", "core_reset_n", "clk", "clk_cp", "clk_rst", "clk_n", "mem_clk",
                 "ref_clk_p"]
        self.assertEqual(self.matches(names), ["1"] * len(names))

    def test_data_ports_kept(self):
        names = ["cfg_v", "mv_fault", "clk_en_q", "rst_cnt[3]", "din[0]", "u_clkgate_en", "reset_done", "first"]
        self.assertEqual(self.matches(names), ["0"] * len(names))

    def test_skip_is_applied_in_the_port_loop(self):
        self.assertIn("if {[regexp $ff_ctl_re $nm] || [ff_is_clock_port [$bt getNet]]} { incr ff_ctl; continue }", FF)


@unittest.skipUnless(shutil.which("tclsh"), "no tclsh")
class Band(unittest.TestCase):
    PROC = piece(r"^proc ff_depths \{face step\} \{.*?^\}$")

    def depths(self, band_um, n, step=270):
        body = (f"set ff_band_um {band_um}\nset ff_dbu 1000\nset ff_bandk {{}}\n" + self.PROC +
                f"\nfor {{set i 0}} {{$i < {n}}} {{incr i}} {{ puts [lindex [ff_depths N {step}] 0] }}\n")
        return [int(x) for x in tcl(body)]

    def test_off_is_unchanged(self):
        self.assertEqual(self.depths(0, 5), [0, 0, 0, 0, 0])

    def test_band_rotates_start_depth(self):
        # 1.08 um band / 0.27 um rows = 4 depth slots
        self.assertEqual(self.depths(1.08, 6), [0, 1, 2, 3, 0, 1])

    def test_order_covers_band_then_inward(self):
        body = ("set ff_band_um 0.81\nset ff_dbu 1000\nset ff_bandk {N 1}\n" + self.PROC +
                "\nputs [lrange [ff_depths N 270] 0 5]\n")
        self.assertEqual([int(x) for x in tcl(body)], [1, 2, 0, 3, 4, 5])


if __name__ == "__main__":
    unittest.main()
