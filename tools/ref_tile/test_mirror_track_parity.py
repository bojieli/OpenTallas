"""QW-CB16FULL/MIRROR 10-19: why an x-mirrored (MY / R180) closed child cannot be placed on the asap7 track grid.

asap7 vertical tracks: M3 x = 9 + 36k nm, M5 x = 12 + 48k nm.  A view built on track has M3 pin centres == 9 (mod 36)
and M5 centres == 12 (mod 48).  MY maps a centre c to ox + W - c, so both layers on track need
ox + W == 18 (mod 36) and ox + W == 24 (mod 48); mod gcd(36, 48) = 12 that is 6 == 0: no origin, for any width.
The best x shift (18 nm) repairs M3 and leaves every M5 pin off -- the 150-pin macro_grid FAIL of qfd_c_land_w257_narrow
MY in the CB16 reg kits.  MX only needs a 24 nm y shift (one horizontal pin layer, M4).  Pure python on the LEFs.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hier_contract"))
import check_macro_track_alignment as cmta  # noqa: E402
import macro_grid_lint as mgl  # noqa: E402

# reg1 geometry: a w257 half at (302.4, 43.2) um on the 21.6 um child lattice
ORIGIN_NM = (302400, 43200)
VIEWS = {   # view dir -> orientations expected on grid (after the place_blocks / on_track snap)
    "physical/ref_tile/qfd_c_land_w257_narrow/views/qfd_c_land_w257_narrow": {"R0", "MX"},
    "physical/ref_tile/qfd_c_land_r257_narrow/views/qfd_c_land_r257_narrow": {"R0", "MX"},
    "physical/ref_tile/qfd_c_land_w258_narrow/views/qfd_c_land_w258_narrow": {"R0", "MX"},
    "physical/ref_tile/qfd_c_land_r258_narrow/views/qfd_c_land_r258_narrow": {"R0", "MX"},
    "physical/ref_tile/qfd_c_stn514/views/qfd_c_stn514": {"R0", "MX"},
    "physical/ref_tile/qfd_c_stn516/views/qfd_c_stn516": {"R0", "MX"},
    "physical/ref_tile/qfd_c_xstn_safe/views/qfd_c_xstn_safe": {"R0", "MX"},
    "physical/ref_tile/qfd_c_xstnw_safe/views/qfd_c_xstnw_safe": {"R0", "MX"},
    # A0 stand-in: W/E-face M4 pins only -> every mirror is solvable (MX / R180 with the 24 nm y shift)
    "physical/ref_tile/qfd_c_b16_dv_diag/a0_standin/qfd_tile_nk_rp2_romleaf_rr": {"R0", "MX", "MY", "R180"},
}


def offtrack(m, o, ox, oy):
    return sum(v["offtrack"] for v in cmta.check_placement(m, o, ox, oy)["layers"].values())


def best(m, o, ox, oy):
    """off-track count at the best origin shift (the place_blocks -> on_track rule)"""
    _, dx, dy = mgl.best_shift(m, o, ox, oy)
    return offtrack(m, o, ox + dx, oy + dy)


class MirrorParity(unittest.TestCase):
    def test_no_mirror_origin_for_m3_and_m5(self):
        # exhaustive over one lcm period of origin and width
        for W in range(144):
            for ox in range(144):
                self.assertFalse((ox + W - 9) % 36 == 9 and (ox + W - 12) % 48 == 12, (W, ox))

    def test_synthetic_macro(self):
        W = 64800
        m = {"name": "syn", "W": W, "H": 43200, "pins": [
            {"name": "a", "use": "SIGNAL", "rects": [("M3", (9 - 9, 43000, 9 + 9, 43200))]},
            {"name": "b", "use": "SIGNAL", "rects": [("M5", (1212 - 12, 43000, 1212 + 12, 43200))]}]}
        self.assertEqual(best(m, "R0", 0, 0), 0)
        self.assertEqual(best(m, "MY", 0, 0), 1)     # one of the two layers always stays off

    def test_closed_cb16_children(self):
        rows = []
        for v, ok in VIEWS.items():
            lef = ROOT / v / f"{Path(v).name}.lef"
            if not lef.exists():
                self.skipTest(f"{lef} not checked out")
            m = next(x for x in cmta.parse_lef(lef.read_text(errors="replace")) if x["name"] == Path(v).name)
            for o in cmta.MIRROR_SET:
                n = best(m, o, *ORIGIN_NM)
                rows.append((Path(v).name, o, n))
                self.assertEqual(n == 0, o in ok, f"{Path(v).name} {o}: {n} pins off track at the best shift")
        w257_my = next(n for name, o, n in rows if name == "qfd_c_land_w257_narrow" and o == "MY")
        self.assertEqual(w257_my, 150)   # the reg-kit macro_grid FAIL: every M5 pin

    def test_fix_hint_names_the_parity(self):
        import ref_tile as RT
        v = "physical/ref_tile/qfd_c_land_w257_narrow/views/qfd_c_land_w257_narrow"
        if not (ROOT / v).exists():
            self.skipTest("view not checked out")
        self.assertIn("x-mirror is impossible", RT.mirror_fix_hint({"view": v, "orient": "MY"}))
        self.assertIn("re-export", RT.mirror_fix_hint({"view": v, "orient": "R0"}))


if __name__ == "__main__":
    unittest.main()
