"""CLAND-CLASS-1 11-11: band-use floor (clock_landing_plan BAND_USE_MAX / ca_ring_reserve40_um2).  KV kv3_hgi_v1 ft1_i
(W=16) failed 3_3_place_gp "OT_CLAND no legal nonoverlapping row/site in reserved band": its live-mode band (261.3 um2)
is below the mapped CA ring 40 % reserve (327.9 um2).  Every ring band is sized so that the reserve uses <= 0.5."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402

# (plan width, measured reserve40 um2) on mapped netlists: KV kv3_hgi_v1 cas W=2/16/1057, HEAD hd_tile ca W=567
MEASURED = [(1, 253.0), (15, 327.9), (1056, 7732.6), (566, 4177.4)]


def _type():
    return dict(outline_um=[400.0, 300.0], hard_cores=[],
                buses=[dict(name="ft1_i", face="S", window_um=[200.0, 200.432], width=15),
                       dict(name="wide_i", face="S", window_um=[100.0, 160.0], width=1056)])


def _area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


class BandUseFloor(unittest.TestCase):
    def tearDown(self):
        CP.BAND_RESERVE = "padded"
        CP.BAND_SPREAD = 1.0
        CP.BAND_USE_MAX = None

    def test_model_covers_measured_mapped_rings(self):
        for w, meas in MEASURED:
            r = CP.ca_ring_reserve40_um2(w)
            self.assertGreaterEqual(r, meas, w)
            self.assertLessEqual(r, meas * 1.01, w)

    def test_ff_form_reserves_flops_only(self):
        # ring_place "ff" (only the flops FIRM): measured flop reserve 111.5 / 152.4 / 4027.7 um2 (0.729 um2 per flop)
        for (w, _), meas_ff, ff in zip(MEASURED[:3], (111.5, 152.4, 4027.7), (153, 209, 5525)):
            self.assertEqual(CP.ca_ring_flops(w), ff)
            self.assertAlmostEqual(CP.ca_ring_reserve40_um2(w, ring_place="ff"), meas_ff, delta=0.1)
        self.assertLess(CP.band_use(1056, 8000, ring_place="ff"), CP.band_use(1056, 8000))

    def test_kv_failing_band_is_over(self):
        # the failing kit band: 30.24 x 8.64 um, width 15 -> reserve does not fit (use > 1)
        self.assertGreater(CP.band_use(15, 30.24 * 8.64), 1.0)
        self.assertLessEqual(CP.band_use(15, 2 * 30.24 * 8.64), 1.0)       # DIE-KV-98 vE2 2x: fits, use ~0.66
        self.assertGreater(CP.band_use(15, 2 * 30.24 * 8.64), 0.5)

    def test_default_is_byte_identical(self):
        CP.BAND_RESERVE = "live"
        s = CP._storage_band(_type(), "ft1_i", 15, [])
        self.assertNotIn("band_use", s)
        self.assertLess(_area(s["rect_um"]), CP.ca_ring_reserve40_um2(15))   # the old undersized band

    def test_floor_sizes_band_at_half_use_in_every_mode(self):
        for mode in CP.BAND_MODES:
            CP.BAND_RESERVE = mode
            CP.BAND_USE_MAX = 0.5
            for bus, w in (("ft1_i", 15), ("wide_i", 1056)):
                s = CP._storage_band(_type(), bus, w, [])
                self.assertLessEqual(s["band_use"], 0.5 + 1e-6, (mode, bus))
                self.assertEqual(s["band_use_target"], 0.5)
                self.assertLessEqual(s["max_pin_to_band_hop_um"], 405)

    def test_use_steps_up_when_half_does_not_fit(self):
        CP.BAND_RESERVE = "live"
        CP.BAND_USE_MAX = 0.5
        ty = _type()
        ty["hard_cores"] = [dict(inst="u_core", origin_um=[0.0, 60.0], outline_um=[400.0, 240.0])]   # 400 x 60 um strip only
        s = CP._storage_band(ty, "wide_i", 1056, [])
        self.assertGreater(s["band_use_target"], 0.5)
        self.assertLessEqual(s["band_use"], s["band_use_target"] + 1e-6)
        self.assertLessEqual(s["rect_um"][3], 60.0)

    def test_resize_use_max_grows_and_default_unchanged(self):
        CP.BAND_RESERVE = "live"
        t = _type()
        t["clock"] = dict(landing_contract=dict(pins=[], bands={}))
        old = CP._storage_band(t, "ft1_i", 15, [])
        CP.BAND_RESERVE = "padded"
        t["clock"]["landing_contract"]["bands"] = dict(ft1_i=dict(old, instance="u_cland_ft1_i"))
        p = dict(partition_types=dict(a=t))
        geom = {b["name"]: b for b in t["buses"]}
        side = dict(collector=dict(types=dict(a=dict(bus_geometry=geom))))
        new, rep = CP.resize_undersized_bands(p, side, ["a"], use_max=0.5)
        b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["ft1_i"]
        self.assertLessEqual(CP.band_use(15, _area(b["rect_um"])), 0.5 + 1e-6)
        self.assertEqual([r["bus"] for r in rep], ["ft1_i"])
        self.assertIsNone(CP.BAND_USE_MAX)                                     # module state restored
        rows = CP.band_use_report(p)
        self.assertTrue(rows[0]["over"] and not rows[0]["reserve_fits"])
        self.assertFalse(CP.band_use_report(new)[0]["over"])

    def _pocket(self, x1, top=40.0):
        # macro-free pocket x 17.28..x1-4.32, y 17.28..top-4.32 (4.32-um core halo); the bus pin sits inside it
        t = dict(outline_um=[400.0, 300.0],
                 hard_cores=[dict(inst="u_top", origin_um=[0.0, top], outline_um=[400.0, 300.0 - top]),
                             dict(inst="u_right", origin_um=[x1, 0.0], outline_um=[400.0 - x1, top])],
                 buses=[dict(name="ft1_i", face="S", window_um=[30.0, 30.432], width=15)])
        t["clock"] = dict(landing_contract=dict(pins=[], bands={}))
        CP.BAND_RESERVE = "live"
        old = CP._storage_band(t, "ft1_i", 15, [])
        CP.BAND_RESERVE = "padded"
        t["clock"]["landing_contract"]["bands"] = dict(ft1_i=dict(old, instance="u_cland_ft1_i"))
        side = dict(collector=dict(types=dict(a=dict(bus_geometry={b["name"]: b for b in t["buses"]}))))
        return dict(partition_types=dict(a=t)), side, old

    def test_resize_steps_use_when_half_does_not_fit(self):
        # COORD 11-11 (KV ft10/ft19/ft24): resize-bands steps 0.55..1.0 like compose instead of failing at use_max
        p, side, old = self._pocket(50.0)      # live 280 and use-1.0 364 um2 fit, the 0.5 floor (~692) does not
        new, rep = CP.resize_undersized_bands(p, side, ["a"], use_max=0.5)
        b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["ft1_i"]
        self.assertGreater(b["band_use_target"], 0.5)
        self.assertLessEqual(b["band_use"], b["band_use_target"] + 1e-6)
        self.assertLessEqual(b["rect_um"][2], 50.0 - 4.32 + 1e-6)
        self.assertLessEqual(b["rect_um"][3], 40.0 - 4.32 + 1e-6)
        self.assertEqual((rep[0]["band_use"], rep[0]["band_use_target"]), (b["band_use"], b["band_use_target"]))

    def test_resize_without_fit_keeps_band_and_reports(self):
        p, side, old = self._pocket(40.0)      # the live band fits, not even the use-1.0 reserve does
        new, rep = CP.resize_undersized_bands(p, side, ["a"], use_max=0.5)
        b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["ft1_i"]
        self.assertEqual(b["rect_um"], old["rect_um"])
        self.assertIsNone(rep[0]["new_rect_um"])
        self.assertIn("error", rep[0])

    def test_compose_rejects_bad_use_and_restores(self):
        with self.assertRaises(ValueError):
            CP.compose({}, {}, band_use_max=2.0)
        self.assertIsNone(CP.BAND_USE_MAX)


if __name__ == "__main__":
    unittest.main()
