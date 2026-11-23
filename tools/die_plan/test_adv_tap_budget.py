"""pytest for adv_tap_budget (PRECHECK-R2 TAP-BUDGET).  Self-contained: inline fixtures copied from S81 J8 c67f4f6ba285."""
import copy
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("adv_tap_budget", os.path.join(HERE, "adv_tap_budget.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

# S81 J8 dsdv_slice_c1x_C__t7: explicit edge-only tap table, the bus:leafup_i0 internal station chain runs down the middle
C1X_TAPS = [("clk", [761.184, 1209.632]), ("clk_t1", [17.76, 17.312]), ("clk_t2", [146.4, 17.312]),
            ("clk_t3", [287.008, 17.312]), ("clk_t4", [439.968, 17.312]), ("clk_t5", [598.368, 17.312]),
            ("clk_t6", [1426.08, 63.2]), ("clk_t7", [17.76, 162.528]), ("clk_t8", [1426.08, 179.936]),
            ("clk_t9", [17.76, 299.68]), ("clk_t10", [1426.08, 302.624]), ("clk_t11", [1426.08, 426.016]),
            ("clk_t12", [17.76, 426.272]), ("clk_t13", [87.2, 1209.632]), ("clk_t14", [252.32, 1209.632]),
            ("clk_t15", [337.504, 1209.632]), ("clk_t16", [422.432, 1209.632]), ("clk_t17", [508.128, 1209.632]),
            ("clk_t18", [593.76, 1209.632]), ("clk_t19", [928.288, 1209.632]), ("clk_t20", [1089.12, 1209.632]),
            ("clk_t21", [1234.656, 1209.632]), ("clk_t22", [1365.984, 1209.632]), ("clk_t23", [752.16, 90.72]),
            ("clk_t24", [1425.12, 1087.136]), ("clk_t25", [193.376, 1147.488]), ("clk_t26", [1349.984, 113.248]),
            ("clk_t27", [1354.336, 261.856]), ("clk_t28", [1393.184, 509.856]), ("clk_t29", [650.976, 95.072]),
            ("clk_t30", [699.232, 12.96]), ("clk_t31", [1354.336, 12.96])]


def plan_c1x():
    t = {"outline_um": [1442.88, 1226.88], "hard": False,
         "clock": {"tap_mode": "explicit", "tap_max_sinks": 1500,
                   "taps": [{"kind": "core", "name": "u_c.clk", "xy": [700.0, 700.0]}]
                   + [{"name": n, "xy": xy} for n, xy in C1X_TAPS]},
         "buses": [{"name": "leafup_i0", "dir": "in", "face": "N", "width": 1, "window_um": [78.0, 79.4]}],
         "internal_stations": [{"conn": "bus:leafup_i0", "regs_um": [[343.969, 1226.88], [478.172, 1095.816],
                                [464.572, 830.548], [478.172, 565.281], [478.172, 300.014]],
                                "from_um": [78.702, 1226.88], "to_um": [478.172, 69.307]}]}
    return {"clock": {"insertion_ps": 250}, "budgets": {"tap_pitch_um": 400},
            "partition_types": {"dsdv_slice_c1x_C__t7": t}, "partitions": [{"name": "p0", "type": "dsdv_slice_c1x_C__t7"}]}


# S81 J7 ot_s81sl_kv_leaf__t5 (FAM-S81-MISC-R4 17:53: pin-register mean 538 ps vs 450): grid+explicit, ft0 with its
# four real stations; every planned pin register is <= ~170 um from a tap, so only the balance-floor summary applies.
def plan_t5():
    t = {"outline_um": [1442.88, 1226.88], "hard": False,
         "clock": {"tap_mode": "grid+explicit", "insertion_ps": 450, "tap_max_sinks": 1500,
                   "insertion_target_override": {"reason": "FABLE-PD-S81-2250 verdict (a)"},
                   "added_taps": [{"name": "clk_t16", "xy": [300.384, 17.28]}, {"name": "clk_t17", "xy": [1081.344, 1209.6]}]},
         "buses": [{"name": "leafdn_i0", "dir": "in", "face": "S", "width": 597, "window_um": [395.52, 522.588]},
                   {"name": "leafup_o0", "dir": "out", "face": "S", "width": 668, "window_um": [249.024, 394.14]}],
         "ft_slots": [{"name": "ft0", "in_face": "N", "in_window_um": [65.28, 125.348], "out_face": "S",
                       "out_window_um": [65.28, 125.348], "stations": 4, "width": 276,
                       "regs_um": [[95.31, 1225.88], [59.498, 858.6], [50.858, 573.48], [50.858, 287.86]]}]}
    return {"clock": {"insertion_ps": 250}, "budgets": {"tap_pitch_um": 400},
            "partition_types": {"ot_s81sl_kv_leaf__t5": t}, "partitions": [{"name": "p0", "type": "ot_s81sl_kv_leaf__t5"}]}


def _type_lines(out):
    return [x for x in out if x.startswith("WARN ADV-TAP-BUDGET ") and " summary:" not in x and "not checked" not in x]


def test_c1x_far_station_flagged():
    out = A.findings(plan_c1x(), "/nonexistent/plan.json", None)
    lines = _type_lines(out)
    assert len(lines) == 1, out
    ln = lines[0]
    assert "dsdv_slice_c1x_C__t7: tap clk_t4" in ln and "bus:leafup_i0" in ln and "> target 450 ps" in ln
    assert "reach 586 um" in ln


def test_c1x_with_interior_tap_clean():
    raw = plan_c1x()
    for i, y in enumerate((300.0, 600.0, 980.0)):     # interior taps on the station column (<= 173 um at 250 ps)
        raw["partition_types"]["dsdv_slice_c1x_C__t7"]["clock"]["taps"].append({"name": f"clk_t{32 + i}", "xy": [478.0, y]})
    out = A.findings(raw, "/nonexistent/plan.json", None)
    assert not _type_lines(out), out
    assert "0 of 1 types" in out[-1]


def test_t5_only_balance_floor():
    out = A.findings(plan_t5(), "/nonexistent/plan.json", None)
    assert not _type_lines(out), out
    s = out[-1]
    assert "balance floor" in s and "target + 41" in s and "t5 538" in s


def test_t5_far_tap_flagged():
    # the same t5 ft0 stations with the grid replaced by one far explicit tap: the distance class fires at 450
    raw = plan_t5()
    ck = raw["partition_types"]["ot_s81sl_kv_leaf__t5"]["clock"]
    ck.update(tap_mode="explicit", taps=[{"name": "clk", "xy": [1300.0, 600.0]}])
    ck.pop("added_taps")
    ln = _type_lines(A.findings(raw, "/nonexistent/plan.json", None))
    assert len(ln) == 1 and "ot_s81sl_kv_leaf__t5: tap clk" in ln[0] and "> target 450 ps" in ln[0]


def test_model_threshold():
    assert 460 < A.reach_limit(450.0) < 470
    assert A.est_arrival(0.0, 1000, 450.0) == 450.0 + A.FLOOR_OVER_PS
    assert A.est_natural(465.0, 1000) + A.SLOW_OVER_PS > 450.0 > A.est_natural(460.0, 1000) + A.SLOW_OVER_PS


def test_never_raises():
    out = A.findings({}, "x.json")
    assert out and out[0].startswith("WARN ADV-TAP-BUDGET not checked")
    bad = copy.deepcopy(plan_c1x())
    bad["partition_types"]["dsdv_slice_c1x_C__t7"]["internal_stations"][0]["regs_um"] = "junk"
    out = A.findings(bad, "x.json")
    assert out and all(x.startswith("WARN ADV-TAP-BUDGET") for x in out)
