import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import qwen_slab_fanout as f
import qwen_slab_fanout_run as run

class FanoutTest(unittest.TestCase):
    def test_north_bank_halo_and_fences(self):
        for n,h in f.HEIGHTS.items():
            r=f.recipe("capture",n);lo,hi=r["capture"]["fence_y_um"]
            self.assertGreaterEqual(lo,f.share.rows(h)[-1]+f.share.ROM_H+f.share.EDGE)
            self.assertGreater((hi-lo)*(f.share.W-40-f.share.EDGE)/4,128*.2916/.5)
            text=f.capture_tcl(n)
            self.assertIn(f"macro_place_h{h:g}.tcl",text)
            self.assertIn(f"{lo:g}*$cap_dbu",text)
            self.assertIn("capture FF census !=512",text)
    def test_finite_constraints_no_parent_admission(self):
        sdc=(f.ROOT/"physical/qwen_slab_fanout/finite_boundary.sdc").read_text()
        self.assertNotIn("set_false_path",sdc)
        self.assertIn("set_load 5.55848 [all_outputs]",sdc)
        self.assertIn("set_clock_uncertainty -setup 60",sdc)
        self.assertIn("set_clock_uncertainty -hold 25",sdc)
        for k in f.KINDS:
            for n in f.HEIGHTS:
                r=f.recipe(k,n)
                self.assertFalse(r["full_native_parent_admission"])
                self.assertEqual(r["finite_service"]["total_credits"],9)
                self.assertGreater(r["port_capacity"]["right_tw_gross_tracks"],514)
    def test_launch_limits_and_no_false_path(self):
        for k in f.KINDS:
            for n in f.HEIGHTS:
                argv=run.command(f.recipe(k,n),Path('/tmp/unused'))
                for flag in ('--synth-timeout-seconds','--flow-timeout-seconds'):
                    self.assertEqual(argv[argv.index(flag)+1],"unlimited")
                self.assertNotIn('--false-path-io',argv)
                self.assertNotIn('--false-path-from',argv)
                self.assertIn('BW_FIFO=1',argv)
                self.assertIn('NUM_CORES=16',argv)
    def test_reject_unnamed_recipes(self):
        for k,n in [('capture',571),('padding',570),('twoface',341)]:
            with self.assertRaises(ValueError):f.recipe(k,n)

if __name__=='__main__':unittest.main()
