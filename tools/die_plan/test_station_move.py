"""STATION-MOVE-HELPER 11-24: station_move.py (move / remove / reseat with every derived record) + station_xref.py (PRE STNXREF)."""
import copy
import json
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import station_move as SM  # noqa: E402
import station_xref as SX  # noqa: E402

TAPS = {1: (950.0, 100.0), 2: (650.0, 100.0), 3: (350.0, 100.0), 4: (80.0, 100.0)}


def taps_fn(raw, tn):
    return dict(TAPS)


def price_fn(raw):
    t = raw["partition_types"]["T"]
    st = next(s for s in t["ft_slots"] if s["name"] == "ft4")["stations"]
    return {"L1": {"cycles": 6 + st, "stations": st, "natural": 6 + st, "pad": 0}}


def _bits(x, y):
    return [[x - 0.7, y - 0.1], [x - 0.7, y + 0.2]]


def plan():
    regs = [[1000.0, 100.0], [700.0, 100.0], [400.0, 100.0], [100.0, 100.0]]
    return {
        "partitions": [{"name": "p0", "type": "T", "origin_um": [0.0, 0.0]}, {"name": "p1", "type": "U", "origin_um": [1000.0, 0.0]}],
        "partition_types": {
            "T": {"outline_um": [1000.0, 200.0],
                  "ft_slots": [{"name": "ft4", "in_face": "E", "out_face": "W", "width": 2, "stations": 4, "regs_um": regs,
                                "bit_sites_um": [_bits(*r) for r in regs[1:]], "bit_site_cell_um": [1.4, 0.27]}],
                  "reset": {"bank_taps": [{"tap": 1, "sinks": ["u_ft_ft4_o_0"]}, {"tap": 2, "sinks": ["u_ft_ft4_o_1"]},
                                          {"tap": 3, "sinks": ["u_ft_ft4_o_2"]}, {"tap": 4, "sinks": ["u_ft_ft4_o_3"]}]},
                  "clock": {"landing_contract": {"pins": [{"name": "fclk_in_ft4_i", "xy_um": [1000.0, 100.0]},
                                                          {"name": "cland_fstart_in_ft4_i", "xy_um": [1000.0, 108.0]}]},
                            "edge_clocks": [{"port": "fclk_in_ft4_i", "tap_um": [1000.0, 100.0]}]}},
            "U": {"outline_um": [500.0, 200.0],
                  "clock": {"landing_contract": {"pins": [{"name": "fclk_out_x_o", "xy_um": [10.0, 100.0]}]}}}},
        "clock": {"landing_network": {"edges": [{"id": "e0", "src": {"part": "p1", "bus": "fclk_out_x_o"},
                                                 "dst": {"part": "p0", "bus": "fclk_in_ft4_i"}, "max_hop_um": 405}]}},
        "latency": {"lanes": {"L1": {"cycles": 10, "stations": 4, "natural": 10, "pad": 0, "param": "LAT_L1"}}},
    }


def run(raw, ops):
    return SM.apply(raw, ops, taps_fn=taps_fn, price_fn=price_fn)


def own(raw, base):
    lines = SX.findings(raw, base, forms=tuple(f for f in SX.FORMS if f != "STAGECNT"))
    return [x for x in lines if x.startswith("WARN ")], SX.counts(lines)


# ---- station_xref (the PRE class) -----------------------------------------------------------------------------------------

def test_xref_clean_plan_is_quiet():
    w, c = own(plan(), plan())
    assert w == [] and sum(c.values()) == 0


def test_xref_banksink_removed_station_kv_c2t_form():
    raw = plan()
    s = raw["partition_types"]["T"]["ft_slots"][0]
    s["regs_um"].pop(2); s["bit_sites_um"].pop(1); s["stations"] = 3          # NOSEAM form: count down, bank_taps untouched
    w, c = own(raw, plan())
    assert c["BANKSINK"] == 1 and "u_ft_ft4_o_3" in next(x for x in w if "BANKSINK" in x)


def test_xref_bankfollow_reseat_left_on_old_tap():
    raw = plan()
    raw["partition_types"]["T"]["ft_slots"][0]["regs_um"][1] = [500.0, 100.0]
    _, c = own(raw, plan())
    assert c["BANKFOLLOW"] == 1 and c["BITFOLLOW"] == 1                       # neither tap nor bits followed


