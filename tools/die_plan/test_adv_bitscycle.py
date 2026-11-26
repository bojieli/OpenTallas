"""FP-CONVERGE-S81: adv_bitscycle (BITS-OVER-CYCLE, PIN-FACE-KVLEAF) + the launch gate: clean plans and a mutant each."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_bitscycle as B  # noqa: E402
import launch_gates as LG  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _t(far=(600, 150), bits=8):
    return {"outline_um": [1000, 1000],
            "hard_cores": [{"inst": "u_a", "origin_um": [100, 100], "outline_um": [100, 100], "orient": "R0"}],
            "buses": [{"name": "b0", "width": 16}],
            "internal_stations": [{"conn": "core:u_a.q|bus:b0", "launch": "core:u_a.q", "capture": "face flop", "bits": bits,
                                   "from_um": [200, 150], "regs_um": [[400, 150]], "to_um": list(far)}]}


def _plan(t, name="dsdv_slice_c1x_C__t5"):
    return {"partition_types": {name: t}}


def _scan(tmp, ty, bits, groups):
    d = tmp / ty / "geom"
    d.mkdir(parents=True)
    (d / "placed_scan.json").write_text(json.dumps({"type": ty, "bits_over_cycle": bits, "bits_over_reach": bits + 10, "groups_need_station": groups}))
    return str(tmp)


def test_plan_bits_clean_and_mutant():
    assert B.plan_bits(_t())["over_cycle_bits"] == 0
    m = _t(far=(1100, 150))                      # last hop 700 um > 580 (cycle) and > 405 (reach)
    p = B.plan_bits(m)
    assert p["over_cycle_bits"] == 8 and p["over_reach_bits"] == 8 and p["over_cycle_chains"] == 1
    m2 = _t(far=(900, 150))                      # last hop 500 um: over reach only
    p2 = B.plan_bits(m2)
    assert p2["over_cycle_bits"] == 0 and p2["over_reach_bits"] == 8


def test_bits_from_bus_width_when_row_has_none():
    m = _t(far=(1100, 150))
    del m["internal_stations"][0]["bits"]
    assert B.plan_bits(m)["over_cycle_bits"] == 16


def test_findings_use_placed_scan_over_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACED_SCAN_DIRS", _scan(tmp_path, "dsdv_slice_c1x_C__t5", 4751, 77))
    out = B.findings(_plan(_t()), "p.json")
    assert any("gate 4751 bits over one cycle (placed)" in x and "77 group(s) need a station" in x for x in out)
    assert any("family dsdv_slice_c1x_C" in x for x in out) and out[-1].startswith("WARN ADV-BITS-OVER-CYCLE summary")
    monkeypatch.delenv("OT_PLACED_SCAN_DIRS")
    out2 = B.findings(_plan(_t()), "p.json")
    assert not any("gate 0 bits" in x and "dsdv_slice_c1x_C__t5" in x for x in out2)      # clean plan, no scan: no per-type line


def test_gate_route_goal_refused_and_clean(tmp_path):
    ds = [_scan(tmp_path, "dsdv_slice_c1x_C__t5", 4751, 77)]
    assert "route goal refused: 4751 bits" in B.gate_lines("dsdv_slice_c1x_C__t5", "route", _plan(_t()), scan_dirs=ds)[0]
    assert B.gate_lines("dsdv_slice_c1x_C__t5", "place", _plan(_t()), scan_dirs=ds) == []           # place probes are what closes it
    assert B.gate_lines("col_h9_r1__t1", "route", _plan(_t(), "col_h9_r1__t1"), scan_dirs=ds) == []   # not a dsdv_slice type
    clean = [_scan(tmp_path / "c", "dsdv_slice_c1x_C__t5", 0, 0)]
    assert B.gate_lines("dsdv_slice_c1x_C__t5", "route", _plan(_t()), scan_dirs=clean) == []
    nos = B.gate_lines("dsdv_slice_c1x_C__t5", "route", _plan(_t()))                                   # no scan at all: unknown, said so
    assert nos and "no placed scan" in nos[0]


def test_blocking_env_and_cli_exit(tmp_path, monkeypatch):
    assert not B.blocking({}) and B.blocking({"OT_BITS_OVER_CYCLE_BLOCK": "1"}) and LG.bits_blocking({"OT_BITS_OVER_CYCLE_BLOCK": "1"})
    assert not LG.bits_blocking({})
    pl = tmp_path / "plan.json"
    pl.write_text(json.dumps(_plan(_t(far=(1100, 150)))))
    monkeypatch.delenv("OT_BITS_OVER_CYCLE_BLOCK", raising=False)
    assert B.main([str(pl)]) == 0                       # report-only by default
    monkeypatch.setenv("OT_BITS_OVER_CYCLE_BLOCK", "1")
    assert B.main([str(pl)]) == 1                       # opt-in blocks


def test_launch_gates_lines_carry_the_gate(tmp_path):
    pl = tmp_path / "plan.json"
    pl.write_text(json.dumps(_plan(_t())))
    env = {"OT_KIT_TYPE": "dsdv_slice_c1x_C__t5", "OT_KIT_GOAL": "route",
           "OT_PLACED_SCAN_DIRS": _scan(tmp_path / "s", "dsdv_slice_c1x_C__t5", 100, 3)}
    out = LG.lines(str(tmp_path / "kit"), str(pl), env)
    assert any("ADV-BITS-OVER-CYCLE" in x and "route goal refused" in x for x in out)
    env["OT_KIT_GOAL"] = "place"
    assert not any("ADV-BITS-OVER-CYCLE" in x for x in LG.lines(str(tmp_path / "kit"), str(pl), env))


def test_pin_face_kvleaf_clean_and_mutant():
    t = _t()                                              # E-face pin (x=200), consumer to the east: not against
    assert B.pin_face_away(t)[:2] == (0, 1)
    m = _t(far=(50, 150))                                 # consumer WEST of the E-face pin: behind the face
    aw, tot, ab, bw, ex = B.pin_face_away(m)
    assert (aw, tot, ab) == (1, 1, 8) and bw == 8 * 2 * 150 and ex[0][3] == 300
    plan = {"partition_types": {"ot_s81sl_kv_leaf__t2": m, "ot_s81sl_leaf__t1": copy.deepcopy(m)}}
    out = B.pin_face_findings(plan, "p.json")
    assert any("ot_s81sl_kv_leaf__t2" in x and "1 of 1" in x for x in out)
    assert not any("ot_s81sl_leaf__t1 " in x for x in out)           # kv_leaf types only
    assert out[-1].startswith("WARN ADV-PIN-FACE-KVLEAF summary 1 kv_leaf types flagged")


def test_registered_in_plan_advisory():
    names = dict(PA.CHECKS)
    assert names["BITS-OVER-CYCLE"] == "adv_bitscycle:BITS-OVER-CYCLE" and names["PIN-FACE-KVLEAF"] == "adv_bitscycle:PIN-FACE-KVLEAF"
    out = PA.run(_plan(_t(far=(1100, 150))), "p.json", checks=["BITS-OVER-CYCLE"], jobs=1)
    assert any("ADV-BITS-OVER-CYCLE" in x for x in out)
