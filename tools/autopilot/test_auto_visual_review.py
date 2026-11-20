import json, tempfile, unittest
from pathlib import Path
import auto_visual_review as AVR

def rpt(wns, slew, slack=None):
    slack = wns if slack is None else slack
    return (f"detailed place report_worst_slack\n" + "-" * 20 + f"\nworst slack max {wns}\n\n" + "=" * 20 + "\n" +
            "detailed place report_checks -path_delay max\n" + "-" * 20 + "\n"
            "Startpoint: a\nEndpoint: b\nPath Type: max\n"
            f"     1    2.53   33.01   55.10  305.10 v u1/QN (DFFHQNx1)\n"
            f"                 {slew}   83.69  609.42 ^ wire1/A (BUFx12f)\n"
            f"                               {slack}   slack (VIOLATED)\n"
            "Startpoint: c\nEndpoint: d\nPath Type: max\n"
            f"                  50.0   10.00  100.00 ^ u2/A (BUFx12f)\n"
            f"                               5.0   slack (MET)\n"
            "detailed place report_checks -unconstrained\n")

def info(wns, slew=100.0, cells=0, dp=("Total Placement Failures:          0",), macro=()):
    return dict(rpt=rpt(wns, slew), cells_on_macros=cells, dp=list(dp), macro=list(macro),
                scan=dict(over_reach=3, need_station=1, bits_over_cycle=7, max_um=500))

class Auto(unittest.TestCase):
    def test_parse(self):
        r = AVR.parse_report(rpt(-391.19, 263.18))
        self.assertEqual((r["wns"], r["worst_slew"], r["paths"]), (-391.19, 263.18, 2))
        self.assertEqual(AVR.parse_report(None)["wns"], None)

    def test_classes(self):
        self.assertEqual(AVR.decide(info(-61))[0], "ACCEPT")
        self.assertEqual(AVR.decide(info(-300))[0], "SETUP")
        self.assertEqual(AVR.decide(info(-700, 150))[0], "SETUP")
        c, why, _ = AVR.decide(info(-700, 1400))
        self.assertEqual(c, "SLEW-LIMITED"); self.assertIn("e7ebced0c4e", why)
        self.assertEqual(AVR.decide(info(-61, cells=4))[0], "ILLEGAL")
        self.assertEqual(AVR.decide(info(-61, dp=("Total Placement Failures:          3",)))[0], "ILLEGAL")
        self.assertEqual(AVR.decide(info(-61, macro=("macro A overlap macro B",)))[0], "ILLEGAL")
        self.assertEqual(AVR.decide(info(-61, macro=("nonoverlapping bands",)))[0], "ACCEPT")
        self.assertEqual(AVR.decide(info(-61, dp=("[INFO DPL-0311] Found 0 overlaps between adjacent cells.",)))[0], "ACCEPT")
        self.assertEqual(AVR.decide(info(-61, dp=("[ERROR] Found 3 overlaps between adjacent cells.",)))[0], "ILLEGAL")
        d = info(-61); d["rpt"] = None
        self.assertEqual(AVR.decide(d)[0], "NODATA")

    def test_pass_writes_accept_only(self):
        coord = Path(tempfile.mkdtemp()); (coord / "lanes").mkdir()
        mk = lambda it, a: {"die": "s81", "item": it, "attempt": a, "status": "ROUTE-HELD", "kit": f"h:/k/{it}",
                            "route_hold": "WAIT-VISUAL: record a GEOM VERDICT"}
        st = {"items": {"s81|a|1": mk("a", 1), "s81|b|2": mk("b", 2), "s81|c|3": mk("c", 3),
                        "s81|d|4": dict(mk("d", 4), status="ENQUEUED")}}
        infos = {"h:/k/a": info(-80), "h:/k/b": info(-900, 100), "h:/k/c": info(-900, 2000)}
        cnt = AVR.auto_review_pass({}, st, lambda c, r: True, lambda r: r["kit"], info_fn=lambda k: infos[k],
                                   coord=coord, commit=False)
        self.assertEqual((cnt["ACCEPT"], cnt["SETUP"], cnt["SLEW_LIMITED"]), (1, 1, 1))
        self.assertEqual(len(st["auto_review"]), 3)
        # commit path writes the files (coord-commit.sh absent -> ignored)
        AVR._publish(coord, ["- x GEOM VERDICT line"], ["s81\tb\t2\tSETUP\tr\t-900\t100\th:/k/b"])
        self.assertIn("GEOM VERDICT", (coord / "lanes/GEOM-REVIEW.md").read_text())
        self.assertIn("SETUP", (coord / "lanes/AUTO-REVIEW-HELD.tsv").read_text())
        # second pass judges nothing again
        cnt2 = AVR.auto_review_pass({}, st, lambda c, r: True, lambda r: r["kit"], info_fn=lambda k: infos[k],
                                    coord=coord, commit=False)
        self.assertEqual(sum(cnt2.values()), 0)

    def test_line_parses_as_exact_verdict(self):
        import kit_wave as KW
        rec = {"die": "s81", "item": "t1", "attempt": 5}
        ln = AVR.verdict_line(rec, "epyc2:/srv/x/y", "placement legal, wns -61 ps", {"over_reach": 2, "bits_over_cycle": 3})
        self.assertEqual(KW.parse_visual_line(ln), ("s81", "t1", 5, "ISSUES-ACCEPT"))
        self.assertIn("kit=epyc2:/srv/x/y", ln)

if __name__ == "__main__":
    unittest.main()
