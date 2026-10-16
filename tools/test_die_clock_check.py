"""tools/die_clock_check.py on a real OpenROAD dump (3 SRAM macros, 3 BUFx24, ASAP7 TT, estimate_parasitics -placement;
produced by tools/die_clock_check.tcl in the orfs asap7lock image, ROOT 2026-10-16)."""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import die_clock_check as D

DUMP = 'R\tport:clk\t700.044\t0.042\t-\t-\nB\tb0/Y\tBUFx24_ASAP7_75t_R\t700.810\t700.135\tport:clk\t1108.575317\t1098.295288\nB\tb2/Y\tBUFx24_ASAP7_75t_R\t1000.810\t700.135\tb0/Y\t1361.661133\t1346.963501\nT\tm2/clk\tot_sram_1r1w_128x256_m1_r2c2\t900.012\t800.780\tb2/Y\t1462.929077\t1448.212280\nB\tb1/Y\tBUFx24_ASAP7_75t_R\t300.810\t700.135\tb0/Y\t1520.360718\t1504.091553\nT\tm1/clk\tot_sram_1r1w_128x256_m1_r2c2\t100.012\t800.780\tb1/Y\t2125.509033\t2109.241211\nT\tm0/clk\tot_sram_1r1w_128x256_m1_r2c2\t100.012\t100.780\tb1/Y\t2750.239502\t2733.973633\nP\tm0\tm1\tr0[0]\nP\tm1\tm2\tr1[0]\nS\troots\t1\nS\tclock_nets\t4\nS\tclock_cells\t3\nS\ttile_entries\t3\nS\tdie_flops\t0\nS\ttile_pairs\t2\nS\tbroadcast_nets_skipped\t0\nS\tmax_fanout\t8\nS\tsta\t1\n'


class DieClockCheck(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.f = os.path.join(self.d, "dump.tsv")
        open(self.f, "w").write(DUMP)

    def test_insertion_and_noncommon(self):
        r = D.report(self.f)
        self.assertEqual(r["counts"]["tiles"], 3)
        self.assertEqual(r["counts"]["clock_cells"], 3)
        t = {x["entry"]: x for x in r["tiles"]}
        self.assertAlmostEqual(t["m0/clk"]["sta_max_ps"], 2750.239502, places=3)
        self.assertEqual(t["m0/clk"]["levels"], 2)
        p = {(x["a"], x["b"]): x for x in r["pairs"]}
        # m0/m1 share b1's output net: the non-common path is each side's wire from b1/Y
        self.assertEqual(p[("m0", "m1")]["lca"], "b1/Y")
        self.assertAlmostEqual(p[("m0", "m1")]["sta_ps"], 2750.2 - 1520.4, delta=0.2)
        # m1/m2 branch at b0/Y
        self.assertEqual(p[("m1", "m2")]["lca"], "b0/Y")
        self.assertAlmostEqual(p[("m1", "m2")]["sta_skew_ps"], 662.6, delta=0.1)
        self.assertIsNone(r["threshold"])

    def test_bus_list_pairs_and_cli(self):
        pj = os.path.join(self.d, "pairs.json")
        json.dump({"pairs": [["m0", "m2", "bus x"], ["m0", "nope"]]}, open(pj, "w"))
        out = os.path.join(self.d, "r.json")
        txt = subprocess.run([sys.executable, os.path.join(HERE, "die_clock_check.py"), "report", self.f, "--out", out,
                              "--pairs", pj], capture_output=True, text=True, check=True).stdout
        self.assertIn("non-common pairs 3", txt)
        r = json.load(open(out))
        self.assertEqual(r["noncommon"]["unmatched_pairs"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.d, "r.txt")))
        self.assertEqual([x["lca"] for x in r["pairs"] if x["a"] == "m0" and x["b"] == "m2"], ["b0/Y"])


if __name__ == "__main__":
    unittest.main()
