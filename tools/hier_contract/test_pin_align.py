"""pin ALIGNMENT of die bundles (owner 2026-10-13): jog along the shared direction, bit order, pin-to-pin length; WARN
above 20 um / reordered / u-turn, FAIL when the jog alone takes more than 0.60 of the channel's tracks; the one-ended
form in slot_fit; the classes of die_pin_audit."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_pin_audit as DPA  # noqa: E402
import pin_align as PA  # noqa: E402
import slot_fit as SF  # noqa: E402


def bus(n, x, y0, face, layer="M4", pitch=0.096, rev=False, horiz=False):
    """n pins on a vertical (E / W) face at x, or with horiz on a horizontal (N / S) face at y = x"""
    idx = range(n - 1, -1, -1) if rev else range(n)
    return [((y0 + i * pitch, x, face, layer) if horiz else (x, y0 + i * pitch, face, layer)) for i in idx]


def lef(name, w, h, pins):
    """pins: [(pin, layer, x0, y0, x1, y1)]"""
    L = [f"MACRO {name}", f"  SIZE {w} BY {h} ;"]
    for p, ly, a, b, c, d in pins:
        L += [f"  PIN {p}", "    PORT", f"      LAYER {ly} ;", f"        RECT {a} {b} {c} {d} ;", "    END", f"  END {p}"]
    L += ["  OBS", "    LAYER M1 ;", f"      RECT 0 0 {w} {h} ;", "  END", f"END {name}", ""]
    return "\n".join(L)


class Bundle(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(PA.WARN_UM, 20.0)
        self.assertEqual(PA.CUT_LIMIT, 0.60)
        self.assertAlmostEqual(PA.CAP_PER_UM, 0.75 / 0.080 + 0.75 / 0.064 + 0.50 / 0.048)       # 31.51 tracks / um
        # the one-length form: 0.60 of a 20-um channel = 378 jog wires = 36 um of a bus at 2 tracks a bit
        self.assertEqual(PA.FAIL_UM, 36)

    def test_facing_and_aligned_is_ok(self):
        r = PA.bundle(bus(512, 100.0, 10.0, "E"), bus(512, 140.0, 10.0, "W"))
        self.assertEqual((r["kind"], r["verdict"], r["order"], r["axis"]), ("straight", "OK", "preserved", "x"))
        self.assertEqual((r["jog_max"], r["gap"], r["len_max"], r["jog_cross"]), (0.0, 40.0, 40.0, 0))

    def test_jog_over_20_um_warns(self):
        r = PA.bundle(bus(64, 100.0, 10.0, "E"), bus(64, 400.0, 40.0, "W"))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["jog_max"], 30.0)
        self.assertEqual(r["jog_cross"], 64)                 # every bit's jog wire crosses the same line
        self.assertLess(r["jog_cut"], 0.60)                  # 64 wires in a 300-um channel: 0.7 % of its tracks
        self.assertIn("jog 30.0 um > 20", r["why"][0])
        self.assertEqual(PA.bundle(bus(64, 100.0, 10.0, "E"), bus(64, 400.0, 29.0, "W"))["verdict"], "OK")   # 19 um

    def test_fail_when_the_jog_alone_fills_the_channel(self):
        # 512 b shifted 60 um across a 20-um channel: 512 perpendicular wires of the channel's 630 tracks = 0.81
        r = PA.bundle(bus(512, 100.0, 10.0, "E"), bus(512, 120.0, 70.0, "W"))
        self.assertEqual(r["verdict"], "FAIL")
        self.assertAlmostEqual(r["jog_cut"], 512 / (PA.CAP_PER_UM * 20.0), places=3)
        self.assertIn("jog cut 0.81 > 0.6", r["why"][0])
        self.assertIn("jog 60.0 um > 20", r["why"][1])
        # the same shift across a 60-um channel is 0.27 of its tracks: a warning, not a failure
        r = PA.bundle(bus(512, 100.0, 10.0, "E"), bus(512, 160.0, 70.0, "W"))
        self.assertEqual((r["verdict"], r["jog_cut"] < 0.60), ("WARN", True))

    def test_fail_threshold_is_the_cut_rule(self):
        n_at_limit = int(0.60 * PA.CAP_PER_UM * 20.0)        # 378 wires
        ok = PA.bundle(bus(n_at_limit, 100.0, 0.0, "E"), bus(n_at_limit, 120.0, 50.0, "W"))
        over = PA.bundle(bus(n_at_limit + 2, 100.0, 0.0, "E"), bus(n_at_limit + 2, 120.0, 50.0, "W"))
        self.assertEqual((ok["verdict"], over["verdict"]), ("WARN", "FAIL"))

    def test_abutted_faces_need_exact_alignment(self):
        ok = PA.bundle(bus(8, 100.0, 10.0, "E"), bus(8, 100.024, 10.0, "W"))
        bad = PA.bundle(bus(8, 100.0, 10.0, "E"), bus(8, 100.024, 10.096, "W"))
        self.assertEqual((ok["verdict"], bad["verdict"]), ("OK", "FAIL"))
        self.assertIn("abutted faces", bad["why"][0])

    def test_reversed_and_interleaved_order(self):
        r = PA.bundle(bus(32, 100.0, 10.0, "E"), bus(32, 200.0, 10.0, "W", rev=True))
        self.assertEqual((r["order"], r["verdict"], r["cross_share"]), ("reversed", "WARN", 1.0))
        self.assertIn("bit order reversed", " ".join(r["why"]))
        a = bus(32, 100.0, 10.0, "E")
        b = bus(32, 200.0, 10.0, "W")
        b[3], b[4] = b[4], b[3]
        r = PA.bundle(a, b)
        self.assertEqual(r["order"], "interleaved")
        self.assertAlmostEqual(r["cross_share"], 1 / (32 * 31 / 2), places=4)

    def test_vertical_travel(self):
        r = PA.bundle(bus(16, 500.0, 10.0, "N", "M5", horiz=True), bus(16, 560.0, 10.0, "S", "M5", horiz=True))
        self.assertEqual((r["kind"], r["axis"], r["verdict"], r["gap"]), ("straight", "y", "OK", 60.0))

    def test_uturn(self):
        r = PA.bundle(bus(16, 100.0, 10.0, "E"), bus(16, 300.0, 10.0, "E"))          # both faces look east
        self.assertEqual((r["kind"], r["verdict"]), ("uturn", "WARN"))
        r = PA.bundle(bus(16, 100.0, 10.0, "E"), bus(16, 40.0, 10.0, "W"))           # the load lies behind the face
        self.assertEqual(r["kind"], "uturn")

    def test_corner_order_is_reported_not_judged(self):
        # driver E face at x 100 (y 10..), load S face at y 200 (x 150..): an L; one H and one V segment per bit on
        # different layers, so the track demand is the same in either order
        a = bus(16, 100.0, 10.0, "E")
        nested = [(150.0 + (15 - i) * 0.096, 200.0, "S", "M5") for i in range(16)]   # lowest bit turns farthest out
        crossing = [(150.0 + i * 0.096, 200.0, "S", "M5") for i in range(16)]
        r = PA.bundle(a, nested)
        self.assertEqual((r["kind"], r["verdict"], r["order"]), ("corner", "OK", "nested"))
        r = PA.bundle(a, crossing)
        self.assertEqual((r["kind"], r["verdict"], r["order"]), ("corner", "OK", "crossing"))

    def test_narrow_gap_short_jog_is_a_warning(self):
        # 99 wires shifted 9.4 um beside a 2.4-um gap: over the channel's 75 tracks, but a jog under 20 um
        r = PA.bundle(bus(99, 100.0, 10.0, "E"), bus(99, 102.4, 19.4, "W"))
        self.assertEqual(r["verdict"], "WARN")
        self.assertGreater(r["jog_cut"], 0.60)
        self.assertIn("spills onto the die's over-tile tracks", r["why"][0])

    def test_judge_from_stored_row(self):
        r = PA.bundle(bus(512, 100.0, 10.0, "E"), bus(512, 120.0, 70.0, "W"))
        self.assertEqual(PA.judge(r)[0], "FAIL")
        self.assertEqual(PA.judge(r, cut_limit=0.9)[0], "WARN")
        self.assertAlmostEqual(r["window_share"], 512 / (PA.OVER_TILE_PER_UM * 260.0), places=3)

    def test_area_pin_is_length_only(self):
        r = PA.bundle([(10.0, 10.0, None, "M8")], [(300.0, 90.0, "W", "M4")])
        self.assertEqual((r["kind"], r["verdict"], r["len_max"]), ("area", "OK", 370.0))

    def test_range_jog(self):
        self.assertEqual(PA.range_jog(10.0, 30.0, 0.0, 40.0), 0.0)
        self.assertEqual(PA.range_jog(10.0, 70.0, 0.0, 40.0), 30.0)
        self.assertEqual(PA.range_jog(-25.0, 30.0, 0.0, 40.0), 25.0)


class _It:
    def __init__(self, name, master, x, y, orient="R0"):
        self.name, self.master, self.x, self.y, self.orient = name, master, x, y, orient


class Analyze(unittest.TestCase):
    def setUp(self):
        pins_e = [(f"o[{i}]", "M4", 49.9, 5 + i * 0.096, 50.0, 5.024 + i * 0.096) for i in range(8)]
        pins_w = [(f"i[{i}]", "M4", 0.0, 5 + i * 0.096, 0.1, 5.024 + i * 0.096) for i in range(8)]
        self.lefs = [lef("A", 50.0, 20.0, pins_e + [("ck", "M5", 25.0, 19.9, 25.024, 20.0)]), lef("B", 50.0, 20.0, pins_w)]

    def test_aligned_pair(self):
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 80, 0)], [("n", "data", 8, [("a", "o"), ("b", "i")])], self.lefs)
        self.assertEqual((rec["verdict"], rec["bundles"], rec["bits"], rec["bits_without_pin"]), ("PASS", 1, 8, 0))
        self.assertEqual(rec["by_kind"], {"straight": 1})
        self.assertEqual(rec["jog_hist_um"]["<= 1 track"], {"bundles": 1, "bits": 8})
        self.assertEqual(rec["classes"][0]["len_max"], 30.1)                # pin centre to pin centre
        self.assertIn("OT_PIN_ALIGN PASS bundles 1 bits 8", PA.line(rec))

    def test_shifted_slot_and_mirror(self):
        ins = [_It("a", "A", 0, 0), _It("b", "B", 80, 30)]
        rec = PA.analyze(ins, [("n", "data", 8, [("a", "o"), ("b", "i")])], self.lefs)
        self.assertEqual((rec["by_verdict"], rec["jog_over_warn"]), ({"WARN": 1}, {"bundles": 1, "bits": 8}))
        self.assertEqual(rec["flagged"][0]["jog_max"], 30.0)
        # B mirrored about x (MX): its pins run top-down, the bus arrives reversed
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 80, 0, "MX")], [("n", "data", 8, [("a", "o"), ("b", "i")])], self.lefs)
        self.assertEqual(rec["by_order"], {"reversed": 1})
        self.assertEqual(rec["order_not_preserved"], {"bundles": 1, "bits": 8})
        # B mirrored about y (MY): its W-face pins now look east, away from A
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 80, 0, "MY")], [("n", "data", 8, [("a", "o"), ("b", "i")])], self.lefs)
        self.assertEqual(rec["by_kind"], {"uturn": 1})

    def test_slices_names_exempt_and_missing(self):
        ins = [_It("a", "A", 0, 0), _It("b", "B", 80, 0), _It("c", "B", 80, 40)]
        buses = [("lo", "data", 4, [("a", "o[0:3]"), ("b", "i[0:3]")]),
                 ("x", "data", 4, [("a", "o[4:7]"), ("c", "nope[0:3]")]),
                 ("ck", "clock_trunk", 1, [("a", "ck"), ("b", "i[0:0]")]),
                 ("fan", "data", 2, [("a", "o[0:1]"), ("b", "i[6:7]"), ("c", "i[0:1]")])]
        rec = PA.analyze(ins, buses, self.lefs)
        self.assertEqual((rec["bundles"], rec["bits"], rec["bits_without_pin"]), (3, 8, 4))
        self.assertEqual(rec["ports_without_pin"], {"B.nope": 4})
        names = lambda it, port, bits: [f"i[{7 - i}]" for i in range(bits)] if it.master == "B" else PA.default_names(it, port, bits)  # noqa: E731
        rec = PA.analyze(ins[:2], [("n", "data", 8, [("a", "o"), ("b", "i")])], self.lefs, names)
        self.assertEqual(rec["by_order"], {"reversed": 1})

    def test_inset_face_pins_are_face_pins(self):
        a = lef("A", 50.0, 20.0, [(f"o[{i}]", "M4", 49.4, 5 + i * 0.096, 49.6, 5.024 + i * 0.096) for i in range(8)])   # 0.4 um inset
        b = lef("B", 50.0, 20.0, [(f"i[{i}]", "M4", 0.4, 5 + i * 0.096, 0.6, 5.024 + i * 0.096) for i in range(8)])
        c = lef("C", 50.0, 20.0, [(f"i[{i}]", "M8", 20.0, 5 + i * 0.096, 20.2, 5.024 + i * 0.096) for i in range(8)])   # interior
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 80, 0), _It("c", "C", 80, 40)],
                         [("n", "data", 8, [("a", "o"), ("b", "i"), ("c", "i")])], [a, b, c])
        self.assertEqual(rec["by_kind"], {"straight": 1, "area": 1})

    def test_later_lef_overrides(self):
        moved = lef("B", 50.0, 20.0, [(f"i[{i}]", "M4", 0.0, 10 + i * 0.096, 0.1, 10.024 + i * 0.096) for i in range(8)])
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 80, 0)], [("n", "data", 8, [("a", "o"), ("b", "i")])],
                         self.lefs + [moved])
        self.assertEqual(rec["classes"][0]["jog_max"], 5.0)

    def test_fail_bundle_fails_the_die(self):
        n = 512
        a = lef("A", 50.0, 200.0, [(f"o[{i}]", "M4", 49.9, 5 + i * 0.096, 50.0, 5.024 + i * 0.096) for i in range(n)])
        b = lef("B", 50.0, 200.0, [(f"i[{i}]", "M4", 0.0, 90 + i * 0.096, 0.1, 90.024 + i * 0.096) for i in range(n)])
        rec = PA.analyze([_It("a", "A", 0, 0), _It("b", "B", 70, 0)], [("n", "data", n, [("a", "o"), ("b", "i")])], [a, b])
        self.assertEqual((rec["verdict"], rec["by_verdict"]), ("FAIL", {"FAIL": 1}))
        self.assertEqual(rec["classes"][0]["worst"], "FAIL")
        self.assertIn("OT_PIN_ALIGN FAIL", PA.line(rec))

    def test_gate_mode(self):
        import os
        old = os.environ.pop("OT_PIN_ALIGN_GATE", None)
        try:
            self.assertEqual(PA.gate_mode(), "fail")
            os.environ["OT_PIN_ALIGN_GATE"] = "warn"
            self.assertEqual(PA.gate_mode(), "warn")
            os.environ["OT_PIN_ALIGN_GATE"] = "bogus"
            self.assertEqual(PA.gate_mode(), "fail")
        finally:
            os.environ.pop("OT_PIN_ALIGN_GATE", None)
            if old is not None:
                os.environ["OT_PIN_ALIGN_GATE"] = old


class SlotFit(unittest.TestCase):
    K = {"outline": [100.0, 400.0], "pins": {"W": ["d"], "N": ["ck"]}, "clock_port": "ck", "reset_ports": [],
         "pin_layers": {"E": ["M4"], "W": ["M4"], "N": ["M5"], "S": ["M5"]}, "cap": "M5", "est_insertion_ps": None,
         "est_basis": None}
    S = {"outline": {"w": 100.0, "h": 400.0}, "layer_cap": "M5",
         "pins": [{"name": "d[511:0]", "face": "W", "layer": "M4", "span_um": [100.0, 150.0]}]}

    def run_(self, rng, slot=None):
        return SF.compare(dict(self.K, pin_ranges=rng), slot or self.S)

    def test_range_inside_or_close(self):
        self.assertEqual(self.run_({"d": [100.0, 150.0]}), ([], []))
        self.assertEqual(self.run_({"d": [90.0, 165.0]}), ([], []))                 # 15 um out: below the warning
        self.assertEqual(self.run_({}), ([], []))                                   # no planned range: not judged

    def test_warn_and_mismatch(self):
        bad, notes = self.run_({"d": [100.0, 175.0]})                               # 25 um
        self.assertEqual(bad, [])
        self.assertIn("pin_align WARN: d planned at 100..175 um lies up to 25.0 um outside", notes[0])
        bad, notes = self.run_({"d": [40.0, 90.0]})                                 # 60 um
        self.assertEqual(len(bad), 1)
        self.assertIn("pin_align: d planned at 40..90 um lies up to 60.0 um outside its slot span 100..150 um on W", bad[0])

    def test_offset_width_span_and_pending_view(self):
        s = dict(self.S, pins=[{"name": "d[511:0]", "face": "W", "layer": "M4", "offset": 125.0, "width": 50.0}])
        self.assertEqual(SF.slot_span(s["pins"][0]), (100.0, 150.0))
        self.assertEqual(len(self.run_({"d": [200.0, 250.0]}, s)[0]), 1)
        s = dict(self.S, pins=[dict(self.S["pins"][0], offset_pending_view=True)])
        self.assertEqual(self.run_({"d": [200.0, 250.0]}, s), ([], []))             # the contract adopts the view's offsets


class AuditClass(unittest.TestCase):
    def rec(self, **kw):
        r = dict(hard_ip=False, top_layer="M5", outline=[10.0, 10.0], slot_outline=[10.0, 10.0], macro="m",
                 face=dict(face_pins=100, blocked_above=0, blocked_same=0), pockets={}, mismatch={}, cluster_child=False)
        r.update(kw)
        return r

    def test_classes(self):
        self.assertEqual(DPA.classify(self.rec())[0], "ACCEPT")
        self.assertEqual(DPA.classify(self.rec(hard_ip=True, face=dict(face_pins=9, blocked_above=9, blocked_same=0)))[0], "ACCEPT")
        self.assertEqual(DPA.classify(self.rec(face=dict(face_pins=100, blocked_above=0, blocked_same=4)))[0], "FIX BY VIEW")
        self.assertEqual(DPA.classify(self.rec(pockets=dict(layer="M7", count=5, marker=False)))[0], "FIX BY VIEW")
        self.assertEqual(DPA.classify(self.rec(pockets=dict(layer="M7", count=5, marker=True)))[0], "ACCEPT")
        self.assertEqual(DPA.classify(self.rec(pockets=dict(layer="M5", count=5, marker=False)))[0], "ACCEPT")
        c, why = DPA.classify(self.rec(face=dict(face_pins=100, blocked_above=30, blocked_same=4)))
        self.assertEqual(c, "FIX BY PIN RE-PLAN")                                   # the costliest action names the class
        self.assertEqual(len(why), 2)
        self.assertEqual(DPA.classify(self.rec(mismatch={"names": ["2 slot pins not in the pin plan (e.g. x)"]}))[0], "FIX AT DIE")
        self.assertEqual(DPA.classify(self.rec(mismatch={"outline": ["outline 1 x 1 != slot 2 x 2"]}))[0], "FIX AT DIE")
        self.assertEqual(DPA.classify(self.rec(mismatch={"layer": ["routing cap M7 above the slot layer cap M5"]}))[0], "ACCEPT")
        c, why = DPA.classify(self.rec(mismatch={"cell": ["slot cell a != view macro m"], "outline": ["outline 1 x 1 != slot 2 x 2"]}))
        self.assertEqual(c, "FIX BY PIN RE-PLAN")
        self.assertIn("NOT THE SLOT'S MASTER", why[0])

    def test_categorise(self):
        cat = DPA.categorise(["outline 1 x 2 != slot 3 x 4", "routing cap M7 above the slot layer cap M5",
                              "3 pins off their slot face: a E (slot W)", "N-face pins may land on M7 (slot M5)",
                              "2 slot pins not in the pin plan (e.g. a)", "estimated clock insertion 400 ps (x) vs slot target 250 ps (+-100)"])
        self.assertEqual(list(cat), ["outline", "layer", "face", "pin_layer", "names", "insertion"])


if __name__ == "__main__":
    unittest.main()
