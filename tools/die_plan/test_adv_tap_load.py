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


def test_no_taps_no_crash_and_loud():
    """COORD 11-23 19:45: a sink_bins_file type with no static taps and no usable tree crashed with ZeroDivisionError;
    now it reports a plain 'not checked' line."""
    pl = plan()
    pl["partition_types"][T5]["clock"] = {"sink_bins_file": "x.json", "tap_max_sinks": 1500}
    out = A.findings(pl, "p", "/nonexistent-tree", flops_cache={"flops": {T5: {"flops": 5000}}})
    assert out and not any("ZeroDivision" in x for x in out)
    assert out[-1].startswith("WARN ADV-TAP-LOAD summary")


def test_no_bins_is_unmeasured_not_pass():
    c = cache()
    c["placed_bins"] = {}
    out = A.findings(plan(), "j8.json", None, flops_cache=c, planned_sinks=planned(), exact=False)
    um = [ln for ln in out if "ADV-TAP-LOAD UNMEASURED" in ln]
    assert um and T5 in um[0], out
    assert "1 UNMEASURED" in out[-1], out[-1]


def test_with_bins_is_measured():
    out = A.findings(plan(), "j8.json", None, flops_cache=cache(), planned_sinks=planned(), exact=False)
    assert not [ln for ln in out if "ADV-TAP-LOAD UNMEASURED" in ln], out
    assert "0 UNMEASURED" in out[-1]


# ---- C-TAP-LOAD 11-27: density types are judged tap by tap against the per-type kit cap; no bins = NOT-CHECKED ----
import json  # noqa: E402
import types  # noqa: E402

DT = "qc_dens"


def dplan(cap=1000, bins_file="bins.json"):
    ck = {"tap_mode": "density", "tap_max_sinks": cap}
    if bins_file:
        ck["sink_bins_file"] = bins_file
    return {"die": {"name": "qc"}, "budgets": {},
            "partition_types": {DT: {"outline_um": [400.0, 400.0], "hard": False, "clock": ck}},
            "partitions": [{"name": "p", "type": DT}]}


def dex(sites):
    return types.SimpleNamespace(ok=True, why="", taps_of=lambda tn: sites)


SITES = [("clk", 100.0, 100.0), ("clk_t1", 300.0, 300.0)]


def dline(out):
    h = [x for x in out if x.startswith(f"WARN ADV-TAP-LOAD {DT}:")]
    return h[0] if h else None


def test_kit_cap_is_the_gen_phys_rule(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    assert A.kit_cap({"clock": {"tap_max_sinks": 1000}}) == 1000
    assert A.kit_cap({"clock": {}}) == 3000 and A.kit_cap({"clock": {"tap_mode": "density"}}) == 1500
    assert A.kit_cap({"clock": {"tap_max_sinks": 3000, "tap_grid": {"bank_sinks": 800}}}) == 800
    monkeypatch.setenv("OT_TAP_MAX_SINKS", "1200")
    assert A.kit_cap({"clock": {"tap_max_sinks": 3000}}) == 1200


def test_density_each_tap_over_cap_is_flagged_even_when_total_is_fine(monkeypatch):
    """total 2,600 sinks on 2 taps (1,300/tap average) is under the 1.3 ratio of any plan model, but one tap holds 1,900 > 1000."""
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    bins = {DT: [(100.0, 100.0, 1900.0), (300.0, 300.0, 700.0)]}
    out = A.findings(dplan(), "p.json", None, flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES), density_bins=bins)
    ln = dline(out)
    assert ln and "1 of 2 taps over the kit cap 1000" in ln and "clk 1,900" in ln, out
    assert "density per-tap: 1 types judged tap by tap (1 over their kit cap), 0 NOT-CHECKED" in out[-1], out[-1]
    assert out[-1].startswith("WARN ADV-TAP-LOAD summary:")


def test_density_tap_under_cap_passes(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    bins = {DT: [(100.0, 100.0, 900.0), (300.0, 300.0, 700.0)]}
    out = A.findings(dplan(), "p.json", None, flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES), density_bins=bins)
    assert dline(out) is None and "1 types judged tap by tap (0 over" in out[-1]


def test_density_cap_is_per_type_not_constant(monkeypatch):
    monkeypatch.delenv("OT_TAP_MAX_SINKS", raising=False)
    bins = {DT: [(100.0, 100.0, 1900.0), (300.0, 300.0, 700.0)]}
    out = A.findings(dplan(cap=3000), "p.json", None, flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES), density_bins=bins)
    assert dline(out) is None            # same loads under a 3000-cap type


def test_density_without_bins_is_not_checked_not_pass():
    out = A.findings(dplan(bins_file=None), "p.json", None, flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES))
    nc = [x for x in out if "ADV-TAP-LOAD NOT-CHECKED" in x]
    assert nc and DT in nc[0] and "no clock.sink_bins_file" in nc[0], out
    assert "1 NOT-CHECKED" in out[-1]


def test_density_bins_file_read_and_missing_file(tmp_path):
    (tmp_path / "bins.json").write_text(json.dumps({"bins": [[100, 100, 1900], [300, 300, 700]]}))
    plan = tmp_path / "plan.json"
    out = A.findings(dplan(), str(plan), str(tmp_path), flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES))
    assert dline(out) and "taps over the kit cap 1000" in dline(out), out
    out = A.findings(dplan(bins_file="gone.json"), str(plan), str(tmp_path), flops_cache={"flops": {}}, exact=False, density_ex=dex(SITES))
    assert any("not found" in x and "NOT-CHECKED" in x for x in out), out


def test_density_taps_unsolvable_is_not_checked():
    bins = {DT: [(100.0, 100.0, 1900.0)]}
    out = A.findings(dplan(), "p.json", None, flops_cache={"flops": {}}, exact=False,
                     density_ex=types.SimpleNamespace(ok=False, why="no taps.py"), density_bins=bins)
    assert any("NOT-CHECKED" in x and "no taps.py" in x for x in out), out
