"""DIE-QC-15: parent_trunk_dme.py (opt-in shared parent-tile trunk planner, upstream of DIE-QC-14 trunk2.py).

Small synthetic tile: 2 macro columns (MY left / R0 right) with a pin-offset child module, 2 fixed-pin children and
glue clusters.  Checks the structural contract (even parity, no repeater inside a macro, bounded segments, balance by
wire length instead of stage stacks), the measured re-balance (corr), the tcl emit, fail-closed inputs and byte
identity with the lane planner it replaces."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import parent_trunk_dme as PT

HERE = Path(__file__).resolve().parent
LANE = HERE.parents[1] / "results/die_qc14_1028/a0trunk/trunk2.py"


def _fixture(tmp, orient=False):
    macros = [[20.0, 100.0, 120.0, 220.0], [200.0, 100.0, 300.0, 220.0],
              [20.0, 300.0, 120.0, 420.0], [200.0, 300.0, 300.0, 420.0]]
    kids = [dict(inst="u_rl0", module="mod_rl", pin=[70.0, 160.0]), dict(inst="u_rl1", module="mod_rl", pin=[250.0, 160.0]),
            dict(inst="u_n0", module="mod_n", pin=[70.0, 360.0]), dict(inst="u_n1", module="mod_n", pin=[250.0, 360.0])]
    if orient:
        kids[0]["orient"] = "MY"; kids[1]["orient"] = "R0"
    clusters = [dict(name="cl%d" % i, n=100, root=r, box=[0, 0, 0, 0], regs=[])
                for i, r in enumerate([[160.0, 60.0], [160.0, 260.0], [160.0, 470.0], [40.0, 260.0], [330.0, 470.0]])]
    G = dict(W=340.0, H=520.0, macros=macros, kids=kids, clusters=clusters)
    ins = {c["name"]: dict(TT=dict(mean=80.0 + 3 * i), FF=dict(mean=62.0 + 2 * i)) for i, c in enumerate(clusters)}
    g = tmp / "geom.json"; g.write_text(json.dumps(G))
    c = tmp / "ins.json"; c.write_text(json.dumps(ins))
    return g, c, G


CI = "mod_rl=250/202.5,mod_n=250/202.5"


def _plan(tmp, extra=(), orient=False):
    g, c, G = _fixture(tmp, orient)
    out = tmp / "plan.json"
    args = ["plan", str(g), str(c), str(out), "--entry", "160,250", "--child-ins", CI] + list(extra)
    if not orient:
        args += ["--pin-offset", "mod_rl=10,5", "--orient-rule", "150"]
    PT.main(args)
    return json.loads(out.read_text()), G, out


@pytest.fixture(scope="module")
def planned(tmp_path_factory):
    return _plan(tmp_path_factory.mktemp("pt"))


def test_plan_structure(planned):
    P, G, _ = planned
    s = P["summary"]
    assert s["sinks"] == 9 and s["odd_parity_sinks"] == []
    for i in P["insts"]:                     # no trunk inverter inside a macro (1 um halo)
        x, y = i["p"]
        assert not any(m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1 for m in G["macros"]), i
    # sp*sp_max is the planning target; legalising a repeater out of a macro can stretch a segment beyond it
    # (A0 nk q4: 158.8 um, routed max clock slew 135 ps << 320), so the hard bound checked here is 2*sp
    lim = 2.0 * s["sp"]

    def legs(nd):
        if nd["kind"] == "merge":
            for kid, lg in zip(nd["kids"], nd["legs"]):
                assert all(PT.man(u, v) <= lim for u, v in zip(lg["pts"], lg["pts"][1:])), lg
                legs(kid)
    legs(P["tree"])
    # the tree is balanced by the plan model (wire length, not stage stacks)
    assert s["plan_tt"]["spread"] <= 30.0 and s["plan_ff"]["spread"] <= 30.0
    assert s["short_stage_pairs_lt8um"] <= 1


def test_pin_offset_orientation(planned, tmp_path):
    P, G, _ = planned
    ch = {k["name"]: k["p"] for k in P["sinks"] if k["kind"] == "child"}
    assert ch["u_rl0"] == [110.0, 105.0]          # MY: x1 - dx
    assert ch["u_rl1"] == [210.0, 105.0]          # R0: x0 + dx
    assert ch["u_n0"] == [70.0, 360.0]            # no offset: geometry pin
    # explicit per-kid orientation gives the same pins
    P2, _, _ = _plan(tmp_path, ["--pin-offset", "mod_rl=10,5"], orient=True)
    assert {k["name"]: k["p"] for k in P2["sinks"] if k["kind"] == "child"} == ch


def test_elongation_not_stacks(tmp_path):
    """two close sinks 60 ps apart in insertion: the tap point alone cannot balance them, so the fast leg is lengthened
    by wire (bridge polyline), not by a stage stack"""
    G = dict(W=600.0, H=600.0, macros=[], kids=[dict(inst="k0", module="mod_n", pin=[300.0, 330.0])],
             clusters=[dict(name="far", n=10, root=[300.0, 350.0], box=[], regs=[])])
    (tmp_path / "g.json").write_text(json.dumps(G))
    (tmp_path / "i.json").write_text(json.dumps({"far": dict(TT=dict(mean=80.0), FF=dict(mean=60.0))}))
    PT.main(["plan", str(tmp_path / "g.json"), str(tmp_path / "i.json"), str(tmp_path / "o.json"), "--entry", "300,300",
             "--child-ins", "mod_n=20/15"])
    s = json.loads((tmp_path / "o.json").read_text())["summary"]
    assert s["elongated_legs"] >= 1 and s["elongation_um"] > 50
    assert s["plan_tt"]["spread"] <= 10.0 and s["odd_parity_sinks"] == [] and s["short_stage_pairs_lt8um"] == 0


def _arrivals(P, tmp, bump=None):
    """synthetic measured file in the kit's meas format from the plan arrivals (+ bump ps on one sink)"""
    lines = []
    for k in P["sinks"]:
        a = P["arrival_plan"][k["name"]]["tt"] + (bump[1] if bump and bump[0] == k["name"] else 0.0)
        if k["kind"] == "cluster":
            for j in range(3):
                lines.append("S r_%s_%d/CLK DFFHQNx1_ASAP7_75t_R clknet_leaf_%d_%s %.3f %.3f %.3f" % (k["name"], j, j, k["name"], a, a + 416.5, a))
        else:
            mod = "mod_rl" if k["name"].startswith("u_rl") else "mod_n"
            lines.append("S %s/clk %s %s %.3f %.3f %.3f" % (k["name"], mod, k["net"], a - 250.0, a + 166.5, a - 250.0))
    lines.append("S a0t_icg/CLK ICGx8DC_ASAP7_75t_R ck 0 416.5 0")
    f = tmp / "arr.txt"; f.write_text("\n".join(lines) + "\n")
    return f


