"""land_reach: re-seat a flagged hard cland core + band to its port; default off, byte-identical without the flag."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_land_reach as A  # noqa: E402
import land_reach as L  # noqa: E402


def _lef(path, w, h, n, y):
    body = "".join(f"  PIN d[{k}]\n    PORT\n      LAYER M5 ;\n        RECT  {k * 0.144:.3f} {y} {k * 0.144 + 0.024:.3f} {y + 0.084} ;\n"
                   f"    END\n  END d[{k}]\n" for k in range(n))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"MACRO m\n  SIZE {w} BY {h} ;\n{body}END m\n")


def _plan(core_xy=(300.0, 1000.0), flag=None, block=None):
    core = {"inst": "cl_x", "origin_um": list(core_xy), "outline_um": [90.0, 50.0], "orient": "R0", "lef": "v/m.lef",
            "param_wrap": {"params": {"WFALL": 1}}}
    band = {"hard_core": "cl_x", "rect_um": [core_xy[0], core_xy[1], core_xy[0] + 90.0, core_xy[1] + 50.0], "width": 10,
            "max_pin_to_band_hop_um": 100.0}
    t = {"outline_um": [1000.0, 1300.0], "hard_cores": [core], "buses": [],
         "ft_slots": [{"name": "x", "in_face": "N", "regs_um": [[455.0, 1296.0]]}],
         "clock": {"keepouts_um": [list(block)] if block else [],
                   "landing_contract": {"bands": {"x_i": band}, "pins": [{"name": "fclk_in_x_i", "xy_um": [455.0, 1296.0]}]}}}
    raw = {"die": {"name": "qwen_compute", "period_ps": 833}, "clock": {}, "partition_types": {"t": t}}
    if flag is not None:
        raw["land_reach"] = flag
    return raw


def _tree(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    return str(tmp_path)


def test_flag_absent_is_noop_and_identical(tmp_path):
    raw = _plan()
    before = json.dumps(raw, sort_keys=True)
    assert not L.enabled(raw) and L.run_flagged(raw, _tree(tmp_path)) is None
    assert json.dumps(raw, sort_keys=True) == before
    assert L.enabled(_plan(flag={"enable": 1})) and not L.enabled(_plan(flag={"enable": 0}))


def test_adv_rows_unchanged_by_detail_hook(tmp_path):
    raw, tree = _plan(), _tree(tmp_path)
    det = []
    assert A.rows(raw, tree) == A.rows(raw, tree, detail=det) and det and det[0]["pins"]


def test_flagged_core_reseated_within_allowance(tmp_path):
    tree = _tree(tmp_path)
    raw = _plan(flag={"enable": 1})
    assert A.rows(raw, tree)[0]["verdict"] == "FAIL"
    rep = L.run_flagged(raw, tree)
    assert rep["summary"]["moved"] == 1 and rep["moved"][0]["status"] == "ok"
    r = A.rows(raw, tree)[0]
    assert r["verdict"] != "FAIL" and r["mmax"] >= 0 and rep["after"]["fail"] == 0
    t = raw["partition_types"]["t"]
    c, b = t["hard_cores"][0], t["clock"]["landing_contract"]["bands"]["x_i"]
    dx, dy = c["origin_um"][0] - 300.0, c["origin_um"][1] - 1000.0
    assert abs(dx / L.STEP_UM - round(dx / L.STEP_UM)) < 1e-6 and abs(dy / L.STEP_UM - round(dy / L.STEP_UM)) < 1e-6
    assert b["rect_um"][0] == round(300.0 + dx, 4) and b["land_reach_from_um"] == [300.0, 1000.0, 390.0, 1050.0]
    assert "C-LAND-REACH" in c["note"]


def test_obstacle_keeps_core_off_blocked_seat(tmp_path):
    tree = _tree(tmp_path)
    free = _plan(flag={"enable": 1})
    L.run_flagged(free, tree)
    nx, ny = free["partition_types"]["t"]["hard_cores"][0]["origin_um"]
    blocked = _plan(flag={"enable": 1}, block=(nx - 5, ny - 5, nx + 95, ny + 55))
    rep = L.run_flagged(blocked, tree)
    c = blocked["partition_types"]["t"]["hard_cores"][0]
    ox, oy = c["origin_um"]
    assert not (ox < nx + 95 + 8.64 and ox + 90 > nx - 5 - 8.64 and oy < ny + 55 + 8.64 and oy + 50 > ny - 5 - 8.64) or rep["unresolved"]


def test_no_legal_seat_is_reported_not_forced(tmp_path):
    tree = _tree(tmp_path)
    raw = _plan(flag={"enable": 1}, block=(0, 0, 1000, 1300))
    before = copy.deepcopy(raw["partition_types"])
    rep = L.run_flagged(raw, tree)
    assert rep["summary"]["unresolved"] == 1 and raw["partition_types"] == before


def test_check_mode_writes_nothing_and_missing_lef_skipped(tmp_path):
    tree = _tree(tmp_path)
    raw = _plan(flag={"enable": 1})
    before = copy.deepcopy(raw)
    rep = L.apply(raw, tree, check=True)
    assert rep["summary"]["moved"] == 1 and raw == before
    nolef = _plan(flag={"enable": 1})
    nolef["partition_types"]["t"]["hard_cores"][0]["lef"] = "missing.lef"
    assert L.apply(nolef, None)["summary"]["skipped"] == 1


def test_cli_flag_gate(tmp_path):
    tree = _tree(tmp_path)
    p, o = tmp_path / "p.json", tmp_path / "o.json"
    p.write_text(json.dumps(_plan()))
    assert L.main([str(p), str(o), "--tree", tree]) == 0 and not o.exists()      # flag absent: nothing written
    assert L.main([str(p), str(o), "--tree", tree, "--force"]) == 0 and o.exists()
    assert A.rows(json.loads(o.read_text()), tree)[0]["verdict"] != "FAIL"


def test_sidecar_path_read_or_named_error(tmp_path):
    tree = _tree(tmp_path)
    (tmp_path / "side.json").write_text(json.dumps({"collector": {"types": {}}}))
    ok = L.apply(_plan(flag={"enable": 1, "sidecar": "side.json"}), tree, check=True)
    bad = L.apply(_plan(flag={"enable": 1, "sidecar": "nope.json"}), tree, check=True)
    assert "sidecar_error" not in ok and "sidecar_error" in bad and bad["summary"]["moved"] == 1


def test_flag_is_known_to_the_plan_schema():
    import schema as S
    errs = []
    S._check({"enable": 1, "margin_ps": -100, "types": "^sle_", "landings": ["t/x_i"], "sidecar": "a/b.json"}, S.SCHEMA["properties"]["land_reach"], "$", errs)
    assert errs == []
    bad = []
    S._check({"enable": 1, "bogus": 2}, S.SCHEMA["properties"]["land_reach"], "$", bad)
    assert bad and "bogus" in bad[0]
