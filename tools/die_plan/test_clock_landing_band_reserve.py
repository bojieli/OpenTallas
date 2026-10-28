"""LAND-KV-1 10-27: opt-in live-ring band reserve (clock_landing_plan BAND_RESERVE)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402


def _type():
    return dict(outline_um=[400.0, 300.0], hard_cores=[],
                buses=[dict(name="ft1_i", face="S", window_um=[200.0, 200.432], width=1),
                       dict(name="wide_i", face="S", window_um=[100.0, 160.0], width=64)])


class BandReserve(unittest.TestCase):
    def tearDown(self):
        CP.BAND_RESERVE = "padded"
        CP.BAND_SPREAD = 1.0

    def test_default_is_padded(self):
        self.assertEqual(CP.BAND_RESERVE, "padded")
        b = CP._storage_band(_type(), "ft1_i", 1, [])
        self.assertAlmostEqual(b["area_reserve_um2"], (5 * 64 * .2916 + 4 * 64 * .0729 + 160 * .2916) / .40, places=3)

    def test_live_one_bit_ring_is_measured_count(self):
        CP.BAND_RESERVE = "live"
        b = CP._storage_band(_type(), "ft1_i", 1, [])
        self.assertAlmostEqual(b["area_reserve_um2"], ((4 * (2 + 3) + 124) * .2916 + 612 * .0729) / .40, places=3)
        self.assertLess(b["area_reserve_um2"], 0.6 * (5 * 64 * .2916 + 4 * 64 * .0729 + 160 * .2916) / .40)

    def test_live_full_chunk_matches_padded(self):
        CP.BAND_RESERVE = "live"
        live = CP._storage_band(_type(), "wide_i", 63, [])["area_reserve_um2"]
        CP.BAND_RESERVE = "padded"
        padded = CP._storage_band(_type(), "wide_i", 63, [])["area_reserve_um2"]
        self.assertLess(abs(live - padded) / padded, 0.02)

    def test_ring_ff_is_flop_count_times_footprint(self):
        # DIE-HEAD-11: hd_tile u_cland_i W=567 -> rw 576, (5*576+160) flops x 1.4166 um2 >= measured 4177.4 um2
        CP.BAND_RESERVE = "ring_ff"
        b = CP._storage_band(_type(), "wide_i", 63, [])
        self.assertAlmostEqual(b["area_reserve_um2"], (5 * 64 + 160) * 4177.4 / 2949 * 1.05, places=3)
        self.assertGreaterEqual((5 * 576 + 160) * CP.RING_FF_RESERVE_UM2, 4177.4)
        rect = b["rect_um"]
        self.assertGreaterEqual((rect[2] - rect[0]) * (rect[3] - rect[1]) + 1e-6, b["area_reserve_um2"])

    def test_compose_accepts_ring_ff(self):
        self.assertIn("ring_ff", CP.BAND_MODES)

    def test_ring_ff_avoids_die_islands(self):
        CP.BAND_RESERVE = "ring_ff"
        ty = _type()
        free = CP._storage_band(ty, "wide_i", 63, [])["rect_um"]
        ty["clock"] = dict(die_islands_um=[[free[0], free[1], free[0] + 8.64, free[1] + 8.64]])
        r = CP._storage_band(ty, "wide_i", 63, [])["rect_um"]
        isl = ty["clock"]["die_islands_um"][0]
        self.assertFalse(min(r[2], isl[2]) > max(r[0], isl[0]) and min(r[3], isl[3]) > max(r[1], isl[1]))
        CP.BAND_RESERVE = "padded"
        self.assertEqual(CP._storage_band(ty, "wide_i", 63, [])["rect_um"], CP._storage_band(_type(), "wide_i", 63, [])["rect_um"])

    def test_band_spread_default_unchanged(self):
        # DIE-HEAD-12: BAND_SPREAD 1.0 (default) leaves every band byte-identical and adds no spread key
        CP.BAND_RESERVE = "ring_ff"
        b = CP._storage_band(_type(), "wide_i", 63, [])
        self.assertNotIn("spread", b)
        CP.BAND_SPREAD = 2.0
        s = CP._storage_band(_type(), "wide_i", 63, [])
        self.assertEqual(s["area_reserve_um2"], b["area_reserve_um2"])
        r = s["rect_um"]
        self.assertAlmostEqual((r[2] - r[0]) * (r[3] - r[1]) / s["area_reserve_um2"], s["spread"], places=3)
        self.assertGreaterEqual(s["spread"], 2.0 - 1e-6)

    def test_band_spread_steps_down_to_fit_reach(self):
        # a band that cannot be 2x within the 405-um reach of its pin steps the spread down (never past reach / macros)
        CP.BAND_RESERVE = "ring_ff"
        CP.BAND_SPREAD = 4.0
        ty = _type()
        ty["hard_cores"] = [dict(origin_um=[0.0, 40.0], outline_um=[400.0, 260.0]),
                            dict(origin_um=[150.0, 0.0], outline_um=[250.0, 40.0])]   # pocket ~128 x 18 um: 4x does not fit
        s = CP._storage_band(ty, "wide_i", 63, [])
        r = s["rect_um"]
        self.assertLess(s["spread"], 4.0)
        self.assertGreater(s["spread"], 1.0)
        self.assertLessEqual(s["max_pin_to_band_hop_um"], 405 - 2.16)
        self.assertLessEqual(r[3], 40.0 - 4.32)
        self.assertLessEqual(r[2], 150.0 - 4.32)

    def test_compose_band_spread_needs_ring_ff(self):
        with self.assertRaises(ValueError):
            CP.compose(dict(), dict(), band_reserve="padded", band_spread=2.0)

    def test_compose_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            CP.compose(dict(), dict(), band_reserve="tiny")


if __name__ == "__main__":
    unittest.main()
