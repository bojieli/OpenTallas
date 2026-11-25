"""FP-CONVERGE-S81 11-25: FAIL INOUTLINE is blocking in plan_gate_pre (pass plan, mutants per category, baseline delta via PRE-DIFF)."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402
import pre_diff as PD  # noqa: E402


def good_type():
    return {"outline_um": [100.0, 100.0], "bit_site_cell_um": [2.0, 1.0],
            "internal_stations": [{"conn": "bus:a", "bits": 2, "from_um": [5, 5], "regs_um": [[20, 20], [60, 60]], "to_um": [90, 90],
                                   "bit_sites_um": [[[20, 20], [22, 20]], [[60, 60], [62, 60]]]}],
            "ft_slots": [{"name": "ft0", "bit_site_cell_um": [2.0, 1.0], "regs_um": [[10, 10]], "bit_sites_um": [[[10, 10]]]}],
            "clock": {"landing_contract": {"collector_tree": {"root": [50, 50], "outs": [[10, 90]], "relays": [{"xy": [40, 40]}]},
                                           "collector_local_sources": [{"xy_um": [99, 50], "pin_xy_um": [100, 50]}],
                                           "pins": [{"xy_um": [0, 30]}]}}}


def run(tmp_path, types, name="p.json", block=True):
    f = tmp_path / name
    f.write_text(json.dumps({"die": "x", "partition_types": types}))
    return G.inoutline_findings(str(f), block=block)


def test_clean_plan_has_no_finding(tmp_path):
    assert run(tmp_path, {"ty": good_type()}) == []


def test_class_is_registered_and_fails():
    assert "INOUTLINE" in G.CLASSES


def test_station_reg_outside_is_a_fail(tmp_path):
    t = good_type()
    t["internal_stations"][0]["regs_um"][1] = [160, 60]
    out = run(tmp_path, {"ty": t})
    assert out[0].startswith("FAIL INOUTLINE ty:") and "station reg" in out[0] and "+60" in out[0]


def test_bit_site_footprint_not_only_centre(tmp_path):
    t = good_type()
    t["internal_stations"][0]["bit_sites_um"][0][0] = [99.0, 50.0]      # centre inside, 2 um cell crosses x=100 by 1 um
    assert run(tmp_path, {"ty": t}) == []                                # 1 um: inside the 1 um tolerance
    t["internal_stations"][0]["bit_sites_um"][0][0] = [97.0, 50.0]
    assert run(tmp_path, {"ty": t}) == []
    t["internal_stations"][0]["bit_sites_um"][0][0] = [101.0, 50.0]      # footprint 3 um over
    assert "station bit site" in run(tmp_path, {"ty": t})[0]


def test_ft_site_and_reg_outside(tmp_path):
    t = good_type()
    t["ft_slots"][0]["regs_um"] = [[10, 125]]
    t["ft_slots"][0]["bit_sites_um"] = [[[10, 130]]]
    assert "ft bit site" in run(tmp_path, {"ty": t})[0]


def test_landing_contract_points_outside(tmp_path):
    t = good_type()
    t["clock"]["landing_contract"]["collector_tree"]["root"] = [1611.84, 12.9]
    t["clock"]["landing_contract"]["collector_local_sources"][0]["pin_xy_um"] = [1620.0, 130.4]
    out = run(tmp_path, {"ty": t})[0]
    assert "collector root" in out and "landing collector_local_sources" in out


def test_pin_on_the_edge_is_fine(tmp_path):
    t = good_type()
    t["clock"]["landing_contract"]["pins"] = [{"xy_um": [100.0, 50.0]}, {"xy_um": [0.0, 0.0]}]
    assert run(tmp_path, {"ty": t}) == []


def test_baseline_delta_blocks_only_new_or_changed(tmp_path):
    bad = good_type()
    bad["internal_stations"][0]["regs_um"][1] = [160, 60]
    base = [x for x in run(tmp_path, {"a": bad, "b": good_type()}, "base.json") if x.startswith("FAIL")]
    assert len(base) == 1
    same = [x for x in run(tmp_path, {"a": copy.deepcopy(bad), "b": good_type()}, "row.json") if x.startswith("FAIL")]
    d = PD.diff(same, base)
    assert d["new"] == [] and d["changed"] == [] and len(d["inherited"]) == 1       # inherited, never a failure
    worse = copy.deepcopy(bad)
    worse["internal_stations"][0]["regs_um"][1] = [190, 60]
    d = PD.diff([x for x in run(tmp_path, {"a": worse, "b": good_type()}, "row2.json") if x.startswith("FAIL")], base)
    assert len(d["changed"]) == 1 and d["new"] == []                                # a worse overshoot blocks
    newb = copy.deepcopy(bad)
    d = PD.diff([x for x in run(tmp_path, {"a": bad, "b": newb}, "row3.json") if x.startswith("FAIL")], base)
    assert len(d["new"]) == 1                                                       # a new type blocks


def test_default_is_report_only_and_env_opts_in(tmp_path, monkeypatch):
    t = good_type()
    t["internal_stations"][0]["regs_um"][1] = [160, 60]
    monkeypatch.delenv("OT_PRE_INOUTLINE_BLOCK", raising=False)
    out = run(tmp_path, {"ty": t}, block=None)
    assert out[0].startswith("WARN INOUTLINE ty:") and not any(x.startswith("FAIL") for x in out)     # a live cut never blocks
    monkeypatch.setenv("OT_PRE_INOUTLINE_BLOCK", "1")
    assert run(tmp_path, {"ty": t}, block=None)[0].startswith("FAIL INOUTLINE ty:")                    # the c11 cut opts in
    monkeypatch.setenv("OT_PRE_INOUTLINE_BLOCK", "0")
    assert run(tmp_path, {"ty": t}, block=None)[0].startswith("WARN INOUTLINE")
