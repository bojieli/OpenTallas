import json, tempfile, unittest
from pathlib import Path
import rst_spread_placed as R
import auto_visual_review as AVR


def geom(rn=False, spread=1500.0, macro_at=None):
    """root flop (id 1) -> net -> 3 buffers (ids 10..12) at 0 / spread/2 / spread um -> leaf nets of 10 DFFASR flops each"""
    L = ["D\t0\t0\t2000\t300", "R\t0\t0\t2000\t300"]
    L.append("C\t1\tS\tDFFHQNx1_ASAP7_75t_R\t5.0\t5.4\t6.0\t5.67\tu_xrl_q")
    ids = {}
    nid = 100
    rnrows, nrows = [], []
    sinks_root = []
    for k, x in enumerate((10.0, spread / 2, spread)):
        b = 10 + k
        L.append(f"C\t{b}\tB\tBUFx4_ASAP7_75t_R\t{x}\t10.8\t{x + 0.5}\t11.07\tbuf{k}")
        sinks_root.append(f"i{b}")
        leaf = []
        for j in range(10):
            nid += 1
            L.append(f"C\t{nid}\tS\tDFFASRHQNx1_ASAP7_75t_R\t{x + 2 + 2 * j}\t100.0\t{x + 3 + 2 * j}\t100.27\tg{k}/r{j}")
            leaf.append(nid)
        nrows.append("N\tSIGNAL\ti%d\t%s" % (b, "\t".join(f"i{n}" for n in leaf)))
        rnrows.append(f"RN\tn_leaf{k}\ti{b}\t" + "\t".join(f"i{n}:RESETN" for n in leaf))
    nrows.append("N\tSIGNAL\ti1\t" + "\t".join(sinks_root))
    rnrows.append("RN\tu_xrl_q_o\ti1\t" + "\t".join(f"{s}:A" for s in sinks_root))
    if macro_at:
        L.append("C\t900\tM\tSRAM\t%s\t%s\t%s\t%s\tsram0" % macro_at)
    p = Path(tempfile.mkdtemp()) / "geom.tsv"
    p.write_text("\n".join(L + nrows + (rnrows if rn else [])) + "\n")
    return str(p)


class Spread(unittest.TestCase):
    def test_tree_flagged_legacy_and_rn(self):
        for rn in (False, True):
            g, res = R.analyse(geom(rn=rn))
            self.assertEqual(len(res), 1, rn)
            r = res[0]
            self.assertEqual(r["fanout"], 30)
            self.assertGreater(r["hpwl_um"], 1400)
            self.assertGreater(r["far_um"], 1400)
            self.assertEqual(r["regions"], 3)
            self.assertEqual(sorted(r["flags"]), ["far", "hpwl"])
            self.assertEqual(r["src"], "RN" if rn else "LEGACY")

    def test_compact_net_not_flagged(self):
        g, res = R.analyse(geom(spread=60.0))
        self.assertEqual(res[0]["flags"], [])
        self.assertEqual(R.summary(res)["flagged"], 0)

    def test_proposal_one_relay_per_region_legal(self):
        path = geom(macro_at=(740, 0, 760, 300))      # macro column across the middle region: seat must dodge it
        g, res = R.analyse(path)
        p = R.proposal(g, res)
        n = p["nets"][0]
        self.assertEqual(len(n["relays"]), 3)
        self.assertEqual(len(n["rehome"]), 30)
        self.assertEqual({h["to_relay"] for h in n["rehome"]}, {r["name"] for r in n["relays"]})
        grid = R.Grid(g)
        for r in n["relays"]:
            self.assertIsNotNone(r["x"])
            self.assertTrue(grid._free(r["row"], r["x"], R.RELAY_W), r)
            self.assertFalse(740 - R.RELAY_W < r["x"] < 760, r)
            self.assertEqual(len(r["sinks"]), 10)
        json.dumps(p)

    def test_sink_inside_macro_counted(self):
        g, res = R.analyse(geom(macro_at=(745, 90, 800, 120)))
        self.assertGreater(res[0]["in_macro"], 0)

    def test_fanout_threshold(self):
        self.assertEqual(R.FANOUT, 3000)
        self.assertEqual((R.FAR_UM, R.HPWL_UM, R.REACH_UM), (405.0, 900.0, 405.0))

    def test_review_section_report_only(self):
        g, res = R.analyse(geom())
        s = R.summary(res)
        info = dict(rpt="detailed place report_worst_slack\n----\nworst slack max -10\n", cells_on_macros=0, dp=["Total Placement Failures: 0"],
                    macro=[], scan={}, rst_spread=s)
        cls, why, facts = AVR.decide(info)
        self.assertNotEqual(cls, "ILLEGAL")                      # report-only: never changes the class
        self.assertIn("RST-SPREAD (report-only) 1/1", AVR.rst_line(facts))
        rec = dict(die="s81", item="a", attempt=1)
        self.assertIn("RST-SPREAD", AVR.verdict_line(rec, "h:/k", why, facts))
        info2 = dict(info, rst_spread=None)
        self.assertEqual(AVR.decide(info2)[0], cls)
        self.assertEqual(AVR.rst_line(AVR.decide(info2)[2]), "")


if __name__ == "__main__":
    unittest.main()
