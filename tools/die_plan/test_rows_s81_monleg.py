"""rows_s81_monleg + plan_gate_pre MONLEG-REACH: stale child node -> same-depth tap at the seam output, 0 cycles."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_gate_pre as G  # noqa: E402
import rows_s81_monleg as M  # noqa: E402


def _plan():
    relays = [dict(d="rst_root_n", depth=1, kind="pad", name="u_rrl_0", q="rst_rl_0", tap=0, xy=[50.0, 50.0])]
    taps = {0: [50.0, 50.0], 1: [1300.0, 50.0], 2: [8.0, 640.0], 3: [1300.0, 1270.0]}
    for k, xy in taps.items():
        relays.append(dict(d="rst_rl_0", depth=2, kind="tap", name=f"u_rrl_{k + 1}", q=f"rst_n_t{k}", tap=k, xy=xy))
    ct = dict(relays=relays, root=[0.0, 0.0], outs=[[1300.0, 50.0], [8.0, 640.0]], n_reset_consumers=1, own_depth=2, depth=2)
    lc = dict(collector_tree=ct, collector_root_node="rst_root_n", collector_local_sources=[dict(name="s", tap=0)],
              collector_children=[dict(index=0, node="rst_n_t3", part="a", seam=True, xy_um=[8.0, 640.0]),
                                  dict(index=1, node="rst_n_t1", part="b", seam=True, xy_um=[1300.0, 50.0])],
              bands=dict(monitor_0=dict(rect_um=[17.0, 470.0, 26.0, 498.0]), monitor_1=dict(rect_um=[1300.0, 17.0, 1309.0, 45.0])))
    return dict(partition_types=dict(T=dict(clock=dict(landing_contract=lc))), die="x")


def test_census_and_fix():
    p = _plan()
    c = M.census(p)
    assert (c["pairs"], c["over_reach"], c["over_fail"]) == (2, 1, 1)
    rep, ch = M.apply(p)
    assert ch == {("T", 0): "rst_n_t2"} and rep["after"]["over_reach"] == 0
    assert rep["max_child_cycles_added"] == 0 and rep["boot_depth_added_cycles"] == {"T": 0}
    ch1 = p["partition_types"]["T"]["clock"]["landing_contract"]["collector_children"]
    assert [x["node"] for x in ch1] == ["rst_n_t2", "rst_n_t1"]


def test_only_node_changes_and_idempotent():
    p = _plan()
    q = copy.deepcopy(p)
    M.apply(q)
    for x, y in zip(p["partition_types"]["T"]["clock"]["landing_contract"]["collector_children"],
                    q["partition_types"]["T"]["clock"]["landing_contract"]["collector_children"]):
        assert {k: v for k, v in x.items() if k != "node"} == {k: v for k, v in y.items() if k != "node"}
    rep, ch = M.apply(q)
    assert not ch and rep["changed_pairs"] == 0


def test_deeper_fallback_and_unfixed():
    p = _plan()
    lc = p["partition_types"]["T"]["clock"]["landing_contract"]
    for r in lc["collector_tree"]["relays"]:
        if r["q"] == "rst_n_t2":
            r["depth"] = 3
    rep, ch = M.apply(p)
    assert ch[("T", 0)] == "rst_n_t2" and rep["types"]["T"][0]["cycles_added"] == 1
    p2 = _plan()
    p2["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]["relays"] = [
        r for r in p2["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]["relays"] if r["q"] != "rst_n_t2"]
    rep, ch = M.apply(p2)
    assert not ch and len(rep["unfixed"]) == 1


def test_sidecar_and_cli(tmp_path):
    p = _plan()
    pin, pout, sin, sout = (str(tmp_path / n) for n in ("p.json", "o.json", "s.json", "so.json"))
    open(pin, "w").write(json.dumps(p, indent=1) + "\n")
    sc = dict(collector=dict(types=dict(T=dict(children=[dict(index=0, node="rst_n_t3"), dict(index=1, node="rst_n_t1")]))))
    open(sin, "w").write(json.dumps(sc, indent=1) + "\n")
    assert M.main([pin, pout, "--sidecar-in", sin, "--sidecar-out", sout]) == 0
    assert json.load(open(sout))["collector"]["types"]["T"]["children"][0]["node"] == "rst_n_t2"
    out = json.load(open(pout))
    assert out["partition_types"]["T"]["clock"]["landing_contract"]["collector_children"][0]["node"] == "rst_n_t2"
    assert M.main([pin, pout + "2", "--strict", "--types=none"]) == 0


def test_precheck_report_only(tmp_path):
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(_plan()))
    out = G.check_monleg(str(f))
    assert out and all(x.startswith("WARN MONLEG-REACH") for x in out)
    assert "1 of 2 pairs on 1 types" in out[-1]
    f.write_text(json.dumps(M.apply(_plan())[0] and (lambda q: (M.apply(q), q)[1])(_plan())))
    assert G.check_monleg(str(f)) == []
    assert "MONLEG" in G.CLASSES


def test_src_form_ops_and_old_check():
    p = _plan()
    lc = p["partition_types"]["T"]["clock"]["landing_contract"]
    lc["collector_local_sources"] = [dict(name="s0", node="rst_n_t3", tap=3, xy_um=[8.0, 640.0],
                                          band=dict(rect_um=[17.0, 470.0, 26.0, 498.0]))]
    import copy
    base = copy.deepcopy(p)
    assert M.src_census(p)["over_reach"] == 1
    rep, ops = M.apply_src(p)
    assert rep["changed"] == 1 and rep["after"] == 0 and M.check_ops(base, ops) == 0
    assert [o["value"] for o in ops] == ["rst_n_t2", 2]


def test_precheck_src_report_only(tmp_path):
    p = _plan()
    lc = p["partition_types"]["T"]["clock"]["landing_contract"]
    lc["collector_local_sources"] = [dict(name="s0", node="rst_n_t3", tap=3, xy_um=[8.0, 640.0],
                                          band=dict(rect_um=[17.0, 470.0, 26.0, 498.0]))]
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(p))
    out = G.check_monleg(str(f))
    assert any(x.startswith("WARN MONLEG-REACH-SRC T:") for x in out)
    assert any("MONLEG-REACH-SRC-SUMMARY 1 sources on 1 types" in x for x in out)
    assert all(x.startswith("WARN ") for x in out)


def test_src_relay_insertion_cli(tmp_path):
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    relays = [dict(d="rst_root_n", depth=1, kind="tap", name="u_rrl_0", q="rst_n_t0", tap=0, xy=[10.0, 10.0])]
    ct = dict(relays=relays, root=[0.0, 0.0], outs=[], n_reset_consumers=1, depth=1, own_depth=1)
    src = dict(name="s0", ready="r", fault="f", tap=0, node="rst_n_t0", xy_um=[900.0, 900.0], pin_xy_um=[900.0, 900.0],
               band=dict(rect_um=[890.0, 890.0, 910.0, 910.0]))
    lc = dict(collector_tree=ct, collector_root_node="rst_root_n", collector_local_sources=[src], collector_children=[], bands={})
    plan = dict(partition_types=dict(T=dict(outline_um=[1000.0, 1000.0], hard_cores=[], clock=dict(landing_contract=lc))))
    pin, pout, rep = str(tmp_path / "i.json"), str(tmp_path / "o.json"), str(tmp_path / "r.json")
    open(pin, "w").write(json.dumps(plan))
    r = subprocess.run([sys.executable, "-I", os.path.join(here, "rows_s81_monleg_src.py"), pin, pout, "--json", rep],
                       env=dict(RC_DRY="1"), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    out = json.load(open(pout))
    lc2 = out["partition_types"]["T"]["clock"]["landing_contract"]
    s2 = lc2["collector_local_sources"][0]
    assert s2["node"].startswith("rst_cx_") and "tap" not in s2
    assert "status_from_band" not in s2 and s2["xy_um"] == [900.0, 900.0]      # no extra key; status point = band centre
    R = {x["q"]: x for x in lc2["collector_tree"]["relays"]}
    assert R[s2["node"]]["kind"] == "cland_copy" and R[s2["node"]]["depth"] > 1      # longer, never shorter
    chain = s2["node"]
    prev = R[chain]["d"]
    assert M.src_census(out)["over_reach"] == 0
    assert all(M.man(R[q]["xy"], R[R[q]["d"]]["xy"]) <= 405.0 + 1e-6 for q in [s2["node"]] + [prev] if R[q]["d"] in R)