def test_xref_landhop_and_landfollow_s81_d2_form():
    raw = plan()
    raw["partitions"][1]["origin_um"] = [1900.0, 0.0]                         # src port moved, edge keeps no relays
    raw["partition_types"]["T"]["ft_slots"][0]["regs_um"][0] = [1000.0, 101.0]  # station 0 off its face pin by 1 um
    w, c = own(raw, plan())
    assert c["LANDHOP"] == 1 and c["LANDFOLLOW"] == 0                         # 1.0 um == TOL: not yet a finding
    raw["partition_types"]["T"]["ft_slots"][0]["regs_um"][0] = [1000.0, 103.0]
    _, c = own(raw, plan())
    assert c["LANDFOLLOW"] == 1


def test_xref_landpin_and_base_over_not_relisted():
    raw = plan()
    raw["clock"]["landing_network"]["edges"][0]["dst"]["bus"] = "fclk_in_gone_i"
    _, c = own(raw, None)
    assert c["LANDPIN"] == 1
    far = plan(); far["partitions"][1]["origin_um"] = [1900.0, 0.0]
    _, c = own(copy.deepcopy(far), far)
    assert c["LANDHOP"] == 0                                                   # the same over-limit hop in BASE: counted only


def test_xref_tapkey_name_retarget():
    base = plan()
    base["partition_types"]["U"]["clock"]["added_taps"] = [{"name": "clk_t5", "xy": [20.0, 100.0]}]
    base["partition_types"]["U"]["clock"]["landing_contract"]["pins"][0]["source_clock_tap"] = "clk_t5"
    raw = copy.deepcopy(base)
    raw["partition_types"]["U"]["clock"]["added_taps"][0]["xy"] = [400.0, 100.0]
    _, c = own(raw, base)
    assert c["TAPKEY"] == 1


def test_xref_stagecnt(monkeypatch):
    class P:
        def __init__(self, raw, *a):
            self.lanes = {"L1": {}}

        def lane_latency(self, lid):
            return {"stations": 3}
    monkeypatch.setitem(sys.modules, "schema", types.SimpleNamespace(Plan=P))
    lines = SX.findings(plan(), None, forms=("STAGECNT",))
    assert SX.counts(lines)["STAGECNT"] == 1


def test_xref_bitcount_and_never_fail():
    raw = plan()
    raw["partition_types"]["T"]["ft_slots"][0]["bit_sites_um"].pop()
    lines = SX.findings(raw, None)
    assert SX.counts(lines)["BITCOUNT"] == 1 and not any(x.startswith("FAIL") for x in lines)


# ---- station_move (the helper) ---------------------------------------------------------------------------------------------

def test_remove_updates_bank_bits_latency_and_is_clean():
    base = plan(); raw = plan()
    rec = run(raw, [{"op": "remove", "type": "T", "slot": "ft4", "at": [400.0, 100.0]}])
    s = raw["partition_types"]["T"]["ft_slots"][0]
    assert s["stations"] == 3 and len(s["bit_sites_um"]) == 2
    sinks = sorted(x for r in raw["partition_types"]["T"]["reset"]["bank_taps"] for x in r["sinks"])
    assert sinks == ["u_ft_ft4_o_0", "u_ft_ft4_o_1", "u_ft_ft4_o_2"]
    assert raw["latency"]["lanes"]["L1"]["cycles"] == 9 and raw["latency"]["lanes"]["L1"]["stations"] == 3 and rec["lanes"] == {"L1": [10, 9]}
    # renumbered survivor (old station 3 at x=100) keeps its tap 4
    assert next(r["tap"] for r in raw["partition_types"]["T"]["reset"]["bank_taps"] if "u_ft_ft4_o_2" in r["sinks"]) == 4
    w, c = own(raw, base)
    assert w == [], w


def test_move_retaps_moves_bits_and_pins():
    base = plan(); raw = plan()
    run(raw, [{"op": "move", "type": "T", "slot": "ft4", "from": [700.0, 100.0], "to": [360.0, 100.0]},
              {"op": "move", "type": "T", "slot": "ft4", "from": [1000.0, 100.0], "to": [1000.0, 120.0]}])
    t = raw["partition_types"]["T"]
    assert next(r["tap"] for r in t["reset"]["bank_taps"] if "u_ft_ft4_o_1" in r["sinks"]) == 3        # nearest tap to 360
    assert t["ft_slots"][0]["bit_sites_um"][0] == _bits(360.0, 100.0)
    assert t["clock"]["landing_contract"]["pins"][0]["xy_um"] == [1000.0, 120.0]
    assert t["clock"]["edge_clocks"][0]["tap_um"] == [1000.0, 120.0]
    w, c = own(raw, base)
    assert c["BANKFOLLOW"] == 0 and c["BITFOLLOW"] == 0 and c["LANDFOLLOW"] == 0


