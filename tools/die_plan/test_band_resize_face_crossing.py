"""DIE-QC-97 11-09: resize_undersized_bands keeps a wide face band on its own pin window.

sle_hc1__cl22c1ff36 (plan_qc53v4w): DIE-KV-32 resized b_hw_i (1573 bits, S pins x 4.32..276.29) from
[17.28,17.28,289.25,45.36] to [108.53,17.28,380.50,62.64], because the deeper rect overlapped rs_n1's OLD rect
[17.28,47.52,106.37,77.76], which was itself resized away right after.  About 600 bits then crossed a 17.28-um strip
along the S face: GRT-0116 with 18833 overflow, all of it in y 0..40 / x 100..360.  The fix resizes every undersized
band of a type as one set (old rects of bands being resized are no obstacle), widest first, and ranks candidates by the
along-face crossing demand vs the strip's parallel tracks (face_crossing)."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402

GEOM = {"b_hw_i": dict(name="b_hw_i", face="S", window_um=[4.32, 276.288], width=1573),
        "rs_n0": dict(name="rs_n0", face="W", window_um=[94.368, 183.36], width=514),
        "rs_n1": dict(name="rs_n1", face="W", window_um=[4.32, 93.408], width=514)}
OLD = {"b_hw_i": ([17.28, 17.28, 289.248, 45.36], 1573), "rs_n1": ([17.28, 47.52, 106.368, 77.76], 514),
       "rs_n0": ([17.28, 94.368, 47.52, 183.36], 514)}


def _plan():
    t = dict(outline_um=[613.44, 1339.2], hard_cores=[], buses=[], clock=dict(landing_contract=dict(pins=[], bands={
        b: dict(rect_um=list(r), width=w, instance="u_cland_" + b) for b, (r, w) in OLD.items()})))
    return dict(partition_types=dict(hc1=t)), dict(collector=dict(types=dict(hc1=dict(bus_geometry=GEOM))))


def _overlap(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


class FaceCrossing(unittest.TestCase):
    def test_crossing_demand_counts_bits_outside_the_span(self):
        t = dict(outline_um=[613.44, 1339.2], _cland_geom=GEOM)
        dm, cap = CP.face_crossing(t, "b_hw_i", [108.528, 17.28, 380.496, 62.64], 1573)   # the failed hc1 band
        self.assertAlmostEqual(dm, 1573 * (108.528 - 4.32) / (276.288 - 4.32), places=3)
        self.assertGreater(dm, cap)                                  # ~603 bits over ~536 tracks x 0.5
        dm2, cap2 = CP.face_crossing(t, "b_hw_i", [17.28, 17.28, 289.248, 62.64], 1573)
        self.assertLess(dm2, cap2)

    def test_hc1_b_hw_i_stays_on_its_pin_window(self):
        p, side = _plan()
        new, rep = CP.resize_undersized_bands(p, side, ["hc1"])
        bands = new["partition_types"]["hc1"]["clock"]["landing_contract"]["bands"]
        b = bands["b_hw_i"]["rect_um"]
        t = dict(outline_um=[613.44, 1339.2], _cland_geom=GEOM)
        dm, cap = CP.face_crossing(t, "b_hw_i", b, 1573)
        self.assertLessEqual(dm, cap, b)
        self.assertLessEqual(b[0], 17.28 + 1e-6)
        self.assertGreaterEqual(b[2] - b[0], 270.0)
        self.assertEqual(rep[0]["bus"], "b_hw_i")                    # widest first
        names = sorted(bands)
        for i, k in enumerate(names):
            self.assertGreaterEqual((bands[k]["rect_um"][2] - bands[k]["rect_um"][0]) *
                                    (bands[k]["rect_um"][3] - bands[k]["rect_um"][1]) + 1e-6,
                                    CP.ring_ff_reserve_um2(OLD[k][1]), k)
            for q in names[i + 1:]:
                self.assertFalse(_overlap(bands[k]["rect_um"], bands[q]["rect_um"]), (k, q))
        self.assertFalse(CP.FACE_CROSSING)                          # module mode restored

    def test_resize_keeps_ring_place(self):
        p, side = _plan()
        bands = p["partition_types"]["hc1"]["clock"]["landing_contract"]["bands"]
        bands["b_hw_i"]["ring_place"] = "ff"; bands["rs_n1"]["ring_place"] = "ff"
        new, rep = CP.resize_undersized_bands(p, side, ["hc1"])
        nb = new["partition_types"]["hc1"]["clock"]["landing_contract"]["bands"]
        self.assertIn("b_hw_i", [r["bus"] for r in rep])
        self.assertEqual(nb["b_hw_i"].get("ring_place"), "ff")
        self.assertEqual(nb["rs_n1"].get("ring_place"), "ff")
        self.assertNotIn("ring_place", nb["rs_n0"])                # untagged band stays untagged

    def test_compose_default_unchanged(self):
        self.assertFalse(CP.FACE_CROSSING)
        t = dict(outline_um=[613.44, 1339.2], hard_cores=[], buses=[], _cland_geom=GEOM,
                 clock=dict(landing_contract=dict(pins=[], bands={})))
        a = CP._storage_band(copy.deepcopy(t), "rs_n0", 514, [])
        CP.FACE_CROSSING = True
        try:
            b = CP._storage_band(copy.deepcopy(t), "rs_n0", 514, [])
        finally:
            CP.FACE_CROSSING = False
        self.assertEqual(a["rect_um"], b["rect_um"])               # an aligned free face strip is the same rect


if __name__ == "__main__":
    unittest.main()
