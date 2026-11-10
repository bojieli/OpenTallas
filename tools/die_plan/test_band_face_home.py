"""DIE-QC-97 11-10: face-home (rehome_far_bands) re-sites ring bands that sit far from their own pin face.

slw_st_a_v2__cl9f076a5c (plan_qc53v4nS_mem9_vml, job 4fccfeabe37d, GRT-0116, overflow 200 all at x 476..565 /
y 167..180): DIE-KV-32 resize put b_hw_ctl_hc0_i (1573 bits, E pins y 4.32..276.51) on a S-face bank
[332.608,60.48,604.8,105.84] (its pin window reaches into the 17.28-um margin, so no E face strip was legal), and
x_fw_ctl_i (536 bits, S pins x 476.06..568.22) then went to [476.016,168.48,568.224,218.16], 168.48 um north of its
pins, above SRAM btb[0] (+4.32 um reset clearance).  Its 2821 ring flops sat in the 11.88-um strip at y 168.5..180.4.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402

W, H = 622.08, 1339.2
GEOM = {"b_hw_ctl_hc0_i": dict(name="b_hw_ctl_hc0_i", face="E", window_um=[4.32, 276.512], width=1574),
        "x_fw_ctl_i": dict(name="x_fw_ctl_i", face="S", window_um=[476.064, 568.224], width=537),
        "b_tw_data_i": dict(name="b_tw_data_i", face="E", window_um=[277.656, 464.232], width=1081),
        "rs_s0": dict(name="rs_s0", face="S", window_um=[185.88, 274.584], width=515)}
OLD = {"b_hw_ctl_hc0_i": ([332.608, 60.48, 604.8, 105.84], 1573),
       "x_fw_ctl_i": ([476.016, 168.48, 568.224, 218.16], 536),
       "b_tw_data_i": ([559.44, 277.472, 604.8, 464.384], 1080),
       "rs_s0": ([185.704, 17.28, 274.6, 69.12], 514)}
BTB0 = dict(inst="u_bound.u_u_btab.u_bt.u_core.g_btb[0].u_m", module="ot_sram_1r1w_128x256_m1_r2c2",
            origin_um=[449.28, 120.96], track_offset_um=[0.0, 0.012], outline_um=[94.824, 41.064], orient="R0",
            halo_um=4.32)


def _plan(budgets=None):
    t = dict(outline_um=[W, H], hard_cores=[copy.deepcopy(BTB0)], buses=[], clock=dict(landing_contract=dict(
        pins=[], bands={b: dict(rect_um=list(r), width=w, instance="u_cland_" + b, ring_place="ff")
                        for b, (r, w) in OLD.items()})))
    p = dict(partition_types=dict(slw=t), budgets=dict(budgets or {}))
    return p, dict(collector=dict(types=dict(slw=dict(bus_geometry=GEOM))))


def _overlap(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


class FaceHome(unittest.TestCase):
    def test_slw_bands_go_home(self):
        p, side = _plan()
        new, rep = CP.rehome_far_bands(p, side, ["slw"])
        nb = new["partition_types"]["slw"]["clock"]["landing_contract"]["bands"]
        self.assertEqual([r["bus"] for r in rep], ["b_hw_ctl_hc0_i", "x_fw_ctl_i"])   # widest first
        self.assertEqual(nb["b_hw_ctl_hc0_i"]["rect_um"], [557.28, 17.28, 604.8, 276.512])
        self.assertEqual(nb["x_fw_ctl_i"]["rect_um"], [465.12, 17.28, 557.28, 66.96])
        t = dict(outline_um=[W, H], _cland_geom=GEOM)
        for bus in ("b_hw_ctl_hc0_i", "x_fw_ctl_i"):
            r = nb[bus]["rect_um"]
            self.assertAlmostEqual(CP.face_distance(t, bus, r), 17.28, places=6)
            dm, cap = CP.face_crossing(t, bus, r, OLD[bus][1])
            self.assertLessEqual(dm, cap, bus)
            self.assertGreaterEqual((r[2] - r[0]) * (r[3] - r[1]) + 1e-6, CP.ring_ff_reserve_um2(OLD[bus][1]), bus)
            self.assertEqual(nb[bus]["ring_place"], "ff")
            self.assertEqual(nb[bus]["resized_from_um"], OLD[bus][0])
        for bus in ("b_tw_data_i", "rs_s0"):                      # near-face bands: byte-identical obstacles
            self.assertEqual(nb[bus], p["partition_types"]["slw"]["clock"]["landing_contract"]["bands"][bus])
        names = sorted(nb)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertFalse(_overlap(nb[a]["rect_um"], nb[b]["rect_um"]), (a, b))
        btb = [449.28 - 4.32, 120.96 - 4.32, 449.28 + 94.824 + 4.32, 120.96 + 41.064 + 4.32]
        for bus in names:
            self.assertFalse(_overlap(nb[bus]["rect_um"], btb), bus)
        self.assertFalse(CP.FACE_HOME)                               # module modes restored
        self.assertFalse(CP.FACE_CROSSING)
        self.assertEqual(CP.BAND_RESERVE, "padded")

    def test_budget_selects_types(self):
        p, side = _plan(dict(cland_face_home_types=["slw"]))
        self.assertEqual(CP.face_home_types(p), ["slw"])
        _, rep = CP.rehome_far_bands(p, side)
        self.assertEqual(len(rep), 2)
        p2, side2 = _plan()
        self.assertEqual(CP.face_home_types(p2), [])
        new, rep2 = CP.rehome_far_bands(p2, side2)
        self.assertEqual(rep2, [])
        self.assertEqual(json.dumps(new, sort_keys=True), json.dumps(p2, sort_keys=True))   # unselected: byte-same

    def test_default_band_search_unchanged(self):
        # FACE_HOME is off outside rehome_far_bands: resize_undersized_bands / compose never enter the clamped
        # corner-window search, so their plans are byte-identical
        self.assertFalse(CP.FACE_HOME)
        real = CP._face_clamped_boxes

        def boom(*a, **k):
            raise AssertionError("clamped search entered with FACE_HOME off")
        CP._face_clamped_boxes = boom
        try:
            p, side = _plan()
            bands = p["partition_types"]["slw"]["clock"]["landing_contract"]["bands"]
            bands["b_hw_ctl_hc0_i"]["rect_um"] = [576.72, 17.28, 604.8, 289.472]    # pre-resize rects (plan history)
            bands["x_fw_ctl_i"]["rect_um"] = [476.016, 17.28, 568.224, 47.52]
            CP.resize_undersized_bands(p, side, ["slw"])
        finally:
            CP._face_clamped_boxes = real
        t = dict(outline_um=[W, H], hard_cores=[copy.deepcopy(BTB0)], buses=[], _cland_geom=GEOM,
                 clock=dict(landing_contract=dict(pins=[], bands={})))
        b = CP._face_clamped_boxes(t, GEOM["b_hw_ctl_hc0_i"], W, H, [OLD["b_tw_data_i"][0]], 17.28, W, 140.416,
                                   CP.ring_ff_reserve_um2(1573))
        self.assertEqual(b, [[557.28, 17.28, 604.8, 276.512]])                    # clamped into the 17.28-um margin

    def test_near_face_band_never_traded_for_a_far_one(self):
        # sle_su_c cws1_i form: an off-window band at its face whose only lower-crossing rect is > far_um from the face
        # stays where it is (the first rule set moved it 17.28 -> 205.2 um)
        geom = {"a": dict(name="a", face="S", window_um=[4.32, 300.0], width=512)}
        t = dict(outline_um=[600.0, 600.0], hard_cores=[], buses=[], clock=dict(landing_contract=dict(pins=[], bands={
            "a": dict(rect_um=[300.0, 17.28, 420.0, 66.96], width=512, instance="u_cland_a"),
            "blk": dict(rect_um=[17.28, 17.28, 299.0, 200.0], width=32, instance="u_cland_blk")})))
        p = dict(partition_types=dict(x=t), budgets={})
        side = dict(collector=dict(types=dict(x=dict(bus_geometry=geom))))
        new, rep = CP.rehome_far_bands(p, side, ["x"])
        self.assertEqual(rep, [])
        self.assertEqual(json.dumps(new, sort_keys=True), json.dumps(p, sort_keys=True))


    def test_type_declared_bus_without_sidecar_geometry_is_a_candidate(self):
        # sle_st_a_v1 / slw_st_a_v1 (5 types): x_fw_i (258 bits) declares its S face/window on the TYPE bus, so the
        # compose sidecar (seam/port-inferred windows only) has no bus_geometry row for it.  Filtering candidates on
        # the sidecar kept it a fixed obstacle at [525.088,168.48,569.728,228.96] (168.48 um from its pins), which
        # blocked the clamped E strip of b_hw_ctl_hc0_i, so nothing moved.  Its own declared geometry makes it a
        # candidate: all three bands go home and stay legal.
        p, side = _plan()
        t = p["partition_types"]["slw"]
        bands = t["clock"]["landing_contract"]["bands"]
        bands["x_fw_ctl_i"]["rect_um"] = [385.728, 168.48, 478.496, 218.16]
        bands["x_fw_i"] = dict(rect_um=[525.088, 168.48, 569.728, 228.96], width=258, instance="u_cland_x_fw_i",
                               ring_place="ff")
        t["buses"] = [dict(name="x_fw_i", dir="in", width=258, kind="data", face="S", window_um=[525.088, 569.728],
                           layers=["M7", "M5"], order="lsb_low")]
        geom = copy.deepcopy(GEOM)
        geom["x_fw_ctl_i"] = dict(name="x_fw_ctl_i", face="S", window_um=[385.728, 478.496], width=536)
        side["collector"]["types"]["slw"]["bus_geometry"] = geom
        self.assertNotIn("x_fw_i", geom)
        new, rep = CP.rehome_far_bands(p, side, ["slw"])
        nb = new["partition_types"]["slw"]["clock"]["landing_contract"]["bands"]
        self.assertEqual([r["bus"] for r in rep], ["b_hw_ctl_hc0_i", "x_fw_ctl_i", "x_fw_i"])
        self.assertEqual(nb["b_hw_ctl_hc0_i"]["rect_um"], [557.28, 17.28, 604.8, 276.512])
        self.assertEqual(nb["x_fw_ctl_i"]["rect_um"], [385.728, 17.28, 478.496, 66.96])
        self.assertEqual(nb["x_fw_i"]["rect_um"], [512.64, 17.28, 557.28, 77.76])
        tt = dict(t, _cland_geom=geom)
        for bus, w in (("b_hw_ctl_hc0_i", 1573), ("x_fw_ctl_i", 536), ("x_fw_i", 258)):
            r = nb[bus]["rect_um"]
            self.assertAlmostEqual(CP.face_distance(tt, bus, r), 17.28, places=6)
            dm, cap = CP.face_crossing(tt, bus, r, w)
            self.assertLessEqual(dm, cap, bus)
        names = sorted(nb)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertFalse(_overlap(nb[a]["rect_um"], nb[b]["rect_um"]), (a, b))
        btb = [449.28 - 4.32, 120.96 - 4.32, 449.28 + 94.824 + 4.32, 120.96 + 41.064 + 4.32]
        for bus in names:
            self.assertFalse(_overlap(nb[bus]["rect_um"], btb), bus)
        # a band with no geometry anywhere (neither sidecar nor type bus) is still never a candidate
        t["buses"] = []
        new2, rep2 = CP.rehome_far_bands(p, side, ["slw"])
        self.assertNotIn("x_fw_i", [r["bus"] for r in rep2])
        self.assertEqual(new2["partition_types"]["slw"]["clock"]["landing_contract"]["bands"]["x_fw_i"],
                         bands["x_fw_i"])


if __name__ == "__main__":
    unittest.main()
