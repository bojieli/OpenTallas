"""stale-sheets 2026-10-08: a budget pinned to a sheets_ref older than the 2026-10-07 make_block_sdc fix must still get
main's generator (vclk-only latency + set_propagated_clock in budget_signoff.sdc); the old output is refused."""
import subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as cl

OLD_REF = "05d995e9b"          # drive-1613: swiglu lane sheets pinned before ce52a512a
MASTER = "ot_dsrom_su_swiglu_lane"


class StaleSheets(unittest.TestCase):
    def test_old_ref_gets_main_generator(self):
        if subprocess.run(["git", "-C", str(cl.REPO), "cat-file", "-e", OLD_REF]).returncode:
            self.skipTest("old ref not in the object store")
        f = cl.budget_files(dict(master=MASTER, sheets_ref=OLD_REF))
        so = f["budget_signoff.sdc"]
        self.assertIsNone(cl.IDEAL_SIGNOFF_RE.search(so))
        self.assertRegex(so, r"set_clock_latency [0-9.]+ \[get_clocks vclk\]")
        self.assertIn("set_propagated_clock [get_clocks {core_clk}]", so)
        self.assertEqual(f["_ref"], cl.git("rev-parse", OLD_REF).stdout.strip())   # the sheet stays pinned

    def test_pattern(self):
        self.assertTrue(cl.IDEAL_SIGNOFF_RE.search("set_clock_latency 429 [get_clocks {core_clk vclk}]"))
        self.assertTrue(cl.IDEAL_SIGNOFF_RE.search("set_clock_latency 558 [get_clocks {clk_a vclk}]"))
        self.assertIsNone(cl.IDEAL_SIGNOFF_RE.search("set_clock_latency 429 [get_clocks vclk]"))
        self.assertIsNone(cl.IDEAL_SIGNOFF_RE.search("set_clock_latency 429 [get_clocks {vclk}]"))


if __name__ == "__main__":
    unittest.main()
