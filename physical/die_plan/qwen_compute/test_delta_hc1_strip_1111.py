"""Tests for delta_hc1_strip_1111 (DIE-QC-97 HC1-STRIP: hc1 b_hw_i back over its pins, rs_n1 north, strip rows 3)."""
import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import delta_hc1_strip_1111 as D  # noqa: E402
import gen_phys as GP  # noqa: E402

OFF = ["sle_hc1__cl7d360508", "slw_hc1__cl3449ea95", "slw_hc1__cl68f9248e__cl144ee7b3",
       "slw_hc1__cl68f9248e__cle683a076"]
HOME_T = "sle_hc1__cl22c1ff36"
OTHER = ["sle_hc2__clcc5e3e61", "slw_hc3__clccfc3e6b", "sle_fw_v2__cl69f5e854", "sle_hc1x_v1", "xslw_hc1"]
RS_N1_NEW = [17.28, 64.8, 69.12, 153.888]


def band(rect, width):
    return {"rect_um": list(rect), "width": width, "ring_width": 64 * -(-(width + 1) // 64),
            "max_pin_to_band_hop_um": 0.0, "placement": "PROPOSED", "instance": "u_cland_x"}


def htype(tn, home):
    bands = ({"b_hw_i": band(D.HOME, 1573), "rs_n0": band([17.28, 94.368, 69.12, 183.36], 514),
              "rs_n1": band([71.28, 64.8, 123.12, 153.888], 514),
              "x_hc0_ctl_i": band([69.12, 180.84, 153.36, 189.48], 9)} if home else
             {"b_hw_i": band([108.528, 17.28, 380.496, 62.64], 1573), "rs_n0": band([95.04, 94.368, 146.88, 183.36], 514),
              "rs_n1": band([17.28, 17.28, 69.12, 106.368], 514),
              "x_hc0_ctl_i": band([146.88, 180.84, 231.12, 189.48], 9)})
    return {"module": tn, "outline_um": [613.44, 1339.2],
            "buses": [{"name": "b_hw_i", "face": "S", "window_um": [4.32, 276.288], "width": 1573},
                      {"name": "rs_n0", "face": "W", "window_um": [94.368, 183.36], "width": 514},
                      {"name": "rs_n1", "face": "W", "window_um": [4.32, 93.408], "width": 514}],
            "clock": {"landing_contract": {"base_type": tn.split("__")[0], "bands": bands,
                                           "collector_tree": {"root": [140.0, 0.0], "relays": [
                                               {"name": "u_rrl_0", "xy": [156.576, 17.312], "q": "rst_rl_0",
                                                "d": "rst_root_n", "depth": 1, "tap": 1, "kind": "pad"}]}}}}


def plan(strip=None):
    T = {tn: htype(tn, False) for tn in OFF}
    T[HOME_T] = htype(HOME_T, True)
    T.update({tn: {"module": tn, "outline_um": [613.44, 1339.2]} for tn in OTHER})
    p = {"schema": "s", "partition_types": T, "budgets": {"face_pins_per_um": 4.2},
         "partitions": [{"name": "p_" + t, "type": t, "origin_um": [0, 0]} for t in T]}
    if strip is not None:
        p["budgets"]["cland_strip_rows_types"] = strip
    return p


class HC1Strip(unittest.TestCase):
    def test_moves_only_the_two_bands_of_the_off_types(self):
        base = plan({"sle_st_a_v2": 2})
        out, types, moved = D.apply(copy.deepcopy(base))
        self.assertEqual(types, sorted(OFF + [HOME_T]))
        self.assertEqual(sorted(moved), sorted(OFF))
        self.assertEqual(out["budgets"]["cland_strip_rows_types"], {"sle_st_a_v2": 2, "sle_hc1": 3, "slw_hc1": 3})
        for tn in OFF:
            b = out["partition_types"][tn]["clock"]["landing_contract"]["bands"]
            ob = base["partition_types"][tn]["clock"]["landing_contract"]["bands"]
            self.assertEqual(b["b_hw_i"]["rect_um"], D.HOME)
            self.assertEqual(b["rs_n1"]["rect_um"], RS_N1_NEW)
            self.assertEqual(b["b_hw_i"]["resized_from_um"], ob["b_hw_i"]["rect_um"])
            self.assertEqual(b["rs_n1"]["resized_from_um"], ob["rs_n1"]["rect_um"])
            self.assertAlmostEqual(b["b_hw_i"]["max_pin_to_band_hop_um"], 211.584)
            self.assertAlmostEqual(b["rs_n1"]["max_pin_to_band_hop_um"], 174.144)
        # full tree diff: nothing else changes
        b2 = copy.deepcopy(base)
        b2["budgets"]["cland_strip_rows_types"] = out["budgets"]["cland_strip_rows_types"]
        for tn in OFF:
            for k in ("b_hw_i", "rs_n1"):
                b2["partition_types"][tn]["clock"]["landing_contract"]["bands"][k] = \
                    out["partition_types"][tn]["clock"]["landing_contract"]["bands"][k]
        self.assertEqual(json.dumps(out, sort_keys=True), json.dumps(b2, sort_keys=True))

    def test_kit_rows_only_hc1(self):
        out, _, _ = D.apply(plan({"sle_st_a_v2": 2}))
        bud = out["budgets"]
        for t in OFF + [HOME_T]:
            self.assertEqual(GP._cland_strip_rows(bud, t), 3, t)
        before = plan({"sle_st_a_v2": 2})["budgets"]
        for t in OTHER:
            self.assertEqual(GP._cland_strip_rows(bud, t), GP._cland_strip_rows(before, t), t)

    def test_refuses_reapply(self):
        out, _, _ = D.apply(plan())
        with self.assertRaises(SystemExit):
            D.apply(out)

    def test_refuses_existing_exact_type_key(self):
        with self.assertRaises(SystemExit):
            D.apply(plan({"slw_hc1__cl3449ea95": 1}))

    def test_refuses_obstacle_at_new_rs_n1(self):
        p = plan()
        p["partition_types"][OFF[0]]["clock"]["landing_contract"]["bands"]["x_blk"] = band([20.0, 120.0, 40.0, 130.0], 8)
        with self.assertRaises(SystemExit):
            D.apply(p)

    def test_refuses_third_band_over_home(self):
        p = plan()
        p["partition_types"][OFF[1]]["clock"]["landing_contract"]["bands"]["x_blk"] = band([200.0, 30.0, 220.0, 40.0], 8)
        with self.assertRaises(SystemExit):
            D.apply(p)

    def test_reset_relay_sites_are_not_obstacles(self):
        # u_rrl_0 sits inside both the old and the new b_hw_i rect (as in the plan); compose ignores relay sites
        out, _, moved = D.apply(plan())
        self.assertIn(OFF[0], moved)

    def test_refuses_plan_without_hc1(self):
        p = plan()
        for t in OFF + [HOME_T]:
            if t.startswith("slw_"):
                del p["partition_types"][t]
        with self.assertRaises(SystemExit):
            D.apply(p)


if __name__ == "__main__":
    unittest.main()