def test_corr_rebalances(planned, tmp_path):
    P, G, out = planned
    f = _arrivals(P, tmp_path, bump=("cl0", -40.0))      # cl0 measured 40 ps early
    o = tmp_path / "corr.json"
    PT.main(["corr", str(out), str(f), str(o)])
    C = json.loads(o.read_text())
    s = C["summary"]
    assert s["iteration"] == 1 and s["legs_lengthened"] >= 1 and s["added_delay_ps"] > 10
    assert s["odd_parity_sinks"] == []
    # topology unchanged: same sinks, same merge count
    assert [k["name"] for k in C["sinks"]] == [k["name"] for k in P["sinks"]]
    assert sum(1 for i in C["insts"] if "_m" in i["name"]) == sum(1 for i in P["insts"] if "_m" in i["name"])


def test_corr_fail_closed(planned, tmp_path):
    P, G, out = planned
    f = _arrivals(P, tmp_path)
    txt = [l for l in f.read_text().splitlines() if "_cl3" not in l]
    f.write_text("\n".join(txt) + "\n")
    with pytest.raises(ValueError, match="no measured registers for cluster cl3"):
        PT.main(["corr", str(out), str(f), str(tmp_path / "x.json")])
    with pytest.raises(ValueError, match="differs from the plan"):
        PT.main(["corr", str(out), str(_arrivals(P, tmp_path)), str(tmp_path / "x.json"), "--sp", "90"])


