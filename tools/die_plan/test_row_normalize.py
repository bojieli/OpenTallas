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
              retap=lambda b, r, ty: {})


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
