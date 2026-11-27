"""REPORT-ONLY fill_corridor (COORD 2026-11-27 ruling 7, C-SPARSE-OUTLINE): definition, eligibility, and the proof that the raw
fill gate and every verdict are unchanged."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geom_corridor as GC  # noqa: E402
import geom_rules as G  # noqa: E402
from test_auto_geom import dump  # noqa: E402


def ctype(W=100.0, H=100.0, band=(40, 40, 60, 60), **kw):
    t = dict(outline_um=[W, H], contents=[], _die="qwen_compute", _type="x", _plan_sha256="ab" * 32, ft_slots=[dict(name="s", in_face="E", out_face="W", width=1, stations=1)],
             clock=dict(landing_contract=dict(collector_tree={"root": [0, 0]}, bands={"b": dict(rect_um=list(band))})))
    t.update(kw)
    return t


PINS = [(0, y) for y in range(0, 101, 2)] + [(100, y) for y in range(0, 101, 2)]    # W and E faces, full height and width


class Geometry(unittest.TestCase):
    def test_union_counts_overlap_once_and_tests_points(self):
        u = GC.Union([(0, 0, 10, 10), (5, 5, 15, 15), (20, 0, 30, 5)])
        self.assertAlmostEqual(u.area, 100 + 100 - 25 + 50)
        self.assertTrue(u.contains(12, 12) and u.contains(25, 2) and u.contains(1, 1))
        self.assertFalse(u.contains(17, 12) or u.contains(25, 7) or u.contains(-1, 0))
        self.assertEqual(GC.Union([]).area, 0.0)

    def test_declared_corridor_kinds_clip_and_site_footprint(self):
        t = ctype(band=(-10, 0, 20, 10))
        t["clock"]["landing_contract"]["group_rects_um"] = {"g": [50, 50, 52, 52], "bad": [1, 1]}
        t["ft_slots"][0].update(bit_site_cell_um=[1.0, 0.5], bit_sites_um=[[[10, 10], [10, 11], [10, 12]], []])
        r = {k: (x0, y0, x1, y1) for k, x0, y0, x1, y1 in GC.corridor_rects(t)}
        self.assertEqual(r["landing_band"], (0.0, 0.0, 20.0, 10.0))            # clipped to the outline
        self.assertEqual(r["landing_group"], (50.0, 50.0, 52.0, 52.0))        # malformed rect dropped
        self.assertEqual(r["routing_station"], (10.0, 10.0, 11.0, 12.5))      # sites bbox + cell, empty station skipped
        self.assertEqual(len(GC.corridor_rects(t)), 3)
        self.assertIsNone(GC._rect([float("nan"), 0, 10, 10], 100, 100))       # non-finite is dropped, not full-width
        self.assertAlmostEqual(GC.Union([(0, 0, 10, 10)]).overlap((5, 5, 25, 25)), 25.0)
        self.assertEqual(GC.Union([(0, 0, 10, 10)]).overlap((10, 0, 12, 5)), 0.0)

    def test_pin_landing_strips_per_pin_intervals(self):
        pins = [(0, 10), (0, 90), (20, 0), (50, 50)]
        st = {tuple(x[1:]) for x in GC.pin_strips(pins, 100, 100)}
        self.assertEqual(st, {(0.0, 0.0, 30.0, 40.0), (0.0, 60.0, 30.0, 100.0), (0.0, 0.0, 50.0, 30.0)})  # gap 40..60 not corridor
        self.assertEqual(GC.pin_strips([(50, 50)], 100, 100), [])               # interior pin
        self.assertEqual(len(GC.pin_strips([(0, 50)], 100, 100)), 1)            # a single pin still gets a strip

    def test_constants_match_geom_rules(self):
        self.assertEqual(GC.PIN_STRIP_UM, G.PINREG_P90)
        self.assertEqual(GC.OUTLINE_TOL, G.OUTLINE_TOL)
        self.assertEqual(GC.FACE_TOL_UM, 2.0)


class Eligibility(unittest.TestCase):
    def test_all_three_predicates_from_data(self):
        e = GC.eligibility(ctype(), pins=PINS)
        self.assertTrue(e["eligible"] and e["collector"] and e["macro_free"] and e["pin_hull_bound"])
        self.assertEqual(e["pin_hull_frac"], 1.0)

    def test_each_predicate_can_fail(self):
        self.assertFalse(GC.eligibility(ctype(contents=[{"inst": "u"}]), pins=PINS)["collector"])
        self.assertFalse(GC.eligibility(ctype(ft_slots=[]), pins=PINS)["collector"])
        t = ctype()
        t["clock"]["landing_contract"].pop("collector_tree")
        self.assertFalse(GC.eligibility(t, pins=PINS)["collector"])
        for k, v in (("hard_cores", [{"name": "m"}]), ("hard", {"x": 1}), ("macro_under_ft", {"rule": "r"})):
            self.assertFalse(GC.eligibility(ctype(**{k: v}), pins=PINS)["macro_free"], k)
        self.assertFalse(GC.eligibility(ctype(), pins=PINS, macros=2)["macro_free"])      # measured macro in the dump
        self.assertFalse(GC.eligibility(ctype(), pins=[(0, 40 + i % 20) for i in range(150)])["pin_hull_bound"])   # short span
        self.assertFalse(GC.eligibility(ctype(), pins=[(0, 0), (0, 100), (100, 50)])["pin_hull_bound"])         # too few pins
        stray = [(0, 40 + i % 20) for i in range(150)] + [(100, 0), (0, 100)]
        e = GC.eligibility(ctype(), pins=stray)
        self.assertTrue(e["pin_hull_bound"])         # fixed far-end pins DO bound the outline ...
        self.assertLess(e["pin_hull_frac_robust"], 0.2)    # ... and the trimmed extent is reported beside it
        self.assertFalse(GC.eligibility(ctype(), pins=stray[:3])["pin_hull_bound"])     # but a handful of pins never qualifies
        self.assertFalse(GC.eligibility(ctype(_die="s81"), pins=PINS)["collector"])          # S81 slice stations are out of scope
        self.assertFalse(GC.eligibility(ctype(_die=None), pins=PINS)["collector"])
        t = ctype()
        t["clock"]["landing_contract"]["collector_tree"] = {}
        self.assertFalse(GC.eligibility(t, pins=PINS)["collector"])
        e = GC.eligibility(ctype(), outline=[120, 120], pins=PINS)
        self.assertFalse(e["eligible"] or e["frame_ok"])                                      # plan 100x100 vs measured 120x120
        e = GC.eligibility(ctype(), pins=None)
        self.assertFalse(e["eligible"] or e["pin_hull_bound"])
        self.assertIn("pin hull not measurable", e["reasons"])

    def test_names_are_never_read(self):
        t = ctype(module="qfd_qc_coll_ftc_part", note="coll_ftc collector", _type="coll_ftc")
        self.assertEqual(GC.eligibility(t, pins=PINS)["eligible"], GC.eligibility(dict(t, module="x", note="", _type="zz"), pins=PINS)["eligible"])


class Metric(unittest.TestCase):
    def cells(self):
        c = [(x + .0, y + .0, x + 1.0, y + 1.0) for x in range(40, 60) for y in range(40, 41)]     # 20 in the band
        c += [(1.0 + i % 10, 1.0 + i // 10, 2.0 + i % 10, 2.0 + i // 10) for i in range(100)]        # 100 in the W strip
        c += [(50.0 + i, 90.0, 51.0 + i, 91.0) for i in range(10)]                                    # 10 outside everything
        return c

    def test_exact_value_share_and_raw_alongside(self):
        r = GC.fill_corridor(ctype(), self.cells(), PINS, raw_fill=0.013)
        # union = band 400 + W strip 30x100 + E strip 30x100 (disjoint)
        self.assertEqual(r["corridor_area"], 6400.0)
        self.assertEqual((r["cell_area_in"], r["cell_area_total"]), (120.0, 130.0))
        self.assertEqual(r["fill_corridor"], round(120 / 6400, 4))
        self.assertEqual(r["share_in"], round(120 / 130, 4))
        self.assertEqual(r["raw_fill"], 0.013)
        self.assertEqual(r["corridor_rects"], {"landing_band": 1, "pin_landing_strip": 2})
        self.assertEqual(r["by_kind"]["landing_band"]["fill"], round(20 / 400, 4))
        self.assertEqual((r["ft_slots_total"], r["ft_slots_undeclared"]), (1, 1))     # no declared station sites: said so
        self.assertEqual(r["provenance"]["_type"], "x")
        self.assertIn("raw fill 0.013 (gate unchanged)", GC.detail(r))
        self.assertIn("REPORT-ONLY", GC.detail(r))

    def test_bounded_by_one_and_straddling_cell_counts_overlap(self):
        r = GC.fill_corridor(ctype(band=(40, 40, 42, 42)), [(35.0, 35.0, 55.0, 55.0)], PINS)    # 20x20 cell over a 2x2 band
        self.assertEqual(r["fill_corridor"], round(4 / (4 + 6000), 4))

    def test_malformed_record_never_raises(self):
        for bad in (None, {}, {"outline_um": None}, ctype(ft_slots=5), dict(ctype(), clock={"landing_contract": []})):
            r = GC.fill_corridor(bad, [(0.0, 0.0, 1.0, 1.0)], PINS, outline=[100, 100])
            self.assertIsNone(r["fill_corridor"])
        t = ctype()
        t["ft_slots"] = [dict(name="s", bit_sites_um=[[["x", "y"]]])]
        r = GC.fill_corridor(t, [(0.0, 0.0, 1.0, 1.0)], PINS, outline=[100, 100])
        self.assertTrue(r["reasons"][0].startswith("error:"))

    def test_load_type_echoes_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.json"
            p.write_text(json.dumps(dict(die=dict(name="qwen_compute"), partition_types=dict(x=ctype()))))
            t = GC.load_type(str(p), "x")
            self.assertEqual((t["_die"], t["_type"]), ("qwen_compute", "x"))
            self.assertEqual(len(t["_plan_sha256"]), 64)

    def test_ineligible_reports_none_with_reason(self):
        r = GC.fill_corridor(ctype(hard_cores=[{"n": 1}]), self.cells(), PINS, raw_fill=0.2)
        self.assertIsNone(r["fill_corridor"])
        self.assertFalse(r["eligible"])
        self.assertIn("fill_corridor n/a", GC.detail(r))
        self.assertNotIn("corridor_area", r)


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        pins = [(i, f"w{i}", "INPUT", 0, 2 * i) for i in range(100)] + [(100 + i, f"e{i}", "OUTPUT", 200, 2 * i) for i in range(100)]
        comb = [(100 + i, 5 + 2 * (i % 10), 5 + 2 * (i // 10)) for i in range(100)]      # 100 cells in the SW corner: raw fill ~0.0025
        self.dump = dump(self.d / "d.tsv", comb=comb, pins=pins)
        self.t = ctype(W=200.0, H=200.0, band=(0, 0, 40, 40))

    def tearDown(self):
        self.tmp.cleanup()

    def test_metric_beside_raw_fill_and_gate_and_verdict_unchanged(self):
        base = G.metrics(str(self.dump))
        withc = G.metrics(str(self.dump), corridor_type=self.t)
        self.assertNotIn("fill_corridor", base)
        fc = withc["fill_corridor"]
        self.assertTrue(fc["eligible"])
        self.assertEqual(fc["raw_fill"], withc["fill_of_free"])
        self.assertGreater(fc["fill_corridor"], withc["fill_of_free"])
        for k in base:                                   # every other metric identical
            self.assertEqual(base[k], withc[k], k)
        R0, v0 = G.judge(base, None, [200, 200])
        R1, v1 = G.judge(withc, None, [200, 200])
        self.assertEqual(v0, v1)
        by = {r["rule"]: r for r in R1}
        self.assertEqual(by["fill"]["status"], "FAIL")   # the raw fill gate is untouched
        self.assertEqual(by["fill_corridor"]["status"], "INFO")
        self.assertIn("raw fill", by["fill_corridor"]["detail"])
        self.assertEqual([r for r in R1 if r["rule"] != "fill_corridor"], R0)
        self.assertNotIn("fill_corridor=", G.verdict_line(v1, R1))

    def test_malformed_type_is_recorded_never_raised(self):
        t = dict(self.t)
        t["ft_slots"] = [dict(name="s", bit_sites_um=[[["x", "y"]]])]
        fc = G.metrics(str(self.dump), corridor_type=t)["fill_corridor"]
        self.assertIsNone(fc["fill_corridor"])
        self.assertTrue(fc["reasons"][0].startswith("error:"))

    def test_cli_flag_and_plan_name_forms_same_result(self):
        tj = self.d / "t.json"
        tj.write_text(json.dumps(self.t))
        pj = self.d / "p.json"
        pj.write_text(json.dumps(dict(die=dict(name="qwen_compute"), partition_types=dict(x=self.t))))
        outs = []
        for extra in ([], ["--corridor-type-json", str(tj)], ["--corridor-plan", str(pj), "--corridor-type", "x"]):
            o = self.d / f"o{len(outs)}.json"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = G.main([str(self.dump), "--json", str(o), "--outline", "200x200"] + extra)
            outs.append((rc, json.loads(o.read_text())))
        self.assertEqual({rc for rc, _ in outs}, {outs[0][0]})
        self.assertEqual({o["verdict"] for _, o in outs}, {outs[0][1]["verdict"]})
        self.assertNotIn("fill_corridor", [r["rule"] for r in outs[0][1]["rules"]])
        a, b = (o["rules"][-1] if o["rules"][-1]["rule"] == "fill_corridor" else
                [r for r in o["rules"] if r["rule"] == "fill_corridor"][0] for _, o in outs[1:])
        self.assertIsNotNone(a["value"])
        self.assertEqual(a["value"], b["value"])
        self.assertEqual(a["status"], "INFO")


if __name__ == "__main__":
    unittest.main()
