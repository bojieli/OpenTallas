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

    def test_literal_entries_preserve_intra_tile_and_specific_branches(self):
        with open(self.f, 'a') as f:
            f.write('T\tm0/clk2\tmaster\t900\t800\tb2/Y\t1500\t1490\n')
        pj = os.path.join(self.d, 'entries.json')
        with open(pj, 'w') as f:
            json.dump({'entry_pairs': [['m0/clk', 'm0/clk2', 'same domain'],
                                       ['m0/clk2', 'm2/clk'], ['m0/missing', 'm2/clk']]}, f)
        r = D.report(self.f, pj)
        exact = [p for p in r['pairs'] if p['source'] == 'literal_entry_list']
        self.assertEqual(len(exact), 2)
        p = next(p for p in exact if p['a'] == 'm0/clk2')
        self.assertEqual((p['entry_a'], p['entry_b'], p['lca']), ('m0/clk2', 'm2/clk', 'b2/Y'))
        self.assertEqual(r['noncommon']['unmatched_pairs'], 1)

    def test_strict_refuses_nearest_entry_inference(self):
        with open(self.f, 'a') as f:
            f.write('T\tm0/clk2\tmaster\t900\t800\tb2/Y\t1500\t1490\n')
        with self.assertRaisesRegex(ValueError, 'ambiguous timed pair'):
            D.report(self.f, strict_entry_pairs=True)
        # Keep only exact timed pairs: nearest geometry is not their source of truth.
        with open(self.f, 'w') as f:
            f.write(DUMP.replace('P\tm0\tm1\tr0[0]\n', '').replace('P\tm1\tm2\tr1[0]\n', ''))
            f.write('T\tm0/clk2\tmaster\t900\t800\tb2/Y\t1500\t1490\n')
        pj = os.path.join(self.d, 'strict.json')
        with open(pj, 'w') as f:
            json.dump({'entry_pairs': [['m0/clk', 'm2/clk']]}, f)
        r = D.report(self.f, pj, strict_entry_pairs=True)
        self.assertEqual(r['pairs'][0]['entry_a'], 'm0/clk')
        with open(pj, 'w') as f:
            json.dump({'entry_pairs': [['m0/absent', 'm2/clk']]}, f)
        with self.assertRaisesRegex(ValueError, 'missing entries'):
            D.report(self.f, pj, strict_entry_pairs=True)



NB = ("R\tpll/a\t0\t0\t-\t-\nR\tpll/b\t0\t0\t-\t-\nR\tpll/h\t0\t0\t-\t-\n"
      "B\tdc_W0_a_B1/Y\tBUFx24_ASAP7_75t_R\t10\t10\tpll/a\t1000\t900\n"
      "B\tdc_E0_b_B1/Y\tBUFx24_ASAP7_75t_R\t20\t10\tpll/b\t1050\t960\n"
      "B\tdc_E1_b_B1/Y\tBUFx24_ASAP7_75t_R\t20\t20\tpll/b\t1300\t1100\n"
      "B\tdc_hb_B1/Y\tBUFx24_ASAP7_75t_R\t20\t20\tpll/h\t3000\t2900\n"
      "T\tt0/ck\tm\t10\t10\tdc_W0_a_B1/Y\t1000\t900\nT\tt1/ck\tm\t20\t10\tdc_E0_b_B1/Y\t1050\t960\n"
      "T\tt2/ck\tm\t20\t20\tdc_E1_b_B1/Y\t1300\t1100\nT\tt3/ck\tm\t20\t20\tdc_hb_B1/Y\t3000\t2900\n"
      "P\tt0\tt1\tn1\nP\tt1\tt2\tn2\nP\tt2\tt3\tn3\n")


class NeighbourCheck(unittest.TestCase):
    """owner 2026-10-16 neighbour-relative clocking: communicating pairs judged against the budget per class, async
    families listed not judged, no FF dump -> INCOMPLETE; cross-root pairs of one family are still synchronous."""
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.f = os.path.join(self.d, "tt.tsv"); open(self.f, "w").write(NB)
        self.ff = os.path.join(self.d, "ff.tsv"); open(self.ff, "w").write(NB.replace("\t1100\n", "\t1000\n"))
        self.spec = os.path.join(self.d, "spec.json")
        json.dump({"trees": [{"name": "W0_a", "balance_group": "W0"}, {"name": "E0_b", "balance_group": "E0"},
                             {"name": "E1_b", "balance_group": "E1"}, {"name": "hb"}]}, open(self.spec, "w"))
        self.fam = os.path.join(self.d, "fam.json")
        json.dump({"core": ["pll/a", "pll/b"], "hbm": ["pll/h"]}, open(self.fam, "w"))

    def test_classes_and_verdict(self):
        r = D.report(self.f, budget=80, region_map=self.spec, families=self.fam, ff_dump=self.ff)["neighbour_check"]
        c = r["classes"]
        self.assertEqual(c["neighbour:E0|W0"]["pairs"], 1)           # different roots, one family: judged
        self.assertEqual(c["neighbour:E0|W0"]["over"], 0)            # 50 TT / 60 FF
        self.assertEqual(c["neighbour:E0|E1"]["over"], 1)            # 250 TT
        self.assertFalse(c["async:core|hbm"]["judged"])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["worst"][0]["a"], "t1")

    def test_no_ff_is_incomplete(self):
        good = NB.replace("\t1300\t1100\n", "\t1060\t970\n")
        open(self.f, "w").write(good)
        r = D.report(self.f, budget=80, region_map=self.spec, families=self.fam)["neighbour_check"]
        self.assertEqual(r["pairs_over"], 0)
        self.assertEqual(r["verdict"], "INCOMPLETE")
        r = D.report(self.f, budget=80, region_map=self.spec, families=self.fam, ff_dump=self.f)["neighbour_check"]
        self.assertEqual(r["verdict"], "PASS")

if __name__ == "__main__":
    unittest.main()
