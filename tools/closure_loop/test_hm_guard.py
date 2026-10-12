"""HM-GUARD (2026-10-08): the route-time hold-margin auto-reduction decision (tools/orfs_hold_mm.tcl ot_hm_decide /
ot_hm_buffers, run under tclsh) and the loop's event parsing."""
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl

TCL = cl.HERE.parent / "orfs_hold_mm.tcl"


def tcl(expr):
    # source only the pure procs (the rest of the file needs OpenROAD); ot_env_num is pure too
    src = TCL.read_text()
    procs = []
    for name in ("ot_env_num", "ot_hm_buffers", "ot_hm_decide"):
        i = src.index(f"proc {name} ")
        j = src.index("\nproc ", i + 1)
        procs.append(src[i:j])
    r = subprocess.run(["tclsh"], input="\n".join(procs) + f"\nputs [{expr}]\n", capture_output=True, text=True, check=True)
    return r.stdout.split()


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class HmDecideTests(unittest.TestCase):
    def decide(self, hm, worst, n, buffers, core=67000.0, area=0.08):
        out = tcl(f"ot_hm_decide {hm} {worst} {n} {buffers} {core} {area} 10000 8.0 10.0")
        return float(out[0]), float(out[1])

    def test_rx128_flood_real_hold_passes(self):
        # qfd_link_rx128: 72,493 endpoints inside 50 ps, real FF ws +2.85 -> floor 10
        new, pts = self.decide(50, 2.85, 72493, 146000)
        self.assertEqual(new, 10.0)
        self.assertGreater(pts, 8.0)

    def test_s81_rootcam_small_real_violation(self):
        # S81 PQ root CAM: 17,152 endpoints, real FF ws -4.97 -> 14.97 + round up -> 15.0
        new, _ = self.decide(50, -4.97, 17152, 21700, core=17700.0)
        self.assertAlmostEqual(new, 15.0)

    def test_area_trigger_below_endpoint_limit(self):
        # 6,000 endpoints but 20k projected buffers in a 17.7k um2 core (+9 pts) -> reduce
        new, pts = self.decide(50, 1.0, 6000, 20000, core=17700.0)
        self.assertEqual(new, 10.0)
        self.assertGreater(pts, 8.0)

    def test_small_block_keeps_margin(self):
        new, _ = self.decide(50, -3.0, 800, 1200)
        self.assertEqual(new, 50.0)

    def test_deep_real_violation_never_raises_margin(self):
        # VM8-like: real FF ws -128.7 -> violation + floor exceeds HM: keep HM (real repair, not a margin flood)
        new, _ = self.decide(50, -128.7, 13700, 102000)
        self.assertEqual(new, 50.0)

    def test_margin_at_floor_untouched(self):
        new, _ = self.decide(10, 2.0, 50000, 60000)
        self.assertEqual(new, 10.0)

    def test_buffer_projection(self):
        # deficits 50-2.85=47.15 -> 3, 50-30=20 -> 1, 50-49=1 -> 1, 60 >= hm -> 0
        self.assertEqual(int(tcl("ot_hm_buffers {2.85 30 49 60} 50 20")[0]), 5)


class HmEventTests(unittest.TestCase):
    def test_lines_and_dedup(self):
        rpt = "OT_HM_AUTO stage=cts HM auto-reduced 50->10: 72493 endpoints in margin (worst FF hold 2.85)\n"
        self.assertEqual(cl.hm_auto_lines(rpt), ["stage=cts HM auto-reduced 50->10: 72493 endpoints in margin (worst FF hold 2.85)"])
        j = dict(name="x", host="h", run="/r", attempt=1)
        with patch.object(cl, "ssh", Mock(return_value=Mock(stdout=rpt))), patch.object(cl, "log"):
            cl.hm_auto_events(j)
            cl.hm_auto_events(j)
        self.assertEqual(len([e for e in j["events"] if "HM auto-reduced 50->10" in e]), 1)


if __name__ == "__main__":
    unittest.main()
