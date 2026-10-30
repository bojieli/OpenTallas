"""DIE-KV-32 10-29: fix-only resize_undersized_bands (clock_landing_plan) re-sizes, in the named types only, the ring
bands below the ring_ff reserve; bands that meet it, monitor bands and other types stay byte-identical."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402

GEOM = {"wide_i": dict(name="wide_i", face="S", window_um=[100.0, 160.0], width=64),
        "ft1_i": dict(name="ft1_i", face="S", window_um=[300.0, 300.432], width=1)}


def _plan():
    def ty():
        return dict(outline_um=[400.0, 300.0], hard_cores=[], buses=[], clock=dict(landing_contract=dict(pins=[], bands={})))
    p = dict(partition_types=dict(a=ty(), b=ty()))
    CP.BAND_RESERVE = "live"     # the KV event26 compose mode: undersized for the count-aligned ring
    t = copy.deepcopy(p["partition_types"]["a"]);t["_cland_geom"] = GEOM
    small = CP._storage_band(t, "wide_i", 63, [])
    CP.BAND_RESERVE = "ring_ff"
    big = CP._storage_band(t, "ft1_i", 1, [small["rect_um"]])
    CP.BAND_RESERVE = "padded"
    for tn in p["partition_types"]:
        p["partition_types"][tn]["clock"]["landing_contract"]["bands"] = dict(
            wide_i=dict(small, instance="u_cland_wide_i"), ft1_i=dict(big, instance="u_cland_ft1_i"),
            monitor_0=dict(rect_um=[17.28, 200.0, 25.92, 208.64], width=2))
    side = dict(collector=dict(types={tn: dict(bus_geometry=GEOM) for tn in p["partition_types"]}))
    return p, side


def _area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


class BandResize(unittest.TestCase):
    def tearDown(self):
        CP.BAND_RESERVE = "padded"

    def test_undersized_band_grows_to_ring_ff_reserve(self):
        p, side = _plan()
        old = p["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["wide_i"]["rect_um"]
        self.assertLess(_area(old), CP.ring_ff_reserve_um2(63))
        new, rep = CP.resize_undersized_bands(p, side, ["a"])
        b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["wide_i"]
        self.assertGreaterEqual(_area(b["rect_um"]) + 1e-6, CP.ring_ff_reserve_um2(63))
        self.assertEqual((b["instance"], b["resized_from_um"]), ("u_cland_wide_i", old))
        self.assertLessEqual(b["max_pin_to_band_hop_um"], 405)
        self.assertEqual([r["bus"] for r in rep], ["wide_i"])
        self.assertEqual(CP.BAND_RESERVE, "padded")          # module mode restored

    def test_resized_band_avoids_the_other_bands(self):
        p, side = _plan()
        new, _ = CP.resize_undersized_bands(p, side, ["a"])
        bands = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]
        r = bands["wide_i"]["rect_um"]
        for k in ("ft1_i", "monitor_0"):
            o = bands[k]["rect_um"]
            self.assertFalse(min(r[2], o[2]) > max(r[0], o[0]) and min(r[3], o[3]) > max(r[1], o[1]), k)

    def test_sufficient_monitor_and_other_types_unchanged(self):
        p, side = _plan()
        new, _ = CP.resize_undersized_bands(p, side, ["a"])
        for k in ("ft1_i", "monitor_0"):
            self.assertEqual(new["partition_types"]["a"]["clock"]["landing_contract"]["bands"][k],
                             p["partition_types"]["a"]["clock"]["landing_contract"]["bands"][k])
        self.assertEqual(new["partition_types"]["b"], p["partition_types"]["b"])
        self.assertNotIn("_cland_geom", new["partition_types"]["a"])

    def test_kv_io_ft_ring_reserve_covers_the_mapped_ring(self):
        # CHECKED 10-29 kits_gen4 kv3_io_ft 2_floorplan.odb: u_cland_ft0_i W=523 maps 11853 cells, 3901.6 um2 reserved
        # at 40 % fill (live band 2641 um2 -> 3_3 "no legal nonoverlapping row/site"); hroot ft10_i W=33: 350.8 um2
        self.assertGreaterEqual(CP.ring_ff_reserve_um2(523), 3901.6)
        self.assertGreaterEqual(CP.ring_ff_reserve_um2(33), 350.8)


def _ov(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


class BandResetSites(unittest.TestCase):
    """FLOW-7 10-30 (DIE-KV-43 KV-022 SD try5 3_3 'u_cland_collect_rst_rl_39 ... band upper bound 0.0 um2'): ring bands
    avoid the type's reset relay / collector sites (the 4.32-um landing_place collector box around each relay xy)."""
    def tearDown(self):
        CP.BAND_RESERVE = "padded"

    def _t(self):
        t = dict(outline_um=[400.0, 300.0], hard_cores=[], buses=[], clock=dict(landing_contract=dict(pins=[], bands={})))
        t["_cland_geom"] = GEOM
        return t

    def test_reset_sites_require_selected_type_or_base_type(self):
        tree = dict(root=[10.0, 20.0], relays=[])
        self.assertEqual(CP._reset_sites_for_type({}, "a", tree), [])
        p = dict(budgets=dict(cland_avoid_reset_types=["a"]))
        self.assertEqual(CP._reset_sites_for_type(p, "a", tree), CP.reset_site_rects(tree))
        self.assertEqual(CP._reset_sites_for_type(p, "b", tree), [])
        self.assertEqual(CP._reset_sites_for_type(p, "a__variant", tree, "a"), CP.reset_site_rects(tree))

    def test_reset_site_rects_are_the_collector_boxes(self):
        tree = dict(root=[10.0, 20.0], relays=[dict(q="rst_rl_39", d="x", xy=[1750.0, 30.24]),
                                                 dict(q="rst_n_t0", d="x", xy=[1750.0, 30.24])])
        self.assertEqual(CP.reset_site_rects(tree), [[1747.84, 28.08, 1752.16, 32.4], [7.84, 17.84, 12.16, 22.16]])
        self.assertEqual(CP.reset_site_rects(None), [])

    def test_band_over_a_relay_site_moves_off_it(self):
        t = self._t()
        free = CP._storage_band(t, "wide_i", 63, [])
        x0, y0, x1, y1 = free["rect_um"]
        site = [[(x0 + x1) / 2 - 2.16, (y0 + y1) / 2 - 2.16, (x0 + x1) / 2 + 2.16, (y0 + y1) / 2 + 2.16]]
        b = CP._storage_band(t, "wide_i", 63, [], resets=site)
        self.assertFalse(_ov(b["rect_um"], site[0]))
        self.assertEqual(b["reset_sites_avoided_um"], site)
        self.assertLessEqual(b["max_pin_to_band_hop_um"], 405)

    def test_band_clear_of_relay_sites_is_byte_identical(self):
        t = self._t()
        free = CP._storage_band(t, "wide_i", 63, [])
        far = [[380.0, 280.0, 384.32, 284.32]]
        self.assertFalse(_ov(free["rect_um"], far[0]))
        self.assertEqual(CP._storage_band(t, "wide_i", 63, [], resets=far), free)

    def test_resize_moves_a_sized_band_off_a_reset_site(self):
        p, side = _plan()
        CP.BAND_RESERVE = "ring_ff"
        t = copy.deepcopy(p["partition_types"]["a"]);t["_cland_geom"] = GEOM
        big = CP._storage_band(t, "wide_i", 63, [p["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["ft1_i"]["rect_um"]])
        CP.BAND_RESERVE = "padded"
        for tn in ("a", "b"):
            p["partition_types"][tn]["clock"]["landing_contract"]["bands"]["wide_i"] = dict(big, instance="u_cland_wide_i")
        x0, y0, x1, y1 = big["rect_um"];cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        side["collector"]["types"]["a"]["tree"] = dict(root=[390.0, 290.0], relays=[dict(q="rst_rl_39", d="rst_root_n", xy=[cx, cy])])
        # Without the explicit plan opt-in even a sized band over a relay is unchanged.
        old, rep = CP.resize_undersized_bands(p, side, ["a", "b"])
        self.assertEqual(old, p)
        self.assertEqual(rep, [])
        p["budgets"] = dict(cland_avoid_reset_types=["a"])
        new, rep = CP.resize_undersized_bands(p, side, ["a", "b"])
        b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["wide_i"]
        self.assertFalse(_ov(b["rect_um"], [cx - 2.16, cy - 2.16, cx + 2.16, cy + 2.16]))
        self.assertIn("reset relay/collector site", b["resize"])
        self.assertEqual([(r["type"], r["bus"]) for r in rep], [("a", "wide_i")])   # b has no tree: unchanged
        self.assertEqual(new["partition_types"]["b"], p["partition_types"]["b"])


if __name__ == "__main__":
    unittest.main()
