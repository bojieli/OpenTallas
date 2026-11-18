"""tests for tools/die_plan/tail_repl.py (TAIL-REPL 11-17): python3 -m pytest tools/die_plan/test_tail_repl.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tail_repl as T  # noqa: E402


def core(inst, x, y, w=100, h=100):
    return dict(inst=inst, origin_um=[x, y], outline_um=[w, h])


def test_config_absent_and_defaults():
    assert T.config({}) == {}
    assert T.config({"tail_repl": {"types": ["a", "b"]}}) == {"a": (400.0, 200.0), "b": (400.0, 200.0)}
    assert T.config({"tail_repl": {"types": ["a"], "min_spread_um": 250, "cluster_um": 90}}) == {"a": (250.0, 90.0)}


def test_config_rejects_bad():
    with pytest.raises(ValueError):
        T.config({"tail_repl": {"types": []}})
    with pytest.raises(ValueError):
        T.config({"tail_repl": {"types": ["a"], "cluster_um": 0}})


def test_centers_and_spread():
    c = T.centers([core("a", 0, 0), core("b", 600, 100)])
    assert c == {"a": (50, 50), "b": (650, 150)}
    assert T.spread(list(c.values())) == 700


def test_close_cores_not_replicated():
    c = T.centers([core("a", 0, 0), core("b", 150, 0), core("c", 0, 150)])
    assert T.decide(c, 400, 200) is None


def test_spread_cores_one_copy_per_cluster():
    c = T.centers([core("a", 0, 0), core("b", 120, 0), core("c", 1000, 0), core("d", 1100, 0), core("e", 0, 900)])
    d = T.decide(c, 400, 200)
    assert d["a"] == d["b"] and d["c"] == d["d"]
    assert len({d["a"], d["c"], d["e"]}) == 3


def test_one_big_cluster_stays_shared():
    c = T.centers([core("a", 0, 0), core("b", 150, 0), core("c", 300, 0), core("d", 450, 0)])
    assert T.decide(c, 400, 1000) is None


def test_single_consumer_never_replicated():
    assert T.decide({"a": (0, 0)}, 0, 10) is None


def test_binder_plan_groups_sinks_by_chain():
    """Binder._tail_repl_plan on a stub: bit 0 of in-bus `x_i` padded 3 feeds cores c0..c3 (two far clusters) and a
    non-core cell; only the core sinks get a cluster, a close pair is left shared"""
    import types
    import bind
    cores = [core("c0", 0, 0), core("c1", 100, 0), core("c2", 2000, 0), core("c3", 2100, 0), core("near", 0, 50)]
    t = dict(hard_cores=cores)
    L = dict(iname="x_i")
    names = {1: "u_c0", 2: "c1", 3: "u_c2", 4: "c3", 5: "glue"}
    d = lambda: ("x", "A0", "o", 0, 0, 0, "P", 3)
    sinks = {(ci, "p", 0): d() for ci in names}
    sinks[(2, "q", 0)] = ("or", (d(),))             # nested in an OR tree: still counted
    st = types.SimpleNamespace(ab={"tail_repl": {"types": ["T"]}}, members={"P": list(names)}, sinks=sinks,
                               cpart={ci: "P" for ci in names}, rel_of=lambda ci: names[ci],
                               bitpos={("A0", "P", "o", 0, 0): (L, 0)})
    out = bind.Binder._tail_repl_plan(st, "P", "T", t)
    assert set(out) == {("x_i", 0, 3)}
    m = out[("x_i", 0, 3)]
    assert set(m) == {1, 2, 3, 4} and m[1] == m[2] != m[3] == m[4]
    assert st.tail_repl_stats["replicated"] == 1 and st.tail_repl_stats["copies"] == 2
    # other type or no key: nothing
    assert bind.Binder._tail_repl_plan(st, "P", "other", t) == {}
    st.ab = {}
    assert bind.Binder._tail_repl_plan(st, "P", "T", t) == {}


def test_bind_emits_tail_copy_same_latency(tmp_path, monkeypatch):
    """end to end on bind_tiny (needs Yosys): land_align pads of snk.d0 (3 stages); with tail_repl forced to split the single
    consumer, the pad becomes shared D-1 prefix + one 1-stage tail copy, the proof and the as-built latency are unchanged"""
    import json
    import shutil
    import os
    if not (os.environ.get("OT_BIND_YOSYS") or shutil.which("docker")):
        pytest.skip("no Yosys")
    import bind
    import test_bind as TB

    def edit(p):
        p["asbuilt"]["land_align"] = "cell"
        p["asbuilt"]["tail_repl"] = {"types": ["ts"], "min_spread_um": 0, "cluster_um": 1}
        p["partition_types"]["ts"]["hard_cores"] = [dict(inst="core", origin_um=[0, 0], outline_um=[10, 10])]
        for x in p["ports"]:
            if x["id"] == "a0s__0":
                x["width"] = 5
            if x["id"] == "a1s__0":
                x["width"] = 16
        for b in p["partition_types"]["ta"]["buses"]:
            if b["name"] == "ys_o":
                b["width"] = 16
        for b in p["partition_types"]["ts"]["buses"]:
            if b["name"] == "d1_i":
                b["width"] = 16
    monkeypatch.setattr(T, "decide", lambda cons, ms, cl: {k: 0 for k in cons})
    out = tmp_path / "o"
    assert TB.run(TB.plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0, \
        TB.report(out)["errors"][:5]
    r = TB.report(out)
    assert r["lanes"]["tail_repl"]["replicated"] == 5 and r["lanes"]["tail_repl"]["copies"] == 5
    ts = (out / "rtl" / "bt_ts.sv").read_text()
    assert ts.count("TAIL-REPL: last pad stage copy") == 5
    assert "ot_dp_dly #(.W(1), .D(2))" in ts and "ot_dp_dly #(.W(1), .D(3))" not in ts
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert {sinks[f"snk.d0[{i}]"][2] for i in range(8)} == {5}
    assert TB.verify(out)["verdict"] == "PASS"
