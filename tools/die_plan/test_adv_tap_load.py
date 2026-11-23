"""pytest: ADV-TAP-LOAD on a fixture modeled on the real positive (COORD 11-22 18:1x TAP-SOFTFLOP, FAM-S81-MISC-R4:
S81 ot_s81sl_kv_leaf__t5 on J8 = 16 R4 grid taps + 22 added taps, planned max tap load 1,099 (5,673 planned sinks),
57,695 netlist flops, placed registers ~8,000 on one tap)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tap_load as A  # noqa: E402

T5 = "ot_s81sl_kv_leaf__t5"
W, H = 1442.88, 1226.88


def plan():
    added = [{"name": f"clk_t{16 + i}", "xy": [90.0 + 60.0 * i, 100.0 + 45.0 * i]} for i in range(22)]
    return {"die": {"name": "s81"}, "budgets": {},
            "partition_types": {T5: {"outline_um": [W, H], "hard": False,
                                     "clock": {"tap_mode": "grid+explicit", "tap_max_sinks": 1500, "tap_um": [725.76, 613.44],
                                               "added_taps": added}}},
            "partitions": [{"name": "l_t5", "type": T5}]}


def taps():
    return A.cheap_taps(plan(), plan()["partition_types"][T5])


def planned():
    tp = {n: (x, y) for n, x, y in taps()}
    pts = [(tp["clk_t35"][0], tp["clk_t35"][1], 1099.0)]            # the planned max tap (1,099)
    rest = [n for n in tp if n != "clk_t35"]
    left = 5673 - 1099
    for i, n in enumerate(rest):
        pts.append((tp[n][0], tp[n][1], float(left // len(rest) + (1 if i < left % len(rest) else 0))))
    return {T5: pts}


def cache(flops=57695, hot=8323):
    tp = {n: (x, y) for n, x, y in taps()}
    x, y = tp["clk_t24"]
    bins = [[x, y, hot]] + [[tp[n][0], tp[n][1], 1300] for n in tp if n != "clk_t24"]
    return {"made": "fixture",
            "flops": {T5: {"flops": flops, "ts": 1795235359, "kit": "epyc8:ot_s81sl_kv_leaf__t5-route-x-1795235359"}},
            "placed_bins": {T5: {"die_um": [W, H], "bin_um": 10.0, "n_regs": hot + 1300 * 37, "ts": 1795235359,
                                 "kit": "epyc8:ot_s81sl_kv_leaf__t5-route-x-1795235359", "bins": bins}}}


def line(out):
    h = [ln for ln in out if ln.startswith(f"WARN ADV-TAP-LOAD {T5}:")]
    return h[0] if h else None


def test_taps_are_the_j8_38():
    assert len(taps()) == 38 and taps()[0][0] == "clk" and taps()[15][0] == "clk_t15"


def test_real_positive_t5_flagged():
    out = A.findings(plan(), "j8.json", None, flops_cache=cache(), planned_sinks=planned(), exact=False)
    ln = line(out)
    assert ln, out
    assert "1,518 netlist flops/tap" in ln and "planned max 1,099 (clk_t35)" in ln and "x1.38 > 1.3" in ln
    assert "clk_t24 8,323" in ln and "over 1500" in ln
    assert "plan sink model 5,673 vs 57,695" in ln
    assert out[-1].startswith("WARN ADV-TAP-LOAD summary: 1 of 1")


def test_fixed_taps_not_flagged():
    # netlist load per tap within 1.3 x the planned max and the placed registers spread under 1,500 per tap
    out = A.findings(plan(), "j8.json", None, flops_cache=cache(flops=40000, hot=1300), planned_sinks=planned(), exact=False)
    assert line(out) is None, out
    assert "0 of 1" in out[-1] and "total-sink rule" in out[-1]      # boundary model only counted, not listed


def test_inventory_rule_on_sink_bins_types():
    p = plan()
    ck = p["partition_types"][T5]["clock"]
    ck["tap_mode"], ck["sink_bins_file"] = "density", "sink_bins/t5.json"
    out = A.findings(p, "j8.json", None, flops_cache=cache(), planned_sinks=planned(), exact=False)
    assert line(out) and "sink bins 5,673 planned vs 57,695" in line(out)


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-TAP-LOAD not checked")
    out = A.findings(plan(), "p", None, flops_cache={"flops": {}}, exact=False)
    assert out[-1].startswith("WARN ADV-TAP-LOAD summary")