def test_plan_fail_closed(tmp_path):
    g, c, G = _fixture(tmp_path)
    o = str(tmp_path / "o.json")
    with pytest.raises(ValueError, match="without a --child-ins budget"):
        PT.main(["plan", str(g), str(c), o, "--entry", "160,250", "--child-ins", "mod_n=250/202.5"])
    with pytest.raises(ValueError, match="needs an orientation"):
        PT.main(["plan", str(g), str(c), o, "--entry", "160,250", "--child-ins", CI, "--pin-offset", "mod_rl=10,5"])
    ins = json.loads(c.read_text()); ins.pop("cl2"); c.write_text(json.dumps(ins))
    with pytest.raises(ValueError, match="cluster insertion missing"):
        PT.main(["plan", str(g), str(c), o, "--entry", "160,250", "--child-ins", CI])


def test_tcl_emit(planned, tmp_path):
    P, G, out = planned
    t = tmp_path / "t.tcl"
    PT.main(["tcl", str(out), str(t)])
    lines = t.read_text().splitlines()
    assert lines[0].startswith("set ICG [list ")
    assert sum(1 for l in lines if l.startswith("lappend TI ")) == P["summary"]["n_inv"]
    assert sum(1 for l in lines if l.startswith("lappend TS ")) == P["summary"]["sinks"]


def test_insert_tcl_present():
    s = (HERE / "parent_trunk_insert.tcl").read_text()
    for k in ("ROOT_SUFFIX", "CHILD_PIN", "detailed_placement", "check_placement", "write_db"):
        assert k in s


