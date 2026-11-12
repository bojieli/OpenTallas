"""reach_fix.py (REACH-FIX-1, OWNER 11-12): one failing fixture per class that the tool fixes, plus idempotency."""
import copy
import json
import sys
import types as _t
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import reach_fix as RF  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _write(tmp_path, plan, name="plan.json"):
    p = tmp_path / name
    p.write_text(json.dumps(plan))
    return p


def _rows(tmp_path, plan_path):
    out = tmp_path / ("chk_%s.json" % plan_path.stem)
    assert RF.main(["check", str(plan_path), "--json", str(out)]) == 0
    return {r["type"]: r for r in json.loads(out.read_text())["rows"]}


def _fix(tmp_path, plan_path, tag, *extra):
    out, ev = tmp_path / ("%s.json" % tag), tmp_path / ("%s_event.json" % tag)
    assert RF.main(["fix", str(plan_path), "--out-plan", str(out), "--event", str(ev)] + list(extra)) == 0
    return out, json.loads(ev.read_text())


def test_class1_tap_radius_fixed(tmp_path):
    # tiny_plan: 864-um types on the 400-um R4 grid: face registers 261.5 um from their tap (plan_geom fixture)
    base = _write(tmp_path, EX)
    before = _rows(tmp_path, base)
    assert before["mid"]["c1"] > 0 and before["mid"]["c1_max_um"] > RF.RADIUS_UM
    out, ev = _fix(tmp_path, base, "f1")
    after = _rows(tmp_path, out)
    assert all(r["c1"] == 0 for r in after.values()), {k: (r["c1"], r.get("error")) for k, r in after.items()}
    ck = json.loads(out.read_text())["partition_types"]["mid"]["clock"]
    assert ck["tap_mode"] == "grid+explicit" and ck["added_taps"]            # the R4 grid kept, taps added
    assert ev["summary_after"]["c1_types"] == 0 < ev["summary_before"]["c1_types"]


def test_class2_tap_load_split(tmp_path):
    p = copy.deepcopy(EX)
    ck = p["partition_types"]["mid"]["clock"]
    # 6,000 sinks in one 60 x 60 um block: more than the grid taps in reach can take at the cap
    ck["sink_sites_um"] = [[300.0 + 6.0 * i, 300.0 + 6.0 * j, 20.0] for i in range(10) for j in range(10)]
    ck["sink_sites_um"] = [r[:2] + [60.0] for r in ck["sink_sites_um"]]
    base = _write(tmp_path, p)
    b = _rows(tmp_path, base)["mid"]
    assert b["c2"] >= 1 and b["c2_max"] > RF.CAP_SINKS
    out, _ev = _fix(tmp_path, base, "f2")
    a = _rows(tmp_path, out)["mid"]
    assert a["c2"] == 0 and a["c2_max"] <= RF.CAP_SINKS and a["c1"] == 0, a
    import schema as S
    fixed = json.loads(out.read_text())
    assert S.validate_structure(fixed) == []                         # only schema keys (no stray clock keys)


def test_class4_signal_hop_gets_registers(tmp_path):
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["ft_slots"][0]["stations"] = 1       # one 864-um hop W -> E
    base = _write(tmp_path, p)
    b = _rows(tmp_path, base)["mid"]
    assert b["c4"] == 1 and b["c4_max_um"] > RF.REACH_UM
    out, ev = _fix(tmp_path, base, "f4", "--classes", "4")
    a = _rows(tmp_path, out)["mid"]
    assert a["c4"] == 0 and a["c4_max_um"] <= RF.REACH_UM
    slot = json.loads(out.read_text())["partition_types"]["mid"]["ft_slots"][0]
    assert slot["stations"] == 3                                     # ceil(864 / 405)
    assert ev["cycles_added"]["mid"] == 2                            # owner-approved cycles reported per type


def test_idempotent(tmp_path):
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["ft_slots"][0]["stations"] = 1
    out1, _ = _fix(tmp_path, _write(tmp_path, p), "i1")
    out2, ev2 = _fix(tmp_path, out1, "i2")
    assert ev2["applied"] == 0 and ev2["summary_before"]["types_viol"] == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_class3_forwarded_clock_split(monkeypatch):
    t = {"outline_um": [2400.0, 400.0], "hard_cores": [],
         "clock": {"edge_clocks": [{"port": "fclk_in_x", "tap_um": [10.0, 200.0]}],
                   "landing_contract": {"pins": [{"name": "fclk_in_x", "dir": "in", "kind": "clock",
                                                  "xy_um": [2.16, 200.0]}],
                                        "bands": {"x": {"rect_um": [2100.0, 150.0, 2200.0, 250.0],
                                                        "instance": "u_cland_x"}}}}}
    P = _t.SimpleNamespace(types={"T": t}, path=None)
    rows = RF.fwd_metrics(P, "T")
    assert rows and not rows[0]["ok"] and rows[0]["far_um"] > RF.REPEATER_UM
    Q = {"partition_types": {"T": copy.deepcopy(t)}}
    assert [r["port"] for r in RF.fix_fwd(P, Q, "T")] == ["fclk_in_x"]
    P2 = _t.SimpleNamespace(types=Q["partition_types"], path=None)
    assert RF.fwd_metrics(P2, "T")[0]["ok"]
    assert RF.fix_fwd(P2, copy.deepcopy(Q), "T") == []                   # idempotent
    # the kit consumer: gen_phys.edge_split_ports names the forwarded port on a die outside EDGE_SPLIT_DIES
    import gen_phys as GP
    P3 = _t.SimpleNamespace(types=Q["partition_types"], die={"name": "s81"}, grid=None, layers=None)
    monkeypatch.setattr(GP, "edge_clock_pins", lambda PP, tn: [("fclk_in_x", 10.0, 200.0, 1)])
    assert GP.edge_split_ports(P3, "T") == ["fclk_in_x"]


def test_class5_raw_tap_reference_reselected(monkeypatch):
    import reset_tree
    trees = {
        "base": dict(relays=[dict(name="u_rrl_3", q="rst_n_t3", d="rst_root_n", depth=2, xy=[100.0, 50.0]),
                             dict(name="u_rrl_5", q="rst_n_t5", d="rst_root_n", depth=2, xy=[900.0, 50.0])]),
        "new": dict(relays=[dict(name="u_rrl_3", q="rst_n_t3", d="rst_root_n", depth=2, xy=[900.0, 50.0]),
                            dict(name="u_rrl_5", q="rst_n_t5", d="rst_root_n", depth=2, xy=[110.0, 50.0]),
                            dict(name="u_rrl_6", q="rst_n_t6", d="rst_root_n", depth=3, xy=[100.0, 50.0])]),
    }
    monkeypatch.setattr(RF, "plan_obj", lambda raw, path: _t.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(RF, "_reset_caches", lambda PQ: None)
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])
    st = dict(raw_reset="rr_t3", xy_um=[100.0, 50.0])
    t = {"clock": {"landing_reader_start": {"branches": {"b": {"stages": [st]}}}}}
    P = _t.SimpleNamespace(tag="base")
    Q = {"tag": "new", "partition_types": {"x": t}}
    rec = RF.fix_raw_tap_refs(P, Q, "x", None)
    assert rec == [["landing_reader_start.b.0", "rr_t3", "rr_t5"]]          # same depth, nearest
    assert st["raw_reset"] == "rr_t5"
    assert RF.fix_raw_tap_refs(P, Q, "x", None) == []                        # idempotent
