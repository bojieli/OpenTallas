"""DIE-QC-97 11-09: resize_undersized_bands relocates a wide ring band that sits off its own pin window.

cbf_q00__cl870de686 (plan_qc53v4nS_mem9_vml_pv cand7) GRT-0116 at attempt_17: 65 of 66 overflow gcells in x 0..100 /
y 2450..2531.  The na_i00 band (514 bits, N pins x 94.46..183.38) had been resized (DIE-KV-32) into the W gutter corner
[28.08,2425.33,79.92,2514.24], because the 51.84-um N face strip does not fit above hard core u_t01 (top 2462.4 +
CLEAR_UM 4.32 leaves 47.52 um).  All 514 bits then ran along the N face past bc_o01's 517 pins and bout flops into a
corner at 60-97 % cell density.  The fix searches such a band again (FACE_CROSSING) and also tries shallower bands
longer than the window that still cover it (_face_wide_boxes)."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402

W, H = 1235.52, 2531.52
OLD_NA = [28.08, 2425.328, 79.92, 2514.24]
GEOM = {"na_i00": dict(name="na_i00", face="N", window_um=[94.464, 183.376], width=514),
        "bc_i00": dict(name="bc_i00", face="S", window_um=[4.32, 93.34], width=516)}


def _core(inst, x, y):
    return dict(inst=inst, module="qfd_tile_nk_a0c", origin_um=[x, y], outline_um=[457.92, 1157.76], orient="R0")


def _plan(na_rect=OLD_NA):
    t = dict(outline_um=[W, H], buses=[], hard_cores=[_core("u_t00", 86.4, 77.76), _core("u_t01", 86.4, 1304.64),
                                                      _core("u_t10", 691.2, 77.76), _core("u_t11", 691.2, 1304.64)],
             clock=dict(landing_contract=dict(pins=[], bands={
                 "na_i00": dict(rect_um=list(na_rect), width=514, instance="u_cland_na_i00", ring_place="ff"),
                 "bc_i00": dict(rect_um=[17.28, 17.28, 106.464, 69.12], width=516, instance="u_cland_bc_i00")})))
    return dict(partition_types=dict(cbf=t)), dict(collector=dict(types=dict(cbf=dict(bus_geometry=GEOM))))


class Relocate(unittest.TestCase):
    def test_old_band_is_off_window(self):
        t = dict(outline_um=[W, H], _cland_geom=GEOM)
        dm, cap = CP.face_crossing(t, "na_i00", OLD_NA, 514)
        self.assertAlmostEqual(dm, 514.0, places=3)                 # every bit runs along the face

    def test_na_i00_moves_onto_its_window_above_the_core(self):
        p, side = _plan()
        new, rep = CP.resize_undersized_bands(p, side, ["cbf"])
        b = new["partition_types"]["cbf"]["clock"]["landing_contract"]["bands"]["na_i00"]
        r = b["rect_um"]
        self.assertLessEqual(r[0], 94.464 + 1e-6)
        self.assertGreaterEqual(r[2], 183.376 - 1e-6)                # covers the whole pin window
        self.assertGreaterEqual(r[1], 2462.4 + 4.32 - 1e-6)          # above u_t01 + clearance
        self.assertLessEqual(r[3], H - 17.28 + 1e-6)
        self.assertGreaterEqual((r[2] - r[0]) * (r[3] - r[1]) + 1e-6, CP.ring_ff_reserve_um2(514))
        self.assertEqual(b["ring_place"], "ff")
        self.assertEqual(b["resized_from_um"], OLD_NA)
        self.assertEqual([x["bus"] for x in rep], ["na_i00"])
        self.assertEqual(rep[0]["crossing_bits"][1], 0.0)
        self.assertFalse(CP.FACE_CROSSING)

    def test_on_window_band_stays_byte_identical(self):
        on = [86.0, 2471.04, 191.84, 2514.24]
        p, side = _plan(on)
        new, rep = CP.resize_undersized_bands(p, side, ["cbf"])
        self.assertEqual(rep, [])
        self.assertEqual(new, p)

    def test_wide_search_only_with_face_crossing(self):
        p, _ = _plan()
        t = copy.deepcopy(p["partition_types"]["cbf"]);t["_cland_geom"] = GEOM
        t["clock"]["landing_contract"]["bands"] = {}
        saved = CP.BAND_RESERVE
        CP.BAND_RESERVE = "ring_ff"
        try:
            a = CP._storage_band(copy.deepcopy(t), "na_i00", 514, [])   # FACE_CROSSING off: legacy rule, W gutter
            CP.FACE_CROSSING = True
            b = CP._storage_band(copy.deepcopy(t), "na_i00", 514, [])
        finally:
            CP.BAND_RESERVE, CP.FACE_CROSSING = saved, False
        self.assertGreater(CP.face_crossing(t, "na_i00", a["rect_um"], 514)[0], 257)
        self.assertEqual(CP.face_crossing(t, "na_i00", b["rect_um"], 514)[0], 0.0)


if __name__ == "__main__":
    unittest.main()
