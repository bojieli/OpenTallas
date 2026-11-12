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
        out, moved, _ = D.apply(copy.deepcopy(base))
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
        once, _, _ = D.apply(plan())
        twice, moved, _ = D.apply(copy.deepcopy(once))
        self.assertEqual(moved, {})
        self.assertEqual(json.dumps(once, sort_keys=True), json.dumps(twice, sort_keys=True))

    def test_kit_rows(self):
        out, _, _ = D.apply(plan())
        for t in OFF + HOME_T:
            self.assertEqual(GP._cland_strip_rows(out["budgets"], t), 3, t)
        for t in OTHER:
            self.assertEqual(GP._cland_strip_rows(out["budgets"], t), GP._cland_strip_rows(plan()["budgets"], t), t)

    def test_follows_geometry_after_a_move(self):
        # a fixed (hard) band where HOME was: the derivation finds the next legal home instead of the old constant
        p = plan()
        bands(p, OFF[0])["hard_x"] = band([17.28, 17.28, 40.0, 30.0], 8, hard_core=True)
        out, moved, _ = D.apply(p)
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
        out, _, _ = D.apply(plan({"sle_hc2": 3}))
        self.assertEqual(out["budgets"]["cland_strip_rows_types"]["sle_hc2"], 3)


def widen_plan():
    """hc1 over a ctl partner (ctl N face = hc1 S face), as in QC slice rows 0/1"""
    p = plan()
    hc = p["partition_types"][OFF[0]]
    hc["buses"] += [{"name": "cw_s1", "face": "S", "window_um": [277.248, 366.528], "width": 516, "dir": "out"},
                    {"name": "x_st_b_o", "face": "S", "window_um": [373.776, 463.104], "width": 516, "dir": "out"}]
    hc["clock"]["landing_contract"]["pins"] = [{"name": "fclk_in_b_hw_i", "layer": "M7", "xy_um": [140.192, 2.656]},
                                              {"name": "fclk_out_cw_s1", "layer": "M7", "xy_um": [322.08, 2.656]}]
    hc["clock"]["landing_contract"]["collector_local_sources"] = [
        {"name": "b_hw_i", "tap": 2, "xy_um": [140.304, 0], "pin_xy_um": [140.304, 0]}]
    p["partition_types"]["ctl_t"] = {"module": "ctl_t", "outline_um": [1226.88, 1339.2], "buses": [
        {"name": "b_hw_hc1_o", "face": "N", "window_um": [4.32, 276.288], "width": 1573, "dir": "out"},
        {"name": "cws1_i", "face": "N", "window_um": [277.248, 366.528], "width": 516, "dir": "in"},
        {"name": "x_st_b_i", "face": "N", "window_um": [373.776, 463.104], "width": 516, "dir": "in"}],
        "clock": {"landing_contract": {"bands": {}, "pins": [
            {"name": "fclk_out_b_hw_hc1_o", "layer": "M7", "xy_um": [140.192, 1336.544]}]}}}
    for q in p["partitions"]:
        q["origin_um"] = [0, 1339.2] if q["type"] == OFF[0] else [5000, 5000]
    p["partitions"].append({"name": "p_ctl", "type": "ctl_t", "origin_um": [0, 0]})
    p["die"] = {"name": "t", "outline_um": [10000.0, 10000.0], "reach_um": 405}
    p["lanes"] = []
    for t in (hc, p["partition_types"]["ctl_t"]):
        for bb in t["buses"]:
            bb.setdefault("layers", ["M7", "M5"])
    p["ports"] = [{"id": "a", "src": {"part": "p_ctl", "bus": "b_hw_hc1_o"}, "dst": {"part": "p_" + OFF[0], "bus": "b_hw_i"},
                   "width": 1573, "kind": "data"},
                  {"id": "b", "src": {"part": "p_" + OFF[0], "bus": "cw_s1"}, "dst": {"part": "p_ctl", "bus": "cws1_i"},
                   "width": 516, "kind": "data"},
                  {"id": "c", "src": {"part": "p_" + OFF[0], "bus": "x_st_b_o"}, "dst": {"part": "p_ctl", "bus": "x_st_b_i"},
                   "width": 516, "kind": "data"}]
    return p


