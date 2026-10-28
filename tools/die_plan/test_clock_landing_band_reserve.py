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
        self.assertAlmostEqual(b["area_reserve_um2"], (5 * 64 + 160) * 4177.4 / 2949, places=3)
        self.assertGreaterEqual((5 * 576 + 160) * CP.RING_FF_RESERVE_UM2, 4177.4)
        rect = b["rect_um"]
        self.assertGreaterEqual((rect[2] - rect[0]) * (rect[3] - rect[1]) + 1e-6, b["area_reserve_um2"])

    def test_compose_accepts_ring_ff(self):
        self.assertIn("ring_ff", CP.BAND_MODES)

    def test_compose_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            CP.compose(dict(), dict(), band_reserve="tiny")


if __name__ == "__main__":
    unittest.main()
