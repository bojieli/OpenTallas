"""PINBAND-1 11-06: gen-time hard-child pin-vs-PG-band check + smallest grid-keeping row-multiple move."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinband_site as PB  # noqa: E402

PDN = ("define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}\n"
       "add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {4.32} -offset {2.064}\n"
       + PB.PARTITION_M6 +
       "define_pdn_grid -macro -name {core_pg_M5} -instances {{^u_a$}} -voltage_domains {CORE} -halo {0}\n"
       "add_pdn_stripe -grid {core_pg_M5} -layer {M6} -width {0.5} -pitch {9.0} -offset {0.1}\n")
CORE = (4.32, 4.32, 400.0, 400.0)


def lef(name, h, rows, m4=False):
    pins = "".join(f"  PIN p{i}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M5 ;\n        RECT 1.0 {a} 1.024 {b} ;\n"
                   f"    END\n  END p{i}\n" for i, (a, b) in enumerate(rows))
    if m4:
        pins += "  PIN q\n    DIRECTION INPUT ;\n    PORT\n      LAYER M4 ;\n        RECT 0 1.0 0.1 1.024 ;\n    END\n  END q\n"
    pins += ("  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M5 ;\n        RECT 3 0 3.1 1 ;\n    END\n  END VDD\n")
    return f"MACRO {name}\n  SIZE 20 BY {h} ;\n{pins}END {name}\n"


def band_hit(y0, y1):
    return PB.row_bad(y0, y1, [(CORE[1] + o, p, b) for o, p, b in PB.stripes(PDN)])


class TestPinbandSite(unittest.TestCase):
    def test_stripes_top_grid_only(self):
        self.assertEqual(PB.stripes(PDN), [(1.968, 4.32, 0.672)])

    def test_step_keeps_tracks(self):
        self.assertAlmostEqual(PB.step_um([]), 0.192)
        self.assertAlmostEqual(PB.step_um(["M4"]), 0.192)
        self.assertAlmostEqual(PB.step_um(["M4", "M6"]), 0.192)
        self.assertAlmostEqual(PB.step_um(["M8"]), 0.96)

    def test_nk_edge_row_r180_moves(self):
        # NK form: 0.084-tall top-edge pin row; R180 puts it at the bottom edge, under band 4.32+1.968+k*4.32
        L = lef("raw", 30.0, [(29.916, 30.0)], m4=True)
        y = CORE[1] + 1.968 + 10 * 4.32 + 0.1          # bottom edge inside the band
        self.assertTrue(band_hit(y, y + 0.084))
        kids = [dict(inst="u_r", master="raw", orient="R180", x=50.0, y=y)]
        rep = PB.site(kids, PDN, CORE, lambda m: L, move=True)
        self.assertEqual(len(rep["moved"]), 1)
        dy = rep["moved"][0]["dy"]
        self.assertAlmostEqual(dy / 0.192, round(dy / 0.192))
        self.assertFalse(band_hit(kids[0]["y"], kids[0]["y"] + 0.084))

    def test_interior_row_smallest_row_multiple(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 0.2       # interior row inside the band
        kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
        rep = PB.site(kids, PDN, CORE, lambda m: L, move=True)
        dy = rep["moved"][0]["dy"]
        self.assertAlmostEqual(dy / 0.192, round(dy / 0.192))
        self.assertLessEqual(abs(dy), 0.768 + 1e-9)
        self.assertFalse(band_hit(kids[0]["y"] + 10.0, kids[0]["y"] + 10.3))

    def test_clear_child_unchanged(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 2.0
        kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
        rep = PB.site(kids, PDN, CORE, lambda m: L, move=True)
        self.assertEqual((rep["moved"], rep["refused"], kids[0]["y"]), ([], [], y))

    def test_neighbour_gap_kept(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 0.2
        above = (50.0, y + 30.0 + 0.3, 70.0, y + 60.0)        # 0.3-um gap above: an up move may not shrink it
        kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
        rep = PB.site(kids, PDN, CORE, lambda m: L, others=[above], move=True)
        self.assertLess(rep["moved"][0]["dy"], 0)

    def test_refused_when_no_legal_move(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 0.2
        tight = (CORE[0], CORE[1], CORE[2], y + 30.0)            # core top = macro top: no up move
        below = (50.0, CORE[1], 70.0, y - 0.1)                      # 0.1-um gap below: no down move
        kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
        rep = PB.site(kids, PDN, tight, lambda m: L, others=[below], move=True)
        self.assertEqual((rep["moved"], len(rep["refused"]), kids[0]["y"]), ([], 1, y))

    def test_unclearable_rows_partial_min_bad(self):
        # two M6 band sets per pitch + an M8 signal pin (step lcm(0.192, 0.08) = 0.96): no move within 4.32 clears the
        # three rows together; take the legal move that leaves 1 row and report it as partial
        pdn = PDN + "add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {0.0}\n"
        bands = [(CORE[1] + o, p, b) for o, p, b in PB.stripes(pdn)]
        h = 24.64 + 0.084
        L = lef("hc", h, [(0.0, 0.084), (0.12, 0.204), (24.64, h)]).replace(
            "  PIN VDD", "  PIN m8\n    DIRECTION INPUT ;\n    PORT\n      LAYER M8 ;\n        RECT 0 5 1 5.08 ;\n"
                         "    END\n  END m8\n  PIN VDD")
        rows = PB.pin_rows(PB.macro_body(L))[2]
        nbad = lambda yy: sum(PB.row_bad(a, b, bands) for a, b, e in PB.abs_rows(rows, h, "R0", yy))
        y = CORE[1] + 20 * 4.32 + 0.24
        self.assertEqual(nbad(y), 2)
        kids = [dict(inst="u_h", master="hc", orient="R0", x=50.0, y=y)]
        rep = PB.site(kids, pdn, CORE, lambda m: L, move=True)
        self.assertEqual((len(rep["moved"]), rep["moved"][0]["rows_left"], rep["partial"]), (1, 1, ["u_h"]))
        dy = rep["moved"][0]["dy"]
        self.assertAlmostEqual(rep["moved"][0]["step"], 0.96)
        self.assertAlmostEqual(dy / 0.192, round(dy / 0.192))
        self.assertEqual(nbad(kids[0]["y"]), 1)

    def test_every_move_on_0192_grid(self):
        # QC-A0C-B6 20:58: every move (full or partial) is a multiple of 0.192 um
        L = lef("leaf", 30.0, [(10.0, 10.3), (21.7, 21.9)], m4=True)
        for i in range(40):
            y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + i * 0.108
            kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
            for r in PB.site(kids, PDN, CORE, lambda m: L, move=True)["moved"]:
                self.assertAlmostEqual(r["dy"] / 0.192, round(r["dy"] / 0.192), places=6)

    def test_env_off_is_check_only(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 0.2
        kids = [dict(inst="u_l", master="leaf", orient="R0", x=50.0, y=y)]
        old = os.environ.get("OT_PINBAND_SITE")
        os.environ["OT_PINBAND_SITE"] = "0"
        try:
            rep = PB.site(kids, PDN, CORE, lambda m: L)
        finally:
            os.environ.pop("OT_PINBAND_SITE") if old is None else os.environ.__setitem__("OT_PINBAND_SITE", old)
        self.assertEqual((rep["moved"], kids[0]["y"]), ([], y))
        self.assertIn("check only", rep["refused"][0]["why"])

    def test_rotated_reported_not_checked(self):
        L = lef("leaf", 30.0, [(10.0, 10.3)])
        kids = [dict(inst="u_r", master="leaf", orient="R90", x=50.0, y=20.0)]
        rep = PB.site(kids, PDN, CORE, lambda m: L, move=True)
        self.assertEqual((rep["not_checked_rotated"], kids[0]["y"]), (["u_r"], 20.0))

    def test_site_rows_in_place_shared_list(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "macros").mkdir()
            (Path(d) / "macros" / "leaf.lef").write_text(lef("leaf", 30.0, [(10.0, 10.3)]))
            y = CORE[1] + 1.968 + 5 * 4.32 - 10.0 + 0.2
            at = [50.0, y]
            spec_macro = dict(at=at)                 # S81 legacy: spec macros[].at is the same list object
            rows = [dict(inst="u_l", master="leaf", at=at, orient="R0")]
            rep = PB.site_rows(d, rows, PDN, CORE)
            self.assertEqual(len(rep["moved"]), 1)
            self.assertIs(rows[0]["at"], at)
            self.assertEqual(spec_macro["at"][1], rep["moved"][0]["y_new"])
            self.assertTrue((Path(d) / "pinband_sites.json").is_file())


if __name__ == "__main__":
    unittest.main()
