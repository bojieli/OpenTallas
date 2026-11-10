"""DIE-S81-85 HCHAN: the horizontal-channel rule sizes a channel from crossing demand, opens it by Y shifts inside the
core, keeps X, refuses what a channel cannot fix, and emits OT_MACRO_MOVES that gen_phys.macro_move_table accepts."""
import unittest

import gen_phys as G
import hchan as H

OBS = ["M1", "M2", "M3", "M4", "M5"]


def dump(macros, nets, core=(0.0, 0.0, 100.0, 100.0)):
    return {"core": list(core), "die": list(core),
            "macros": [{"name": f"u_bound.m{i}", "master": "mm", "box": list(b), "obs": OBS} for i, b in enumerate(macros)],
            "nets": nets}


def street_nets(n, y0, y1, x0=5.0, x1=95.0):
    """n cell-only nets crossing the die left -> right, pins spread over y0..y1 (a bus in a street)."""
    return [[x0, y0 + (y1 - y0) * k / max(1, n - 1), x1, y0 + (y1 - y0) * k / max(1, n - 1), 2, []] for k in range(n)]


class Supply(unittest.TestCase):
    def test_tracks(self):
        self.assertAlmostEqual(H.tracks_per_um(H.H_LAYERS), 0.5 / 0.039 + 0.75 / 0.048 + 0.7 / 0.064, places=6)
        self.assertAlmostEqual(H.tracks_per_um(H.H_LAYERS, set(OBS)), 0.7 / 0.064, places=6)

    def test_measured_over_macro(self):
        m = H.Model(dump([[10, 40, 90, 60]], []), mac_tpu=5.26)
        self.assertAlmostEqual(m.mac_tpu[0], 5.26, places=6)
        m6 = H.Model(dump([[10, 40, 90, 60]], []), mac_tpu=5.26)
        m6.d["macros"][0]["obs"] = OBS + ["M6"]
        self.assertAlmostEqual(H.Model(m6.d, mac_tpu=5.26).mac_tpu[0], 0.0)


class Rule(unittest.TestCase):
    def test_no_demand_no_channel(self):
        r = H.run(dump([[10, 20, 90, 40], [10, 60, 90, 80]], street_nets(50, 45, 55)), mac_tpu=5.26)
        self.assertEqual(r["moves"], [])
        self.assertEqual(r["bands_before"], [])

    def test_street_deficit_opens_channel_by_y_shift(self):
        # street 40..60 between two macro rows carries 39.4 tracks/um x 20 um = 788; 1400 nets need ~36 um
        core = (0.0, 0.0, 100.0, 200.0)
        d = dump([[10, 10, 90, 40], [10, 60, 90, 90]], street_nets(1400, 41, 59), core)
        r = H.run(d, mac_tpu=5.26, cut_step=4.0, bin_um=1.0, detour=0.0)
        self.assertTrue(r["bands_before"])
        self.assertGreater(r["bands_before"][0]["deficit"], 500)
        self.assertEqual(r["bands_after"], [])
        boxes = {m["macro"]: m for m in r["moves"]}
        for mv in r["moves"]:
            self.assertEqual(mv["from_ll"][0], mv["to_ll"][0])                       # X fixed
            self.assertAlmostEqual(mv["dy_um"] / 0.864, round(mv["dy_um"] / 0.864), places=6)  # origin grid
        gap = 0.0
        lo = 40.0 + boxes.get("u_bound.m0", {"dy_um": 0.0})["dy_um"]
        hi = 60.0 + boxes.get("u_bound.m1", {"dy_um": 0.0})["dy_um"]
        gap = hi - lo
        self.assertGreaterEqual(gap * H.tracks_per_um(H.H_LAYERS) + 1e-6, 1400 - 1.0)
        for mv in r["moves"]:
            self.assertGreaterEqual(mv["to_ll"][1], core[1])

    def test_no_headroom_is_refused_plainly(self):
        core = (0.0, 0.0, 100.0, 92.0)
        d = dump([[10, 2, 90, 40], [10, 60, 90, 90]], street_nets(1400, 41, 59), core)
        r = H.run(d, mac_tpu=5.26, cut_step=4.0, bin_um=1.0, detour=0.0)
        self.assertTrue(any("refused" in c for c in r["channels"]))
        self.assertTrue(r["bands_after"])
        for mv in r["moves"]:
            self.assertGreaterEqual(mv["to_ll"][1], core[1] - 1e-6)

    def test_core_core_nets_inside_macro_run_not_fixable(self):
        # pins of two abutting macros at the same y, both inside the run: the window is inside the macros
        core = (0.0, 0.0, 100.0, 200.0)
        nets = [[None, None, None, None, 0, [[0, 20.0, 50.0 + k * 0.01], [1, 80.0, 50.0 + k * 0.01]]] for k in range(400)]
        d = dump([[5, 30, 50, 70], [50, 30, 95, 70]], nets, core)
        r = H.run(d, mac_tpu=5.26, cut_step=4.0, bin_um=1.0, detour=0.0)
        self.assertTrue(r["bands_before"])
        self.assertEqual(r["bands_before"][0]["core_core_nets"], 400)
        self.assertEqual(r["moves"], [])
        self.assertTrue(all("refused" in c for c in r["channels"]))

    def test_abutting_halves_move_rigidly(self):
        core = (0.0, 0.0, 100.0, 200.0)
        d = dump([[10, 10, 50, 40], [50, 10, 90, 40], [10, 60, 50, 90], [50, 60, 90, 90]], street_nets(1400, 41, 59), core)
        r = H.run(d, mac_tpu=5.26, cut_step=4.0, bin_um=1.0, detour=0.0)
        dy = {m["macro"]: m["dy_um"] for m in r["moves"]}
        self.assertTrue(dy)
        self.assertEqual(dy.get("u_bound.m0", 0.0), dy.get("u_bound.m1", 0.0))
        self.assertEqual(dy.get("u_bound.m2", 0.0), dy.get("u_bound.m3", 0.0))

    def test_env_accepted_by_gen_phys(self):
        core = (0.0, 0.0, 100.0, 200.0)
        d = dump([[10.108, 10.012, 90.108, 40.012], [10.108, 60.012, 90.108, 90.012]], street_nets(1400, 41, 59), core)
        ptype = {"outline_um": [100.0, 200.0], "hard_cores": [
            {"inst": "u.a", "module": "mm", "origin_um": [10.0, 10.0], "outline_um": [80.0, 30.0], "orient": "R0",
             "track_offset_um": [0.108, 0.012]},
            {"inst": "u.b", "module": "mm", "origin_um": [10.0, 60.0], "outline_um": [80.0, 30.0], "orient": "R0",
             "track_offset_um": [0.108, 0.012]}]}
        r = H.run(d, ptype, mac_tpu=5.26, cut_step=4.0, bin_um=1.0, detour=0.0)
        self.assertTrue(r["OT_MACRO_MOVES"])
        self.assertEqual(r["unmapped"], [])
        t = G.macro_move_table(ptype, "t", {"OT_MACRO_MOVES": r["OT_MACRO_MOVES"]})
        for mv in r["moves"]:
            self.assertAlmostEqual(t[mv["plan_inst"]]["y"], mv["to_ll"][1], places=4)


if __name__ == "__main__":
    unittest.main()
