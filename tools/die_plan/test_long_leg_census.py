"""long_leg_census: classification, bus grouping and kit selection on synthetic scan rows (no OpenROAD)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_leg_census as L  # noqa: E402


def row(die, tn, legs, slots=(), pats=()):
    return dict(die=die, type=tn, kit=tn + "-route-h-1-1", status="OK", legs=legs, slots=list(slots), patterns=list(pats), macros=[])


def leg(um, la, lb, ma="reg:DFFHQNx1", mb="reg:DFFHQNx1", net="n"):
    return [um, um, la, lb, "D", [0, 0], [um, 0], net, ma, mb]


class T(unittest.TestCase):
    def test_classes(self):
        rows = [row("s81", "serdes__t3", [
            leg(1100, "port:am_ok[3]", "u_bout_am_ok_i0/q", "port", "reg:DFFHQNx1"),          # port + station: a
            leg(900, "port:coll_o0[1]", "u_core.u_x.r_7_", "port", "reg:DFFHQNx1"),             # port + logic: b
            leg(500, "u_core.u_a.r", "u_core.u_b.r"),                                           # logic + logic: c
            leg(700, "u_core.u_a.r", "u_core.u_mem", mb="macro:fakeram"),                      # logic + macro: b
            leg(600, "u_core.u_strap_a", "u_core.u_b.r"),                                       # strap
        ])]
        legs = L.classify_rows(rows)
        self.assertEqual([x["cls"] for x in legs], ["a", "b", "c", "b", "c"])
        self.assertTrue(legs[-1]["strap"])
        self.assertEqual(legs[0]["bus"], "am_ok")
        self.assertEqual(legs[1]["bus"], "coll_o")
        agg = L.aggregate(legs)
        self.assertEqual(sum(r["legs"] for r in agg), 4)          # strap excluded
        self.assertTrue(all(r["owner"] == "FABLE-FIX-S81-SERDES-0000" for r in agg))

    def test_same_bus_across_types(self):
        mk = lambda tn: row("qc", tn, [leg(2149, "port:cbn_q01[2]", "u_lpad_nb_i12.r", "port")])   # noqa: E731
        agg = L.aggregate(L.classify_rows([mk("cbn_q01__a"), mk("cbn_q01__b")]))
        self.assertEqual(len(agg), 1)
        self.assertEqual((agg[0]["types"], agg[0]["worst_um"], agg[0]["cls"]), (2, 2149, "a"))
        self.assertEqual(agg[0]["owner"], "QC-PLAN-R3")

    def test_variant_collapse(self):
        self.assertEqual(L.base_type("col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8"), "col_h9_r0_p3__t1")
        self.assertEqual(L.base_type("serdes__t3"), "serdes__t3")

    def test_off_centre_pin(self):
        # 100 x 40 macro, pin 4 x 4 near the left end: R0 pin at x=6, centre would be x=50
        r = [(4, 18, 8, 22)]
        self.assertEqual(L.pin_centroid(r, "R0", (1000, 500), (100, 40)), (1006.0, 520.0))
        self.assertEqual(L.pin_centroid(r, "MY", (1000, 500), (100, 40)), (1094.0, 520.0))     # mirrored: pin at the right end
        self.assertEqual(L.pin_centroid(r, "R180", (1000, 500), (100, 40)), (1094.0, 520.0))
        x, y = L.pin_centroid(r, "R90", (1000, 500), (100, 40))
        self.assertEqual((x, y), (1000 + 40 - 20, 500 + 6))
        # two shapes: weighted by area
        self.assertEqual(L.pin_centroid([(0, 0, 2, 2), (8, 0, 10, 6)], "R0", (0, 0), (10, 6))[0], (1 * 4 + 9 * 12) / 16)

    def test_changed_by_pin(self):
        far = leg(900, "u_core.u_a.r", "u_core.u_mem", mb="macro:core")
        far.append(467.0)                       # old core-centre measure said 467 um: over 405 either way -> no change
        near = leg(861, "u_core.u_a.r", "u_core.u_m2", mb="macro:core")
        near.append(300.0)                      # old said 300, pin says 861: enters the census
        gone = leg(250, "u_core.u_a.r", "u_core.u_m3", mb="macro:core")
        gone.append(350.0)                      # old 350, pin 250: leaves
        legs = L.classify_rows([row("s81", "hd_lep0N", [far, near, gone])])
        self.assertEqual([x["changed"] for x in legs], ["", "new", "dropped"])
        self.assertEqual(len(L.aggregate(legs)), 2)          # the dropped leg is not counted

    def test_half_cycle(self):
        a = leg(300, "u_core.u_a.r", "u_core.u_b.r") + [300.0, "p", "n"]      # 300 um on a half cycle: over 200
        b = leg(290, "u_core.u_a.r", "u_core.u_c.r") + [290.0, "n", "n"]      # both negedge: full cycle, 290 < 300: not a leg
        c = leg(150, "u_core.u_a.r", "u_core.u_d.r") + [150.0, "p", "n"]      # 150 on half cycle: fine
        legs = L.classify_rows([row("s81", "slice_c", [a, b, c])])
        self.assertEqual([x["cls"] for x in legs], ["h", "c", "h"])
        agg = L.aggregate(legs)
        self.assertEqual(sum(r["legs"] for r in agg), 1)
        self.assertEqual(agg[0]["cls"], "h")

    def test_slack_bins(self):
        legs = []
        eps = {}
        for i in range(120):                       # 120 full-cycle legs at 320 um: slack falls with length
            um = 100 + 4 * i
            nm = f"u.r{i}$_DFF_P_"
            legs.append(leg(um, "u.a", nm) + [um, "p", "p", 0.0, um * 1.2])
            eps[nm + "/D"] = 200.0 - 0.8 * um
        rows = L.slack_rows(legs, eps)
        self.assertEqual(len(rows), 120)
        self.assertAlmostEqual(rows[0][6], 1.2, 3)
        md = L.slack_report(rows, minn=5)
        self.assertIn("median slack crosses 0 ps at: ", md)
        self.assertIn("Routed / placed wire length", md)
        xs = [125.0, 175.0, 225.0]
        self.assertEqual(L.crossing(xs, [50.0, 10.0, -10.0], 0.0), 200.0)

    def test_firm_site_rank(self):
        r = row("s81", "t", [leg(500, "u_bound.u_bin_x_i0/q", "u_core.u_a.r"), leg(500, "u_core.u_a.r", "u_core.u_b.r")])
        self.assertEqual([x["rank1"] for x in L.classify_rows([r])], ["firm-site", ""])

    def test_reset_class(self):
        r = row("s81", "t", [leg(900, "u_bound.u_cland_rst_ft0_i/q", "u_bound.u_cland_origin/s1"), leg(900, "u_core.u_a.r", "u_core.u_b.r")])
        self.assertEqual([x["cls"] for x in L.classify_rows([r])], ["r", "c"])
        agg = L.aggregate(L.classify_rows([r]))
        self.assertEqual(sorted(x["cls"] for x in agg), ["c", "r"])

    def test_slot_row(self):
        r = row("kv", "hg_x", [leg(450, "u_core.u_ft3_i.a", "u_core.b")], slots=["ft3_i"])
        self.assertEqual(L.classify_rows([r])[0]["station_row"], "yes")

    def test_select_newest_placed(self):
        with tempfile.TemporaryDirectory() as d:
            for n, ep in (("t1-route-h-1-100", 100), ("t1-route-h-2-200", 200), ("t2-route-h-3-300", 300)):
                k = Path(d, n)
                (k / "work/run/results/asap7/x/base").mkdir(parents=True)
                (k / "work/config.mk").write_text("")
                (k / "work/budget.json").write_text(json.dumps(dict(die="s81", type=n.split("-")[0])))
                if n != "t2-route-h-3-300":
                    (k / "work/run/results/asap7/x/base/3_place.odb").write_text("x")
            import os
            import time
            for p in Path(d).glob("*/work/run/results/*/*/base/3_place.odb"):
                os.utime(p, (time.time() - 600, time.time() - 600))
            sel = L.select_kits([d])
            self.assertEqual({k: v[0].name for k, v in sel.items()}, {("s81", "t1"): "t1-route-h-2-200"})


if __name__ == "__main__":
    unittest.main()