def test_idempotent_all_ops():
    ops = [{"op": "move", "type": "T", "slot": "ft4", "from": [700.0, 100.0], "to": [690.0, 100.0]},
           {"op": "remove", "type": "T", "slot": "ft4", "at": [400.0, 100.0]},
           {"op": "reseat", "type": "T", "slot": "ft4", "sites": [[1000.0, 100.0], [690.0, 100.0], [100.0, 100.0]]}]
    raw = plan(); run(raw, ops)
    once = json.dumps(raw, sort_keys=True)
    rec = run(raw, ops)
    assert json.dumps(raw, sort_keys=True) == once and rec["slots"] == [] and rec["lanes"] == {}


def test_reseat_same_sites_is_byte_noop_and_grow_count():
    raw = plan(); ref = json.dumps(raw, sort_keys=True)
    run(raw, [{"op": "reseat", "type": "T", "slot": "ft4", "sites": plan()["partition_types"]["T"]["ft_slots"][0]["regs_um"]}])
    assert json.dumps(raw, sort_keys=True) == ref
    base = plan()
    run(raw, [{"op": "reseat", "type": "T", "slot": "ft4",
               "sites": [[1000.0, 100.0], [800.0, 100.0], [600.0, 100.0], [400.0, 100.0], [100.0, 100.0]]}])
    s = raw["partition_types"]["T"]["ft_slots"][0]
    assert s["stations"] == 5 and len(s["bit_sites_um"]) == 4 and raw["latency"]["lanes"]["L1"]["cycles"] == 11
    sinks = sorted(x for r in raw["partition_types"]["T"]["reset"]["bank_taps"] for x in r["sinks"])
    assert sinks == [f"u_ft_ft4_o_{k}" for k in range(5)]
    w, _ = own(raw, base)
    assert w == [], w


def test_refuses_without_tap_in_reach_and_last_station():
    raw = plan()
    with pytest.raises(SM.MoveError):
        SM.apply(raw, [{"op": "move", "type": "T", "slot": "ft4", "from": [700.0, 100.0], "to": [700.0, 900.0]}],
                 taps_fn=lambda r, t: {1: (0.0, 0.0)}, price_fn=price_fn)
    with pytest.raises(SM.MoveError):
        run(plan(), [{"op": "reseat", "type": "T", "slot": "ft4", "sites": []}])


def test_cli_writes_out_and_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(SM, "_default_taps", taps_fn)
    monkeypatch.setattr(SM, "default_price", lambda raw, plan_path=None: price_fn(raw))
    src = tmp_path / "p.json"; src.write_text(json.dumps(plan(), indent=1))
    ops = tmp_path / "ops.json"; ops.write_text(json.dumps([{"op": "remove", "type": "T", "slot": "ft4", "at": [400.0, 100.0]}]))
    out = tmp_path / "o.json"; rc_ = tmp_path / "r.json"
    monkeypatch.setitem(sys.modules, "schema", types.SimpleNamespace(Plan=lambda raw, *a: types.SimpleNamespace(lanes={})))
    assert SM.main([str(src), str(out), "--ops", str(ops), "--receipt", str(rc_)]) == 0
    assert json.loads(out.read_text())["partition_types"]["T"]["ft_slots"][0]["stations"] == 3
    assert json.loads(rc_.read_text())["lanes"] == {"L1": [10, 9]}


def test_xref_bankfollow_renumbered_end_station_kept_name_tap():
    """KV C2T ft4: 6 -> 4 keeps the END station's site, now named _3, but it kept old _3's tap instead of old _5's"""
    base = plan(); raw = plan()
    s = raw["partition_types"]["T"]["ft_slots"][0]
    s["regs_um"] = [s["regs_um"][0], s["regs_um"][1], s["regs_um"][3]]; s["bit_sites_um"] = [s["bit_sites_um"][0], s["bit_sites_um"][2]]
    s["stations"] = 3
    bt = raw["partition_types"]["T"]["reset"]["bank_taps"]
    bt[:] = [{"tap": 1, "sinks": ["u_ft_ft4_o_0"]}, {"tap": 2, "sinks": ["u_ft_ft4_o_1"]}, {"tap": 3, "sinks": ["u_ft_ft4_o_2"]}]
    w, c = own(raw, base)
    assert c["BANKFOLLOW"] == 1 and "site of BASE u_ft_ft4_o_3" in next(x for x in w if "BANKFOLLOW" in x)


