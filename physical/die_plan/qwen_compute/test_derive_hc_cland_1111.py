"""Tests for derive_hc_cland_1111 (DIE-QC-97 HC-CLAND: re-runnable hc1/hc2 face-home + strip-rows derivation)."""
import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import derive_hc_cland_1111 as D  # noqa: E402
import gen_phys as GP  # noqa: E402

OFF = ["sle_hc1__cl7d360508", "slw_hc1__cl3449ea95"]
HOME_T = ["sle_hc1__cl22c1ff36", "sle_hc2__clcc5e3e61", "slw_hc2__cl6bcaba89"]
OTHER = ["slw_hc3__clccfc3e6b", "sle_fw_v2__cl69f5e854", "sle_hc1x_v1"]
HOME = [17.28, 17.28, 289.248, 62.64]
RS_N1_NEW = [17.28, 64.8, 69.12, 153.888]


def band(rect, width, **kw):
    return dict({"rect_um": list(rect), "width": width, "max_pin_to_band_hop_um": 0.0, "placement": "PROPOSED",
                 "instance": "u_cland_x"}, **kw)


def htype(tn, home):
    bands = ({"b_hw_i": band(HOME, 1573), "rs_n0": band([17.28, 94.368, 69.12, 183.36], 514),
              "rs_n1": band([71.28, 64.8, 123.12, 153.888], 514)} if home else
             {"b_hw_i": band([108.528, 17.28, 380.496, 62.64], 1573), "rs_n0": band([95.04, 94.368, 146.88, 183.36], 514),
              "rs_n1": band([17.28, 17.28, 69.12, 106.368], 514)})
    bands["x_hc0_ctl_i"] = band([146.88, 180.84, 231.12, 189.48] if not home else [69.12, 180.84, 153.36, 189.48], 9)
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
    T.update({tn: htype(tn, True) for tn in HOME_T})
    T.update({tn: {"module": tn, "outline_um": [613.44, 1339.2]} for tn in OTHER})
    p = {"schema": "s", "partition_types": T, "budgets": {"face_pins_per_um": 4.2},
         "partitions": [{"name": "p_" + t, "type": t, "origin_um": [0, 0]} for t in T]}
    if strip is not None:
        p["budgets"]["cland_strip_rows_types"] = strip
    return p


def bands(p, tn):
    return p["partition_types"][tn]["clock"]["landing_contract"]["bands"]


class Derive(unittest.TestCase):
    def test_reproduces_hc1_strip_and_touches_nothing_else(self):
        base = plan({"sle_st_a_v2": 2})
        out, moved = D.apply(copy.deepcopy(base))
        self.assertEqual(sorted(moved), sorted(OFF))
        for tn in OFF:
            self.assertEqual(sorted(moved[tn]), ["b_hw_i", "rs_n1"])
            self.assertEqual(bands(out, tn)["b_hw_i"]["rect_um"], HOME)
            self.assertEqual(bands(out, tn)["rs_n1"]["rect_um"], RS_N1_NEW)
            self.assertEqual(bands(out, tn)["rs_n1"]["resized_from_um"], [17.28, 17.28, 69.12, 106.368])
            self.assertAlmostEqual(bands(out, tn)["b_hw_i"]["max_pin_to_band_hop_um"], 211.584)
            self.assertAlmostEqual(bands(out, tn)["rs_n1"]["max_pin_to_band_hop_um"], 174.144)
        self.assertEqual(out["budgets"]["cland_strip_rows_types"],
                         {"sle_st_a_v2": 2, "sle_hc1": 3, "slw_hc1": 3, "sle_hc2": 3, "slw_hc2": 3})
        b2 = copy.deepcopy(base)
        b2["budgets"]["cland_strip_rows_types"] = out["budgets"]["cland_strip_rows_types"]
        for tn in OFF:
            for k in ("b_hw_i", "rs_n1"):
                bands(b2, tn)[k] = bands(out, tn)[k]
        self.assertEqual(json.dumps(out, sort_keys=True), json.dumps(b2, sort_keys=True))

    def test_idempotent(self):
        once, _ = D.apply(plan())
        twice, moved = D.apply(copy.deepcopy(once))
        self.assertEqual(moved, {})
        self.assertEqual(json.dumps(once, sort_keys=True), json.dumps(twice, sort_keys=True))

    def test_kit_rows(self):
        out, _ = D.apply(plan())
        for t in OFF + HOME_T:
            self.assertEqual(GP._cland_strip_rows(out["budgets"], t), 3, t)
        for t in OTHER:
            self.assertEqual(GP._cland_strip_rows(out["budgets"], t), GP._cland_strip_rows(plan()["budgets"], t), t)

    def test_follows_geometry_after_a_move(self):
        # a fixed (hard) band where HOME was: the derivation finds the next legal home instead of the old constant
        p = plan()
        bands(p, OFF[0])["hard_x"] = band([17.28, 17.28, 40.0, 30.0], 8, hard_core=True)
        out, moved = D.apply(p)
        r = bands(out, OFF[0])["b_hw_i"]["rect_um"]
        self.assertNotEqual(r, HOME)
        self.assertFalse(D._ov(r, [17.28, 17.28, 40.0, 30.0]))
        self.assertAlmostEqual(r[2] - r[0], HOME[2] - HOME[0], places=6)

    def test_refuses_without_legal_home(self):
        p = plan()
        bands(p, OFF[1])["hard_x"] = band([17.28, 17.28, 596.16, 1321.92], 8, hard_core=True)
        with self.assertRaises(SystemExit):
            D.apply(p)

    def test_refuses_conflicting_rows(self):
        with self.assertRaises(SystemExit):
            D.apply(plan({"sle_hc2": 2}))

    def test_keeps_matching_rows(self):
        out, _ = D.apply(plan({"sle_hc2": 3}))
        self.assertEqual(out["budgets"]["cland_strip_rows_types"]["sle_hc2"], 3)


if __name__ == "__main__":
    unittest.main()
