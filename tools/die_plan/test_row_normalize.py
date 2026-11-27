"""NORMALIZE (COMPOSE-FAST 11-25): reprice, bank legaliser, density tap names, retap and R8 refresh derived after the rows."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_normalize as RN  # noqa: E402


def _plan(fixed=2, regs_a=1):
    return {"partitions": [{"name": "pa", "type": "a"}, {"name": "pb", "type": "b"}],
            "ports": [{"id": "p1", "src": {"part": "pa", "bus": "o"}, "dst": {"part": "pb", "bus": "i"}}],
            "lanes": [{"id": "L1", "ports": ["p1"], "fixed_cycles": fixed}],
            "latency": {"lanes": {"L1": {"fixed": fixed, "cycles": fixed + 2, "natural": fixed}}},
            "partition_types": {"a": {"internal_stations": [{"conn": "bus:o", "regs_um": [[0, 0]] * regs_a}]},
                                "b": {"internal_stations": [{"conn": "bus:i", "regs_um": [[1, 1]]}]}}}


NOHOOK = dict(resite=lambda b, t, r: None, base_count=lambda tn: 0, legal_for=lambda tn: (lambda x, y: True, []),
              retap=lambda b, r, ty: {}, landremap=lambda b, r, ty: ({}, {}))


def test_unchanged_plan_is_untouched(tmp_path):
    base = _plan()
    raw = copy.deepcopy(base)
    rep = RN.normalize_plan(base, raw, hooks=NOHOOK)
    assert raw == base and rep["changed"] == {} and rep["touched_types"] == []
    (tmp_path / "b.json").write_text(json.dumps(base))
    (tmp_path / "i.json").write_text("{\n" + json.dumps(base)[1:])        # own formatting: kept byte-equal when nothing fires
    assert RN.main(["plan", "--base", str(tmp_path / "b.json"), "--in", str(tmp_path / "i.json"), "--out", str(tmp_path / "o.json"),
                    "--skip", "legal", "--skip", "tapname", "--skip", "retap"]) == 0
    assert (tmp_path / "o.json").read_bytes() == (tmp_path / "i.json").read_bytes()


def test_reprice_follows_added_station():
    base, raw = _plan(), _plan(regs_a=2)                   # the row added one station register on bus o
    rep = RN.normalize_plan(base, raw, hooks=NOHOOK)
    assert raw["lanes"][0]["fixed_cycles"] == 3
    assert raw["latency"]["lanes"]["L1"] == {"fixed": 3, "cycles": 5, "natural": 3}
    assert rep["steps"]["reprice"] == {"L1": [2, 3]} and rep["touched_types"] == ["a"]


def _ty(regs, sites, cores=None):
    return {"outline_um": [100, 100], "hard_cores": cores or [],
            "internal_stations": [{"conn": "bus:o", "regs_um": regs, "bit_sites_um": [sites]}]}


def test_legal_bank_follows_moved_regs_unless_row_moved_it():
    seen = []

    def resite(b, t, r):                                   # record the base regs the legaliser sees, shift by the regs delta
        seen.append(b["internal_stations"][0]["regs_um"])
        dx = t["internal_stations"][0]["regs_um"][0][0] - b["internal_stations"][0]["regs_um"][0][0]
        t["internal_stations"][0]["bit_sites_um"] = [[[q[0] + dx, q[1]] for q in g] for g in t["internal_stations"][0]["bit_sites_um"]]
    base = {"partition_types": {"a": _ty([[10, 10]], [[11, 10]])}}
    raw = {"partition_types": {"a": _ty([[20, 10]], [[11, 10]])}}          # regs moved, bank left behind
    rep = RN.step_legal(raw, base, ["a"], resite=resite)
    assert raw["partition_types"]["a"]["internal_stations"][0]["bit_sites_um"] == [[[21, 10]]] and rep["a"]["changed"]
    raw = {"partition_types": {"a": _ty([[20, 10]], [[21, 10]])}}          # the row moved the bank itself: no second shift
    RN.step_legal(raw, base, ["a"], resite=resite)
    assert seen[-1] == [[20, 10]] and raw["partition_types"]["a"]["internal_stations"][0]["bit_sites_um"] == [[[21, 10]]]
    raw = {"partition_types": {"a": base["partition_types"]["a"], "x": {"outline_um": [1, 1]}}}
    assert RN.step_legal(raw, base, ["a", "x"], resite=resite) == {}      # stations and cores as in BASE: not legalised


def test_tapname_renames_from_new_base_and_relegalises():
    raw = {"partition_types": {"pv": {"clock": {"tap_mode": "density", "added_taps": [
        {"name": "clk_t150", "xy": [5.0, 5.0]}, {"name": "clk_t151", "xy": [50.0, 50.0]}]}},
        "grid": {"clock": {"tap_mode": "grid", "added_taps": [{"name": "clk_t9", "xy": [1, 1]}]}}}}

    def legal_for(tn):
        return (lambda x, y: x >= 6.0 - 1e-9), []
    rep = RN.step_tapname(raw, ["pv", "grid"], base_count=lambda tn: 158, legal_for=legal_for)
    added = raw["partition_types"]["pv"]["clock"]["added_taps"]
    assert [a["name"] for a in added] == ["clk_t158", "clk_t159"]
    assert added[0]["xy"][0] >= 6.0 and abs(added[0]["xy"][0] - 6.0) < 0.06 and added[1]["xy"] == [50.0, 50.0]
    assert rep["pv"]["renamed"] == 2 and rep["pv"]["relegalised"] == 1
    assert raw["partition_types"]["grid"]["clock"]["added_taps"][0]["name"] == "clk_t9" and "grid" not in rep


def test_tapname_names_already_right_is_noop():
    raw = {"partition_types": {"pv": {"clock": {"tap_mode": "density", "added_taps": [{"name": "clk_t4", "xy": [1, 1]}]}}}}
    before = copy.deepcopy(raw)
    assert RN.step_tapname(raw, ["pv"], base_count=lambda tn: 4, legal_for=lambda tn: ((lambda x, y: True), [])) == {}
    assert raw == before


def test_tables_reports_r8_drift_fixed(tmp_path, monkeypatch):
    import r8_refresh as RR
    (tmp_path / "r8.json").write_text(json.dumps({"members": [{"id": "m", "bound": 30}]}))
    (tmp_path / "x.json").write_text(json.dumps({"members": []}))
    (tmp_path / "ab.json").write_text(json.dumps({"land_r8": "r8.json", "land_r8_extra": ["x.json"]}))

    def fake(argv):                                       # the derive moved the bound depth 30 -> 32 (KV pvw_1)
        Path(argv[2]).write_text(json.dumps({"members": [{"id": "m", "bound": 32}]}))
        print("R8_REFRESH OK")
        return 0
    monkeypatch.setattr(RR, "main", fake)
    rep = RN.normalize_tables(tmp_path / "p.json", tmp_path, "ab.json", tmp_path / "bg.json")
    assert rep["rc"] == 0 and list(rep["fixed"]) == ["r8.json"] and "R8 drift fixed in 1 of 2" in rep["r8"]
    (tmp_path / "ab.json").write_text(json.dumps({}))
    assert RN.normalize_tables(tmp_path / "p.json", tmp_path, "ab.json", tmp_path / "bg.json")["fixed"] == {}


def test_landremap_runs_before_retap_and_its_names_survive_retap():
    order = []
    base = {"partition_types": {"pv": {"clock": {"tap_mode": "density", "added_taps": [{"name": "clk_t5", "xy": [1, 1]}],
                                                  "landing_raw_branches": {"b": "rst_rl_1"},
                                                  "landing_contract": {"pins": [{"source_clock_tap": "clk_t5"}]}}}}}
    raw = copy.deepcopy(base)
    raw["partition_types"]["pv"]["clock"]["added_taps"][0]["xy"] = [2, 2]

    def landremap(b, r, ty):                                  # sees OLD reference names, renames them itself
        ck = r["partition_types"]["pv"]["clock"]
        order.append(("landremap", ck["landing_contract"]["pins"][0]["source_clock_tap"]))
        ck["landing_raw_branches"] = {"b": "rst_rl_9"}
        ck["landing_contract"]["pins"][0]["source_clock_tap"] = "clk_t4"
        return {"pv": 2}, {"pv": RN._protect(r["partition_types"]["pv"])}

    def retap(b, r, ty):                                      # would map clk_t4 a second time through the old table
        order.append("retap")
        ck = r["partition_types"]["pv"]["clock"]
        ck["landing_contract"]["pins"][0]["source_clock_tap"] = "clk_t3"
        ck["landing_raw_branches"] = {"b": "rst_rl_1"}
        return {"pv": 1}
    hooks = dict(NOHOOK, landremap=landremap, retap=retap, base_count=lambda tn: 4)
    rep = RN.normalize_plan(base, raw, hooks=hooks)
    ck = raw["partition_types"]["pv"]["clock"]
    assert order == [("landremap", "clk_t5"), "retap"]
    assert ck["landing_contract"]["pins"][0]["source_clock_tap"] == "clk_t4" and ck["landing_raw_branches"] == {"b": "rst_rl_9"}
    assert ck["added_taps"][0]["name"] == "clk_t4" and rep["steps"]["landremap"] == {"pv": 2}


def test_landremap_error_on_one_type_does_not_fail_the_others(monkeypatch):
    """LANDREMAP-ISOLATE-1125 (KV A5t8): one RemapError on kv3_sys_SD marked all 5 landremap types failed (rc 3).  Now the
    named type fails alone, the plan is restored from its partial rewrite and the others are re-run."""
    import landing_remap as LM
    calls = []

    def fake(braw, raw, root, plan_dir, types, **kw):
        calls.append(sorted(types))
        for tn in sorted(types):
            raw["partition_types"][tn]["touched"] = True                      # partial rewrite before the raise
        if "sd" in types:
            raise LM.RemapError("sd: tap reference(s) ['clk_t11'] are not in the old plan's tap table")
        return dict(taps=[dict(type=tn, remaps=[1]) for tn in sorted(types)])
    monkeypatch.setattr(LM, "remap_plan", fake)
    raw = {"partition_types": {"sd": {"clock": {}}, "pv": {"clock": {}}, "pw": {"clock": {}}}}
    rep, prot = RN.step_landremap({}, raw, "/", "/x/plan.json", ["sd", "pv", "pw"])
    assert calls == [["pv", "pw", "sd"], ["pv", "pw"]]
    assert rep["sd"]["failed"].startswith("landing_remap RemapError: sd:") and rep["pv"] == 1 and rep["pw"] == 1
    assert "touched" not in raw["partition_types"]["sd"] and raw["partition_types"]["pv"]["touched"]
    assert set(prot) == {"pv", "pw"}


def test_landremap_error_naming_no_type_fails_all(monkeypatch):
    import landing_remap as LM

    def fake(braw, raw, root, plan_dir, types, **kw):
        raise LM.RemapError("bad tree")
    monkeypatch.setattr(LM, "remap_plan", fake)
    raw = {"partition_types": {"sd": {"clock": {}}, "pv": {"clock": {}}}}
    rep, prot = RN.step_landremap({}, raw, "/", "/x/plan.json", ["sd", "pv"])
    assert set(rep) == {"sd", "pv"} and all("bad tree" in v["failed"] for v in rep.values()) and prot == {}

def test_retap_reuses_only_the_prepared_base_tree(monkeypatch):
    from concurrent.futures import Future
    import retap

    base, candidate = {}, {}
    good, failed = Future(), Future()
    good.set_result({"old": {"relays": [{"name": "prepared"}]}})
    failed.set_exception(RuntimeError("worker stopped"))
    calls = []

    def direct(raw, path):
        return lambda tn: calls.append((raw is base, path, tn)) or {"relays": []}

    def repoint(braw, raw, base_path, path, *, types, tree_fn):
        assert types == {"old", "missing"}
        assert tree_fn(braw, base_path)("old") == good.result()["old"]
        assert tree_fn(braw, base_path)("missing") == {"relays": []}
        assert tree_fn(raw, path)("old") == {"relays": []}
        return {}

    monkeypatch.setattr(retap, "_plan_tree", direct)
    monkeypatch.setattr(retap, "repoint", repoint)
    assert RN.step_retap(base, candidate, "/base/plan.json", "/candidate/plan.json",
                         ["old", "missing"], base_trees={"old": good, "missing": failed}) == {}
    assert calls == [(True, "/base/plan.json", "missing"), (False, "/candidate/plan.json", "old")]


def test_retap_repicks_after_protected_landing_refs_are_restored(monkeypatch):
    import retap

    clock = {
        "landing_reader_start": {"branches": {"ft_i": {"stages": [
            {"xy_um": [105.0, 100.0], "raw_reset": "rr_t2"},
            {"xy_um": [105.0, 100.0], "raw_reset": "rst_rl_5"},
        ]}}},
        "landing_writer_start": {"branches": {"ft_o": {"stages": [
            {"xy_um": [900.0, 100.0], "raw_reset": "rr_t0"},
        ]}}},
        "landing_raw_branches": [{"consumers": ["writer:ft_o:0"]}],
    }
    base = {"partition_types": {"ft": {"clock": clock}}}
    candidate = copy.deepcopy(base)
    protect = {"ft": RN._protect(candidate["partition_types"]["ft"])}
    taps = [("clk", 100.0, 100.0), ("clk_t1", 500.0, 100.0), ("clk_t2", 900.0, 100.0)]
    monkeypatch.setattr(retap, "_plan_taps",
                        lambda raw, path: lambda tn: taps if raw is base else taps[:-1] + [("clk_t2", 910.0, 100.0)])
    monkeypatch.setattr(retap, "_plan_consumer_taps", lambda raw, path: lambda tn: taps)

    RN.step_retap(base, candidate, "/base/plan.json", "/candidate/plan.json", ["ft"], protect)

    actual = candidate["partition_types"]["ft"]["clock"]
    reader = actual["landing_reader_start"]["branches"]["ft_i"]["stages"]
    writer = actual["landing_writer_start"]["branches"]["ft_o"]["stages"]
    original = clock["landing_reader_start"]["branches"]["ft_i"]["stages"]
    assert [stage["raw_reset"] for stage in reader] == ["rr_t0", "rst_rl_5"]
    assert writer[0]["raw_reset"] == "rr_t0"
    assert original[0]["raw_reset"] == "rr_t2"


def _lr_plan(flag=None):
    core = {"inst": "cl_x", "origin_um": [300.0, 1000.0], "outline_um": [90.0, 50.0], "orient": "R0", "lef": "v/m.lef",
            "param_wrap": {"params": {"WFALL": 1}}}
    band = {"hard_core": "cl_x", "rect_um": [300.0, 1000.0, 390.0, 1050.0], "width": 10}
    t = {"outline_um": [1000.0, 1300.0], "hard_cores": [core], "buses": [], "ft_slots": [{"name": "x", "in_face": "N", "regs_um": [[455.0, 1296.0]]}],
         "clock": {"landing_contract": {"bands": {"x_i": band}, "pins": [{"name": "fclk_in_x_i", "xy_um": [455.0, 1296.0]}]}}}
    raw = {"die": {"name": "qwen_compute", "period_ps": 833}, "clock": {}, "partition_types": {"t": t}}
    if flag is not None:
        raw["land_reach"] = flag
    return raw


def test_land_reach_flag_off_changes_nothing_and_on_reseats(tmp_path):
    body = "".join(f"  PIN d[{k}]\n    PORT\n      LAYER M5 ;\n        RECT  {k * 0.144:.3f} 49.9 {k * 0.144 + 0.024:.3f} 49.984 ;\n"
                   f"    END\n  END d[{k}]\n" for k in range(10))
    (tmp_path / "v").mkdir()
    (tmp_path / "v/m.lef").write_text(f"MACRO m\n  SIZE 90.0 BY 50.0 ;\n{body}END m\n")
    base = _lr_plan()
    off = copy.deepcopy(base)
    rep = RN.normalize_plan(base, off, tree=str(tmp_path), hooks=NOHOOK)
    assert off == base and "landreach" not in rep["steps"] and "landreach" not in rep["seconds"] and rep["changed"] == {}
    on = _lr_plan({"enable": 1})
    rep = RN.normalize_plan(base, on, tree=str(tmp_path), hooks=NOHOOK)
    assert rep["steps"]["landreach"] and rep["changed"]["landreach"] == 1 and on["partition_types"]["t"]["hard_cores"][0]["origin_um"] != [300.0, 1000.0]
    assert rep["touched_types"] == ["t"]               # the later steps (legal / tapname / landremap / retap) see the re-seated type
    assert RN.normalize_plan(base, _lr_plan({"enable": 1}), tree=str(tmp_path), skip=["landreach"], hooks=NOHOOK)["steps"].get("landreach") is None



def test_legacy_sink_trials_keep_first_feasible_result(monkeypatch):
    import reset_tree
    import taps

    monkeypatch.setattr(reset_tree, "pool_size", lambda n: min(n, 4))
    points = tuple((float(x + 2), float(y + 2)) for x in range(12) for y in range(12))
    args = points, 16.0, 16.0, 2.5, 16, (8.0, 8.0)
    serial = taps._solve_sink_grid(*args)
    assert taps._solve_sink_grid(*args, parallel=True) == serial
    taps._shared_sink_grid.cache_clear()
    try:
        assert taps._shared_sink_grid(*args) == serial
        assert taps._shared_sink_grid(*args) == serial
        assert taps._shared_sink_grid.cache_info().hits == 1
    finally:
        taps._shared_sink_grid.cache_clear()

    import threading

    monkeypatch.setattr(threading, "active_count", lambda: 2)
    def unsafe_pool(_):
        raise AssertionError("must leave the trial in the serial reader")

    monkeypatch.setattr(reset_tree, "pool_size", unsafe_pool)
    assert taps._solve_sink_grid(*args, parallel=True) == serial