def test_xref_crashed_form_says_err(monkeypatch):
    monkeypatch.setattr(SX, "check_tapkey", lambda raw, base: 1 / 0)
    lines = SX.findings(plan(), plan(), forms=("TAPKEY", "BANKSINK"))
    assert "TAPKEY=ERR" in lines[-1] and any("not checked (TAPKEY)" in x for x in lines)


TINY = HERE / "examples" / "tiny_plan.json"


def test_regen_derived_rewrites_copied_forward_package(tmp_path):
    import gen
    import latpkg_check as LP
    raw = json.loads(TINY.read_text())
    old = copy.deepcopy(raw); old["note"] = "the plan before the station move"
    gen.write_latency(old, tmp_path / "lat")                     # copied-forward package of the old plan
    (tmp_path / "plan.json").write_text(json.dumps(raw))
    assert LP.read_package(tmp_path / "lat" / "tiny_latency.json")["digest"] != gen.plan_digest(raw)
    rg = SM.regen_derived(raw, tmp_path / "plan.json", tree=tmp_path)
    assert {Path(f["path"]).name for f in rg["files"]} == {"tiny_latency.json", "tiny_lat_pkg.sv"} and not rg["stale_after"]
    for n in ("tiny_latency.json", "tiny_lat_pkg.sv"):
        assert LP.read_package(tmp_path / "lat" / n)["digest"] == gen.plan_digest(raw)
    assert "stale=0" in rg["latpkg"][-1]
    assert SM.regen_derived(raw, tmp_path / "plan.json", tree=tmp_path)["files"] == []     # idempotent: nothing stale, nothing written


def test_regen_derived_leaves_packages_outside_plan_dir(tmp_path):
    import gen
    raw = json.loads(TINY.read_text())
    old = copy.deepcopy(raw); old["note"] = "old"
    (tmp_path / "die" / "prep").mkdir(parents=True)
    gen.write_latency(old, tmp_path / "die" / "lat")               # an ancestor's lat/: reported, never rewritten unasked
    before = (tmp_path / "die" / "lat" / "tiny_latency.json").read_text()
    (tmp_path / "die" / "prep" / "plan.json").write_text(json.dumps(raw))
    rg = SM.regen_derived(raw, tmp_path / "die" / "prep" / "plan.json", tree=tmp_path)
    assert rg["files"] == [] and (tmp_path / "die" / "lat" / "tiny_latency.json").read_text() == before


def test_regen_schedule_receipt_and_pkg(tmp_path, monkeypatch):
    sys.path.insert(0, str(HERE.parent / "s81_head"))
    import regen_schedule_constants as RS
    monkeypatch.setattr(RS, "head_transport", lambda lats: dict(total_cycles=sum(lats.values())))
    raw = json.loads(TINY.read_text()); raw["die"]["name"] = "s81_head"
    (tmp_path / "plan.json").write_text(json.dumps(raw))
    old = RS.generate(raw); old["lanes"]["x"]["cycles"] = old["lanes"]["x"]["raw_cycles"] = 3
    old["inputs"] = dict(plan="old.json", plan_sha256="0" * 64, ca=None)
    rc = tmp_path / "nf_schedule.json"; rc.write_text(json.dumps(old))
    (tmp_path / "nf_pkg.sv").write_text("package s81_head_sched_pkg;\nendpackage\n")
    row = SM.regen_schedule(raw, tmp_path / "plan.json", rc)
    new = json.loads(rc.read_text())
    assert row["changed"] == ["x"] and new["lanes"]["x"]["cycles"] == 8
    assert new["inputs"]["plan_sha256"] == SM.hashlib.sha256((tmp_path / "plan.json").read_bytes()).hexdigest()
    assert "LAT_X = 8;" in (tmp_path / "nf_pkg.sv").read_text()
    old["inputs"]["landed_sidecar_sha256"] = "1" * 64; rc.write_text(json.dumps(old))
    with pytest.raises(SM.MoveError, match="landed-sidecar"):
        SM.regen_schedule(raw, tmp_path / "plan.json", rc)