class Widen(unittest.TestCase):
    def test_widen_both_seam_sides(self):
        out, moved, rep = D.apply(widen_plan(), widen_face=True)
        hc = {b["name"]: b["window_um"] for b in out["partition_types"][OFF[0]]["buses"]}
        ctl = {b["name"]: b["window_um"] for b in out["partition_types"]["ctl_t"]["buses"]}
        d = 596.16 - 463.104
        d = int(d / D.WG + 1e-6) * D.WG
        self.assertAlmostEqual(hc["b_hw_i"][1], round(276.288 + d, 6))
        self.assertAlmostEqual(hc["cw_s1"][0], round(277.248 + d, 6))
        self.assertLessEqual(hc["x_st_b_o"][1], 596.16 + 1e-6)
        self.assertEqual(ctl["b_hw_hc1_o"], hc["b_hw_i"])
        self.assertEqual(ctl["cws1_i"], hc["cw_s1"])
        self.assertEqual(ctl["x_st_b_i"], hc["x_st_b_o"])
        lc = out["partition_types"][OFF[0]]["clock"]["landing_contract"]
        self.assertAlmostEqual(lc["collector_local_sources"][0]["xy_um"][0], (4.32 + hc["b_hw_i"][1]) / 2)
        pin = {q["name"]: q["xy_um"] for q in lc["pins"]}
        self.assertAlmostEqual((pin["fclk_in_b_hw_i"][0] - 140.192) / D.WG, round((pin["fclk_in_b_hw_i"][0] - 140.192) / D.WG))
        cpin = out["partition_types"]["ctl_t"]["clock"]["landing_contract"]["pins"][0]["xy_um"][0]
        self.assertAlmostEqual(cpin, pin["fclk_in_b_hw_i"][0])
        b = bands(out, OFF[0])["b_hw_i"]["rect_um"]
        self.assertGreater(b[2] - b[0], 289.248 - 17.28)       # the band follows the wider window
        again, moved2, rep2 = D.apply(copy.deepcopy(out), widen_face=True)
        self.assertEqual(rep2["windows"], {})
        self.assertEqual(json.dumps(out, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_widen_keep_band(self):
        """HC1 MEASURED winner: widened windows, the kit band stays where it is once it is home, rows 4"""
        p = widen_plan()
        old = copy.deepcopy(bands(p, OFF[0]))
        out, moved, rep = D.apply(p, rows=4, bases=("sle_hc1", "slw_hc1"), widen_face=True, keep_band=True)
        self.assertIn(f"{OFF[0]}.b_hw_i", rep["windows"])
        self.assertNotIn(OFF[0], moved)
        self.assertEqual(bands(out, OFF[0]), old)
        self.assertEqual(out["budgets"]["cland_strip_rows_types"]["sle_hc1"], 4)
        again, moved2, _ = D.apply(copy.deepcopy(out), rows=4, bases=("sle_hc1", "slw_hc1"), widen_face=True,
                                   keep_band=True)
        self.assertEqual(moved2, {})
        self.assertEqual(json.dumps(out, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_widen_refuses_disagreeing_partner(self):
        p = widen_plan()
        p["partition_types"]["ctl_t"]["buses"][0]["window_um"] = [8.64, 280.608]
        with self.assertRaises(SystemExit):
            D.apply(p, widen_face=True)


class Exclude(unittest.TestCase):
    def test_fw_v1_never_touched(self):
        p = plan()
        p["partition_types"]["slw_fw_v1__cl51d45468"] = htype("slw_fw_v1__cl51d45468", False)
        before = json.dumps(p["partition_types"]["slw_fw_v1__cl51d45468"], sort_keys=True)
        out, moved, _ = D.apply(p, bases=D.BASES + ("slw_fw_v1x",))
        self.assertNotIn("slw_fw_v1__cl51d45468", moved)
        self.assertEqual(json.dumps(out["partition_types"]["slw_fw_v1__cl51d45468"], sort_keys=True), before)
        self.assertNotIn("slw_fw_v1", out["budgets"]["cland_strip_rows_types"])

    def test_refuses_fw_v1_base(self):
        with self.assertRaises(SystemExit):
            D.apply(plan(), bases=("sle_hc1", "slw_fw_v1"))


if __name__ == "__main__":
    unittest.main()
