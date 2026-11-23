"""tap_split.py (TAP-GRID-R5 11-21, COORD lever 6.1): plan tap splitter.   python3 -m pytest -q tools/die_plan/test_tap_split.py"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
import taps  # noqa: E402
import tap_split as TS  # noqa: E402


class _Free:
    """every point inside the outline (margin 8.64) and 8.64 um off every tap is legal; snapped to 0.01 um."""

    def __init__(self, P, tn, fixed):
        self.w, self.h = P.types[tn]["outline_um"]
        self.fixed = list(fixed)

    def place(self, x, y, added):
        x, y = round(min(max(x, 8.64), self.w - 8.64), 2), round(min(max(y, 8.64), self.h - 8.64), 2)
        if any(abs(x - a) < 8.64 and abs(y - b) < 8.64 for a, b in self.fixed + list(added)):
            return None
        return (x, y)


def _setup(monkeypatch, mode, tps, sinks, cap=1000):
    P = SimpleNamespace(types={"t": {"outline_um": [800.0, 800.0], "clock": {"tap_mode": mode, "tap_max_sinks": cap}}})
    monkeypatch.setattr(schema, "tap_grid", lambda P_, tn: list(tps))
    monkeypatch.setattr(taps, "sink_sites", lambda P_, tn, control=True: list(sinks))
    monkeypatch.setattr(gen_phys, "_tap_cap", lambda t: cap)
    monkeypatch.setattr(TS, "Site", _Free)
    return P


def _line(n, x0, y0, x1, y1):
    return [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1), 1.0) for i in range(n)]


def test_explicit_tap_over_cap_is_split_to_cap_and_radius(monkeypatch):
    # coll_ft-like: two explicit taps, a dense 3,000-sink station column between them, 260 um from both
    tps = [("clk", 100.0, 400.0), ("clk_t1", 600.0, 400.0)]
    sinks = _line(3000, 360.0, 280.0, 360.0, 520.0)
    P = _setup(monkeypatch, "explicit", tps, sinks)
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["status"] == "SPLIT" and rep["key"] == "taps"
    assert [r["name"] for r in rows] == [f"clk_t{2 + i}" for i in range(len(rows))]
    allt = [(x, y) for _, x, y in tps] + [tuple(r["xy"]) for r in rows]
    loads = taps.tap_loads(allt, sinks)
    assert max(n for n, _ in loads) <= 1000 and max(f for _, f in loads) <= 300.0
    assert all(n > 0 for n, _ in loads[2:])               # no empty added tap


def test_density_far_sinks_get_a_tap_within_radius(monkeypatch):
    tps = [("clk", 100.0, 100.0)]
    sinks = _line(200, 90.0, 90.0, 110.0, 110.0) + _line(50, 700.0, 700.0, 720.0, 720.0)
    P = _setup(monkeypatch, "density", tps, sinks)
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["status"] == "SPLIT" and rep["key"] == "added_taps" and len(rows) == 1
    assert rep["before"]["over_radius"] == 1 and rep["after"]["max_radius"] <= 300.0


def test_ok_type_unchanged_and_grid_mode_unsupported(monkeypatch):
    tps = [("clk", 100.0, 100.0)]
    P = _setup(monkeypatch, "density", tps, _line(500, 90.0, 90.0, 110.0, 110.0))
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["status"] == "OK" and rows == []
    P = _setup(monkeypatch, "grid", tps, _line(3000, 90.0, 90.0, 110.0, 110.0))
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["status"] == "UNSUPPORTED" and rows == []


def test_apply_rows_appends_after_existing_entries():
    raw = {"partition_types": {"a": {"clock": {"added_taps": [{"name": "clk_t5", "xy": [1, 2]}]}},
                               "b": {"clock": {"taps": [{"name": "clk", "xy": [0, 0]}, {"name": "u.clk", "kind": "core", "xy": [3, 3]}]}}}}
    TS.apply_rows(raw, {"a": ("added_taps", [{"name": "clk_t6", "xy": [9, 9]}]),
                        "b": ("taps", [{"name": "clk_t1", "xy": [5, 5]}])})
    assert [p["name"] for p in raw["partition_types"]["a"]["clock"]["added_taps"]] == ["clk_t5", "clk_t6"]
    assert raw["partition_types"]["b"]["clock"]["taps"][-1] == {"name": "clk_t1", "xy": [5, 5]}


def test_radius_bound_is_300(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({}))
    with pytest.raises(SystemExit):
        TS.main([str(p), "--radius-um", "301", "--rows", str(tmp_path / "r.json")])


def test_cap_option_only_tightens(monkeypatch):
    """TAP-GRID-R5 11-22 (Fable lever 8): --cap 1650 splits to min(plan cap, 1650); a larger --cap never loosens the plan cap."""
    import inspect
    src = inspect.getsource(TS.split_type)
    assert "min(cap, gen_phys._tap_cap(t))" in src
    assert "--cap" in inspect.getsource(TS.main)


def test_placed_inventory_replaces_planned_only_model(monkeypatch, tmp_path):
    """TAP-SOFTFLOP (TAP-GRID-R5 11-22, COORD; MISC-R4 kv_leaf t5): the planned sinks (face / ft only) are under the cap,
    the placed register inventory is not -> split on the placed one; the .reg die origin is subtracted."""
    tps = [("clk", 100.0, 400.0), ("clk_t1", 600.0, 400.0)]
    P = _setup(monkeypatch, "grid+explicit", tps, _line(50, 90.0, 390.0, 110.0, 410.0))
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["status"] == "OK" and rep["sink_basis"] == "planned" and "SINK-MODEL-PLANNED-ONLY" in rep["why"]
    reg = tmp_path / "t.reg"
    reg.write_text("D 10.0 20.0 810.0 820.0\n" + "".join(f"R {x + 10.0:.3f} {y + 20.0:.3f}\n" for x, y, _ in _line(3000, 360.0, 280.0, 360.0, 520.0)))
    pl = TS.load_placed(reg)
    assert len(pl) == 3000 and abs(pl[0][0] - 360.0) < 1e-6 and abs(pl[0][1] - 280.0) < 1e-6
    monkeypatch.setitem(TS.PLACED, "t", pl)
    rep, rows = TS.split_type(P, "t", 300.0, 50)
    assert rep["sink_basis"] == "placed" and rep["status"] == "SPLIT" and rep["before"]["max_load"] > 1000
    assert rep["after"]["max_load"] <= 1000 and rows


def test_require_placed_refuses_planned_only_type(monkeypatch):
    P = _setup(monkeypatch, "grid+explicit", [("clk", 100.0, 100.0)], _line(50, 90.0, 90.0, 110.0, 110.0))
    monkeypatch.setattr(TS, "PLACED", {})
    rep, rows = TS.split_type(P, "t", 300.0, 50, require_placed=True)
    assert rep["status"] == "NO_PLACED" and rows == []
    P.types["t"]["clock"]["sink_bins_file"] = "x.json"           # a placed-netlist bins file is a full inventory
    rep, rows = TS.split_type(P, "t", 300.0, 50, require_placed=True)
    assert rep["sink_basis"] == "bins" and rep["status"] == "OK"


def test_load_placed_formats(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps({"bin_um": 10.8, "bins": [[5.4, 5.4, 3]]}))
    (tmp_path / "l.json").write_text(json.dumps([[1.0, 2.0], [3.0, 4.0]]))
    assert TS.load_placed(tmp_path / "b.json") == [(5.4, 5.4, 3.0)]
    assert TS.load_placed(tmp_path / "l.json") == [(1.0, 2.0, 1.0), (3.0, 4.0, 1.0)]


def _raw2():
    return {"partition_types": {
        "a": {"clock": {"added_taps": [], "landing_local_resets": [{"raw": "rst_rl_1"}]}},
        "b": {"clock": {"added_taps": [], "landing_local_resets": [{"raw": "rst_rl_2"}]}},
        "c": {"clock": {"added_taps": []}}}}


def test_remap_always_runs_anchor_and_drops_stale_types(tmp_path):
    """REMAP-ALWAYS (TAP-GRID-R5 11-23, COORD): every touched type is remapped; a type the remap refuses (a) or whose
    landing reference the PRE check still finds stale (b) is restored to the input plan and reported; c stays."""
    import copy
    orig = _raw2()
    raw = copy.deepcopy(orig)
    for t in ("a", "b", "c"):
        raw["partition_types"][t]["clock"]["added_taps"] = [{"name": f"clk_t9{t}", "xy": [1, 2]}]
    seen = {}

    def remap_fn(old, new, names):
        seen.setdefault("calls", []).append(list(names))
        if "a" in names:
            raise ValueError("a: 1 relay(s) with no successor")
        for t in names:
            new["partition_types"][t]["clock"]["remapped"] = True
        return {"resets": []}

    def check_fn(new_path, old_path):
        d = json.loads(Path(new_path).read_text())["partition_types"]
        return ["FAIL LANDREMAP b: 1 stale"] if d["b"]["clock"].get("added_taps") else []

    out = tmp_path / "out.json"
    rec, failed = TS.remap_rows(orig, raw, str(tmp_path / "in.json"), str(out), ["a", "b", "c"], str(tmp_path),
                                remap_fn=remap_fn, check_fn=check_fn)
    assert seen["calls"][0] == ["a", "b", "c"] and seen["calls"][1] == ["b", "c"]
    assert set(failed) == {"a", "b"} and all(v.startswith("REMAP_FAIL") for v in failed.values())
    w = json.loads(out.read_text())["partition_types"]
    assert w["a"] == orig["partition_types"]["a"] and w["b"] == orig["partition_types"]["b"]
    assert w["c"]["clock"]["added_taps"] and w["c"]["clock"].get("remapped")


def test_main_out_plan_always_remaps_and_exits_3_on_stale(monkeypatch, tmp_path):
    import inspect
    src = inspect.getsource(TS.main)
    assert "remap_rows(" in src and "return rc" in src and "--no-remap" not in src
    assert 'resets="anchor"' in inspect.getsource(TS.remap_rows)


def _dense(nx, ny, x0, y0, w, h):
    return [(x0 + w * i / (nx - 1), y0 + h * j / (ny - 1), 1.0) for i in range(nx) for j in range(ny)]


def test_multi_tap_splits_dense_cluster_single_add_cannot(monkeypatch):
    """MULTI-TAP (TAP-GRID-R5 11-23, COORD): leaf t47 clk_t29 form -- 2,700 sinks in a 98 x 28 um box served by one tap.
    Any single new tap takes the whole cluster (no improvement, greedy stops); k-medians k = ceil(2700/900) = 3 splits it."""
    # the serving tap sits 240 um off the cluster (L1 diameter 126 um): every sink is nearer ANY new tap in the box
    tps = [("clk", 180.0, 180.0)]
    sinks = _dense(90, 30, 300.0, 300.0, 98.0, 28.0)
    P = _setup(monkeypatch, "grid+explicit", tps, sinks)
    rep0, rows0 = TS.split_type(P, "t", 400.0, 50, multi_margin=0)
    assert rep0["status"] == "BLOCKED" and not rows0 and rep0["after"]["max_load"] == 2700
    rep, rows = TS.split_type(P, "t", 400.0, 50)
    assert rep["status"] == "SPLIT" and rep.get("multi", 0) >= 1, rep
    allt = [(x, y) for _, x, y in tps] + [tuple(r["xy"]) for r in rows]
    loads = taps.tap_loads(allt, sinks)
    assert max(n for n, _ in loads) <= 1000 and max(f for _, f in loads) <= 400.0
    assert all(n > 0 for n, _ in loads[1:]) and 3 <= len(rows) <= 5


def test_kmedians_seeds_and_converges():
    import numpy as np
    pts = _dense(30, 10, 0.0, 0.0, 90.0, 9.0)
    X, Y, W = (np.array([p[i] for p in pts]) for i in range(3))
    C = sorted(TS.kmedians(X, Y, W, 3))
    assert len(C) == 3 and C[0][0] < 30 < C[1][0] < 60 < C[2][0]