@pytest.mark.skipif(not LANE.is_file(), reason="lane planner results/die_qc14_1028 not in this checkout")
def test_byte_identical_to_lane_planner(tmp_path):
    """the shared tool reproduces the DIE-QC-14 lane planner (trunk2.py) byte for byte (plan + corr) on the same inputs;
    on the real A0 nk inputs the whole q0 -> q4 chain was checked identical (DIE-QC-15 README)"""
    g, c, G = _fixture(tmp_path)
    tab = tmp_path / "stage_table.json"; tab.write_text(PT.DEFAULT_TABLE.read_text())
    # the lane planner hard-codes the romleaf module name and the x0 < 200 MY rule
    for k in G["kids"]:
        k["module"] = {"mod_rl": "ot_qwen_tile_romleaf", "mod_n": "ot_qwen_tile_node"}[k["module"]]
    g.write_text(json.dumps(G))
    ci = "ot_qwen_tile_lsl_rawfault_m3=250/202.5,ot_qwen_tile_node=250/202.5,ot_qwen_tile_romleaf=250/202.5"
    subprocess.run([sys.executable, "-I", str(LANE), "plan", "t", "geom.json", "ins.json", "lane.json", "--entry", "160,250",
                    "--romleaf-pin", "10,5", "--child-ins", ci], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run([sys.executable, "-I", str(HERE / "parent_trunk_dme.py"), "plan", "geom.json", "ins.json", "shared.json",
                    "--entry", "160,250", "--pin-offset", "ot_qwen_tile_romleaf=10,5", "--orient-rule", "200",
                    "--child-ins", ci], cwd=tmp_path, check=True, capture_output=True)
    assert (tmp_path / "lane.json").read_bytes() == (tmp_path / "shared.json").read_bytes()


# ---------------------------------------------------------------- DIE-QC-17: opt-in balanced top-down bipartition
def test_default_topology_is_greedy(tmp_path):
    """--topology greedy (the default) is the DIE-QC-15 planner: same bytes with or without the flag, no new keys"""
    P0, _, o0 = _plan(tmp_path)
    b0 = o0.read_bytes()
    P1, _, o1 = _plan(tmp_path, ["--topology", "greedy"])
    assert o1.read_bytes() == b0
    assert "topology" not in P1["summary"] and "plan_ocv" not in P1["summary"]


def _far_singleton(tmp, regs=False):
    """A0 nl failure shape: a dense glue field + a 1-register cluster far at the N edge + children in two columns"""
    macros = [[40.0, 60.0, 140.0, 160.0], [300.0, 60.0, 400.0, 160.0]]
    kids = [dict(inst="k0", module="mod_n", pin=[90.0, 110.0]), dict(inst="k1", module="mod_n", pin=[350.0, 110.0])]
    roots = [[180.0 + 30 * (i % 4), 220.0 + 30 * (i // 4)] for i in range(8)] + [[220.0, 760.0]]
    clusters = [dict(name="c%d" % i, n=10, root=r, box=[], regs=(["r_c%d_%d" % (i, j) for j in range(3)] if regs else []))
                for i, r in enumerate(roots)]
    G = dict(W=440.0, H=800.0, macros=macros, kids=kids, clusters=clusters)
    ins = {c["name"]: dict(TT=dict(mean=70.0 + 4 * (i % 3)), FF=dict(mean=55.0 + 3 * (i % 3))) for i, c in enumerate(clusters)}
    ins["c8"] = dict(TT=dict(mean=24.0), FF=dict(mean=21.0))
    g = tmp / "fs_geom.json"; g.write_text(json.dumps(G)); c = tmp / "fs_ins.json"; c.write_text(json.dumps(ins))
    return g, c, G


def _fs_plan(tmp, extra=(), regs=False):
    g, c, G = _far_singleton(tmp, regs)
    out = tmp / ("fs_%s.json" % ("_".join(x.strip("-").replace("/", "-") for x in extra) or "greedy"))
    PT.main(["plan", str(g), str(c), str(out), "--entry", "220,300", "--child-ins", "mod_n=150/120"] + list(extra))
    return json.loads(out.read_text()), G, out


def _plan_ocv(P):
    T = PT._load_aocv(PT.HERE / "clk_aocv_table_g021.json")
    rng = {C: {k: (x[C.lower()], x[C.lower()]) for k, x in P["arrival_plan"].items()} for C in ("TT", "FF")}
    o = PT.ocv_spread(T, P["tree"], rng)
    return max(o["TT"]["ocv_inclusive_spread"], o["FF"]["ocv_inclusive_spread"])


@pytest.fixture(scope="module")
def fs_pair(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("fs")
    return _fs_plan(tmp), _fs_plan(tmp, ["--topology", "bipart"]), tmp


def test_bipart_structure(fs_pair):
    (Pg, G, _), (Pb, _, _), _ = fs_pair
    s = Pb["summary"]
    assert s["topology"] == "bipart" and s["odd_parity_sinks"] == []
    assert sorted(k["name"] for k in Pb["sinks"]) == sorted(k["name"] for k in Pg["sinks"])
    for i in Pb["insts"]:
        x, y = i["p"]
        assert not any(m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1 for m in G["macros"]), i
    # the winner is the argmin of the stated objective over the evaluated variants
    obj = [max(r["ocv_tt"], r["ocv_ff"]) for r in s["bipart_table"]]
    assert len(obj) >= 2 and max(s["plan_ocv"]["TT"]["ocv_inclusive_spread"],
                                 s["plan_ocv"]["FF"]["ocv_inclusive_spread"]) == pytest.approx(min(obj), abs=0.05)
    # plan_ocv is the plan-model OCV spread of the emitted tree (recomputed independently from the json)
    assert _plan_ocv(Pb) == pytest.approx(min(obj), abs=0.05)


def test_bipart_beats_greedy_on_objective(fs_pair):
    """on the far-singleton shape the bipartition objective (OCV-inclusive spread) is no worse than greedy's"""
    (Pg, _, _), (Pb, _, _), _ = fs_pair
    assert _plan_ocv(Pb) <= _plan_ocv(Pg) + 0.05


def test_bipart_variant_select_and_fail_closed(tmp_path):
    P, _, _ = _fs_plan(tmp_path, ["--topology", "bipart", "--bipart-variants", "geo/count/auto", "--bipart-pull", "0"])
    assert [r["variant"] for r in P["summary"]["bipart_table"]] == ["geo/count/auto/p0"]
    with pytest.raises(ValueError, match="selects none"):
        _fs_plan(tmp_path, ["--topology", "bipart", "--bipart-variants", "nope/x/y"])


def _arr_corner(P, tmp, C, ci):
    lines = []
    for k in P["sinks"]:
        a = P["arrival_plan"][k["name"]][C.lower()]
        if k["kind"] == "cluster":
            for j in range(3):
                lines.append("S r_%s_%d/CLK DFFHQNx1_ASAP7_75t_R clknet_%s %.3f %.3f %.3f" % (k["name"], j, k["name"], a, a + 416.5, a))
        else:
            lines.append("S %s/clk mod_n %s %.3f %.3f %.3f" % (k["name"], k["net"], a - (150.0, 120.0)[ci], a, a))
    f = tmp / ("arr_%s.txt" % C); f.write_text("\n".join(lines) + "\n")
    return f


def test_ocv_mode_and_corr_on_bipart(tmp_path):
    """ocv mode on arrivals equal to the plan reproduces the plan-model OCV spread; corr runs on a bipart tree"""
    P, G, out = _fs_plan(tmp_path, ["--topology", "bipart"], regs=True)
    fT, fF = _arr_corner(P, tmp_path, "TT", 0), _arr_corner(P, tmp_path, "FF", 1)
    o = tmp_path / "ocv.json"
    PT.main(["ocv", str(out), str(fT), str(fF), str(o)])
    oc = json.loads(o.read_text())
    for C in ("TT", "FF"):
        assert oc[C]["ocv_inclusive_spread"] == pytest.approx(P["summary"]["plan_ocv"][C]["ocv_inclusive_spread"], abs=0.2)
    # fail closed: a plan sink without measured arrivals
    fT.write_text("\n".join(l for l in fT.read_text().splitlines() if "r_c3_" not in l) + "\n")
    with pytest.raises(ValueError, match="miss 1 plan sinks"):
        PT.main(["ocv", str(out), str(fT), str(fF)])
    PT.main(["corr", str(out), str(_arr_corner(P, tmp_path, "TT", 0)), str(tmp_path / "c1.json")])
    C1 = json.loads((tmp_path / "c1.json").read_text())
    assert C1["summary"]["iteration"] == 1 and C1["summary"]["odd_parity_sinks"] == []


# ---------------------------------------------------------------- DIE-QC-18: eco (rebuild only the changed legs)
def _eco_netlist(built, eco_tcl):
    """apply the eco tcl (parsed) to the netlist of the as-built plan; returns ({inst: (in, out)}, {sink: net})"""
    import re
    insts = {i["name"]: (i["in_net"], i["out_net"]) for i in built["insts"]}
    sinks = {s["name"]: s["net"] for s in built["sinks"]}
    merge_in = {}
    lines = eco_tcl.read_text().splitlines()
    pend = None
    for l in lines:
        m = re.match(r"set i \[\$blk findInst \{(.+?)\}\]; .*dbInst_destroy", l)
        if m:
            insts.pop(m.group(1)); continue
        m = re.match(r"set m .*dbInst_create \$blk \$m (\S+?)\]; .*econet (\S+)\].*econet (\S+)\]$", l)
        if m:
            insts[m.group(1)] = (m.group(2), m.group(3)); continue
        m = re.match(r"set it \[\[\$blk findInst (?:\{(.+?)\}|\[string cat \{(.+?)\} \$RS\])\] findITerm (\S+)\]$", l)
        if m:
            pend = (m.group(1) or m.group(2), m.group(3)); continue
        m = re.match(r"\$it disconnect; \$it connect \[econet (\S+)\]$", l)
        if m:
            name, pin = pend
            if pin == "A" and name in insts:
                insts[name] = (m.group(1), insts[name][1])
            else:
                sinks[name] = m.group(1)
            pend = None
    return insts, sinks


def test_eco_identity_and_partial_rebuild(planned, tmp_path):
    P, G, out = planned
    # identity: nothing to rebuild, as-built == plan
    PT.main(["eco", str(out), str(out), str(tmp_path / "e0.tcl"), str(tmp_path / "b0.json")])
    B0 = json.loads((tmp_path / "b0.json").read_text())
    assert B0["insts"] == P["insts"] and B0["sinks"] == P["sinks"]
    assert B0["summary"]["eco"]["legs_rebuilt"] == 0 and "dbInst_destroy" not in (tmp_path / "e0.tcl").read_text()
    # corr changes some legs: only those are rebuilt, every other cell keeps its name and nets
    f = _arrivals(P, tmp_path, bump=("cl0", -40.0))
    PT.main(["corr", str(out), str(f), str(tmp_path / "c1.json")])
    C1 = json.loads((tmp_path / "c1.json").read_text())
    PT.main(["eco", str(out), str(tmp_path / "c1.json"), str(tmp_path / "e1.tcl"), str(tmp_path / "b1.json")])
    B1 = json.loads((tmp_path / "b1.json").read_text()); e = B1["summary"]["eco"]
    assert 1 <= e["legs_rebuilt"] < e["legs_kept"]
    assert e["cells_added"] == sum(1 for i in B1["insts"] if "_e1_r" in i["name"])
    old = {i["name"] for i in P["insts"]}
    assert len([i for i in B1["insts"] if i["name"] in old]) == len(P["insts"]) - e["cells_removed"]
    # the as-built plan is the planned geometry (same cells / positions as the corr plan, emit order kept)
    assert [(i["cell"], i["p"]) for i in B1["insts"]] == [(i["cell"], i["p"]) for i in C1["insts"]]
    assert B1["summary"]["n_inv"] == C1["summary"]["n_inv"] and len(B1["insts"]) == len(C1["insts"])
    # applying the eco tcl to the built netlist gives exactly the as-built netlist
    ins, snk = _eco_netlist(P, tmp_path / "e1.tcl")
    assert ins == {i["name"]: (i["in_net"], i["out_net"]) for i in B1["insts"]}
    assert snk == {s["name"]: s["net"] for s in B1["sinks"]}
    # the chain continues: corr + eco on the as-built plan
    PT.main(["corr", str(tmp_path / "b1.json"), str(_arrivals(B1, tmp_path, bump=("cl2", 25.0))), str(tmp_path / "c2.json")])
    PT.main(["eco", str(tmp_path / "b1.json"), str(tmp_path / "c2.json"), str(tmp_path / "e2.tcl"), str(tmp_path / "b2.json")])
    B2 = json.loads((tmp_path / "b2.json").read_text())
    ins, snk = _eco_netlist(B1, tmp_path / "e2.tcl")
    assert ins == {i["name"]: (i["in_net"], i["out_net"]) for i in B2["insts"]}
    assert snk == {s["name"]: s["net"] for s in B2["sinks"]}


def test_eco_fail_closed(planned, tmp_path):
    P, G, out = planned
    g, c, _ = _fixture(tmp_path)
    o2 = tmp_path / "other.json"
    PT.main(["plan", str(g), str(c), str(o2), "--entry", "160,250", "--child-ins", CI, "--pin-offset", "mod_rl=10,5",
             "--orient-rule", "150", "--topology", "bipart"])
    if json.loads(o2.read_text())["tree"] != P["tree"]:
        with pytest.raises(ValueError, match="eco: (topology|node) differs"):
            PT.main(["eco", str(out), str(o2), str(tmp_path / "x.tcl"), str(tmp_path / "x.json")])
    bad = dict(P); bad["insts"] = P["insts"][:-1]
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="plan insts"):
        PT.main(["eco", str(tmp_path / "bad.json"), str(out), str(tmp_path / "x.tcl"), str(tmp_path / "x.json")])


def test_grt_tcl_inc_loads_routes_first():
    s = (HERE / "parent_trunk_grt.tcl").read_text()
    i = s.index('$MODE eq "inc"')
    blk = s[i:s.index("global_route -end_incremental", i)]
    assert blk.index("estimate_parasitics -global_routing") < blk.index("global_route -start_incremental") < \
        blk.index("source $::env(ECO)")


# ---------------------------------------------------------------- QC-A0-KITS-9: --ungated-split (ICG inside the tree)
def _split_plan(tmp, extra=(), flag=True, regs=False):
    """far-singleton tile with the two N-edge-ish clusters flagged as the UNGATED input-face branch"""
    g, c, G = _far_singleton(tmp, regs)
    for cl in G["clusters"]:
        if cl["name"] in ("c3", "c7"):
            cl["ungated"] = True
    g.write_text(json.dumps(G))
    out = tmp / ("sp_%s.json" % ("_".join(x.strip("-") for x in extra) or "greedy"))
    PT.main(["plan", str(g), str(c), str(out), "--entry", "220,300", "--child-ins", "mod_n=150/120"]
            + (["--ungated-split"] if flag else []) + list(extra))
    return json.loads(out.read_text()), G, out


def _walk(nd, path=()):
    if nd["kind"] in ("cluster", "child"):
        yield nd, path
        return
    for k in nd["kids"]:
        yield from _walk(k, path + (nd["kind"],))


@pytest.mark.parametrize("topo", [(), ("--topology", "bipart")])
def test_ungated_split_structure(tmp_path, topo):
    P, G, out = _split_plan(tmp_path, topo)
    s = P["summary"]; u = s["ungated_split"]
    assert s["odd_parity_sinks"] == [] and sorted(u["ungated_sinks"]) == ["c3", "c7"]
    # ICG is a node below the root merge: every gated sink sits below it, no ungated sink does
    assert P["tree"]["kind"] == "merge"
    for nd, path in _walk(P["tree"]):
        assert ("icg" in path) == (not nd.get("ungated")), nd["name"]
    # the root leg starts at the tile entry on the clock port net; the ICG input is a planned trunk net
    assert P["root_leg"][0] == [220.0, 300.0] and u["root_net"] == "a0t_ckin"
    nets_out = {i["out_net"] for i in P["insts"]}
    assert u["icg_in"] in nets_out
    ins_in = {i["in_net"] for i in P["insts"]}
    assert "a0t_gclk" in ins_in or any(x["net"] == "a0t_gclk" for x in P["sinks"])
    # the ICG delay is charged to the gated branch only: gated vs ungated plan arrivals balanced by the root merge
    arr = P["arrival_plan"]
    g = [arr[n]["tt"] for n in arr if n not in ("c3", "c7")]; ug = [arr["c3"]["tt"], arr["c7"]["tt"]]
    assert max(g + ug) - min(g + ug) == pytest.approx(s["plan_tt"]["spread"], abs=0.11)
    assert abs(sum(g) / len(g) - sum(ug) / len(ug)) < 15.0
    for i in P["insts"]:
        x, y = i["p"]
        assert not any(m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1 for m in G["macros"]), i
    # tcl carries ROOT_NET / ICG_IN only for split plans
    t = tmp_path / "sp.tcl"; PT.main(["tcl", str(out), str(t)])
    txt = t.read_text()
    assert "set ROOT_NET a0t_ckin\n" in txt and ("set ICG_IN %s\n" % u["icg_in"]) in txt


def test_ungated_split_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="--ungated-split"):
        _split_plan(tmp_path, flag=False)
    with pytest.raises(ValueError, match="needs >= 1 ungated"):
        _fs_plan(tmp_path, ["--ungated-split"])


def test_ungated_split_default_untouched(tmp_path):
    """plans without the flag carry no split keys and their tcl no ROOT_NET (default bytes unchanged)"""
    P, _, out = _fs_plan(tmp_path)
    assert "ungated_split" not in P["summary"] and all("ungated" not in s for s in P["sinks"])
    t = tmp_path / "d.tcl"; PT.main(["tcl", str(out), str(t)])
    assert "ROOT_NET" not in t.read_text()


def test_ungated_split_ocv_corr_and_eco_refused(tmp_path):
    P, G, out = _split_plan(tmp_path, ("--topology", "bipart"), regs=True)
    fT, fF = _arr_corner(P, tmp_path, "TT", 0), _arr_corner(P, tmp_path, "FF", 1)
    o = tmp_path / "ocv.json"
    PT.main(["ocv", str(out), str(fT), str(fF), str(o)])
    oc = json.loads(o.read_text())
    for C in ("TT", "FF"):
        assert oc[C]["ocv_inclusive_spread"] == pytest.approx(P["summary"]["plan_ocv"][C]["ocv_inclusive_spread"], abs=0.2)
    PT.main(["corr", str(out), str(fT), str(tmp_path / "c1.json")])
    C1 = json.loads((tmp_path / "c1.json").read_text())
    assert C1["summary"]["iteration"] == 1 and C1["summary"]["odd_parity_sinks"] == []
    assert C1["summary"]["ungated_split"]["root_net"] == "a0t_ckin"
    with pytest.raises(ValueError, match="ungated-split"):
        PT.main(["eco", str(out), str(tmp_path / "c1.json"), str(tmp_path / "e.tcl"), str(tmp_path / "eb.json")])


def test_insert_tcl_ungated_split_and_icg_reuse():
    t = (HERE / "parent_trunk_insert.tcl").read_text()
    assert "ROOT_NET" in t and "ICG_IN" in t and "ICG_INST" in t and "OT_PT_NO_IO" in t
