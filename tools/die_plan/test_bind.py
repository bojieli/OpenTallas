"""tests for tools/die_plan/bind.py (BINDER2 10-23): python3 -m pytest tools/die_plan/test_bind.py

Runs the binder end to end (Yosys elab -> bind -> Yosys re-elab + connectivity proof + Verilator lint) on the
examples/bind_tiny die: a GEN-style die top with relays, a reset repeater, a fault OR, clock/reset sources, a dissolved
structural parent and a declared strap.  Needs Yosys ($OT_BIND_YOSYS or the ORFS docker image); skipped otherwise.
"""
import copy
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
pytestmark = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


def run(plan, out, *cmds):
    for c in cmds:
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        if rc:
            return rc
    return 0


def plan_copy(tmp_path, name, edit):
    """the example plan with `edit(plan)` applied, written next to the example sources (asbuilt.base made absolute)"""
    p = json.loads((EX / name).read_text())
    edit(p)
    p["asbuilt"]["base"] = str(EX)
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def report(out):
    return json.loads((Path(out) / "bind_report.json").read_text())


def verify(out):
    return json.loads((Path(out) / "verify_report.json").read_text())


@pytest.mark.parametrize("name", ["die_plan.json", "die_plan_lanes.json"])
def test_tiny_binds_and_proves(tmp_path, name):
    out = tmp_path / "o"
    assert run(EX / name, out, "elab", "bind", "verify") == 0
    r, v = report(out), verify(out)
    assert r["proof"] == dict(unbound=0, tied=0, undriven=0, multiply_bound=0, straps=8, plan_driven=0)
    assert r["n_errors"] == 0
    assert v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0 and v["counts"]["matched"] == 64
    if v["lint"].get("ran"):
        assert v["lint"]["errors"] == 0
    # leaves unchanged: the generated partitions instantiate the original masters with the as-built parameters
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    assert "lf_a #(.ID(P_u_a_ID))" in ta and "lf_b u_u_b" in ta
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert re.search(r"bt_ta #\(.*\.P_u_a_ID\(1\)", top) and re.search(r"bt_ta #\(.*\.P_u_a_ID\(2\)", top)
    # no constant reaches a leaf except through a declared strap parameter
    for f in (out / "rtl").glob("bt_*.sv"):
        body = f.read_text().split(");", 1)[1]
        assert not re.search(r"\.\w+\(\s*\d+'[bdh]", body), f


def test_lanes_ft_station_and_latency(tmp_path):
    out = tmp_path / "o"
    assert run(EX / "die_plan_lanes.json", out, "elab", "bind") == 0
    r = report(out)
    assert r["lanes"]["carrying"] == 6 and r["lanes"]["unplanned_bits"] == 0 and r["lanes"]["ft_hops"] == 1
    ft = (out / "rtl" / "bt_tf.sv").read_text()
    assert "input  wire [8:0] y_i" in ft and "output wire [8:0] y_o" in ft and ft.count("ot_dp_st #(.W(8))") == 1
    lat = {b["lane"]: b for b in json.loads((out / "bind_latency.json").read_text())["buses"]}
    assert lat["a0y"]["bound_stages"] == 3 == lat["a0y"]["plan_cycles"]
    assert lat["a0y"]["asbuilt_stages"] == [2, 2]          # two as-built relays removed, recorded
    assert lat["a1y"]["bound_stages"] == 2 and lat["a1y"]["asbuilt_stages"] == [1, 1]
    # plan bus names are the partition port names
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    for port in ("y_o", "ys_o", "f_o", "x_i"):
        assert re.search(rf"\b{port}\b", ta)


def test_forwarded_lane_chain(tmp_path):
    """no direct A0 -> S lane: the bits ride A0 -> A1 (via F) -> S, forwarded inside A1"""
    def edit(p):
        p["ports"] = [x for x in p["ports"] if x["id"] != "a0s__0"]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "a0s"]
        for x in p["ports"]:
            if x["id"] == "a1s__0":
                x["width"] = 16
        for b in p["partition_types"]["ta"]["buses"]:
            if b["name"] == "ys_o":
                b["width"] = 16
        for b in p["partition_types"]["ts"]["buses"]:
            if b["name"] == "d1_i":
                b["width"] = 16
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0
    r = report(out)
    assert r["lanes"]["forwarded_bits"] == 8 and r["lanes"]["unplanned_bits"] == 0
    assert r["lanes"]["forwarded_pairs"] == {"A0->S": 8}
    v = verify(out)
    assert v["verdict"] == "PASS", v["mismatches"][:3]
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert sinks["snk.d0[0]"][2] == 3 + 2                   # A0->A1 lane (3 cycles) + A1->S lane (2)


def test_unplanned_bits_are_reported(tmp_path):
    def edit(p):
        for x in p["ports"]:
            if x["id"] == "a0s__0":
                x["width"] = 5
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind")
    r = report(out)
    # 3 bits of A0 -> S have no lane room (A0 -> A1 -> S forwarding has no room either: a1s is full)
    assert r["lanes"]["unplanned_bits"] == 3 and r["proof"]["unbound"] == 3
    assert any(e.startswith("UNPLANNED A0 -> S: 3") for e in r["errors"])


def test_constant_is_reported_never_tied(tmp_path):
    """drop the strap declaration: the as-built 4'd5 / 4'd6 on u_b.id is TIED in the as-built; the binder reports it and
    leaves the leaf input an undriven wire (never a generated constant), so the proof fails"""
    def edit(p):
        p["asbuilt"]["straps"] = []
    out = tmp_path / "o"
    rc = run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify")
    r = report(out)
    assert r["proof"]["tied"] == 8 and r["proof"]["straps"] == 0
    assert any(e.startswith("TIED p0.u_b.id[0] = 1") for e in r["errors"])
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    assert "UNBOUND tied: p0.u_b.id[0]" in ta and "4'b" not in ta.split(");", 1)[1]
    assert rc != 0 and verify(out)["verdict"] == "FAIL"


def test_unmapped_and_unknown_are_errors(tmp_path):
    def edit(p):
        p["asbuilt"]["map"]["parts"].pop("snk")
        p["asbuilt"]["transport"] = [t for t in p["asbuilt"]["transport"] if t["module"] != "trep"]
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind")
    r = report(out)
    assert r["unmapped"] == 1
    assert any(e.startswith("UNMAPPED snk") for e in r["errors"])
    assert any(e.startswith("UNKNOWN_MODULE rst_rep0 (trep)") for e in r["errors"])


def test_substitute_inst_variant(tmp_path):
    """p1.u_b takes the plan variant lf_b_nid (no id port): its 4 strap bits disappear (recorded, not tied), A1 binds
    as a variant of type ta, and the proof still passes"""
    def edit(p):
        p["asbuilt"]["substitute_inst"] = [{"inst": r"p1\.u_b", "module": "lf_b_nid", "reason": "test chain head"}]
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0
    r = report(out)
    assert r["variants"]["instances"] == 1 and r["variants"]["removed_input_bits"] == {"lf_b_nid.id": 4}
    assert r["proof"]["tied"] == 0 and r["proof"]["straps"] == 4 and r["n_errors"] == 0
    assert any(t["type"] == "ta" for t in r["type_splits"])
    assert verify(out)["verdict"] == "PASS"
    assert "lf_b_nid u_u_b" in "".join(f.read_text() for f in (out / "rtl").glob("bt_ta*.sv"))


def test_lint_split(tmp_path):
    """asbuilt.lint_split: top against leaf interface stubs + one run per partition module with its own leaf closure"""
    def edit(p):
        p["asbuilt"]["lint_split"] = True
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0
    lt = verify(out)["lint"]
    if lt.get("ran"):
        assert lt["split"] and lt["errors"] == 0 and lt["runs"] >= 3


def test_plan_cells_replace_constants(tmp_path):
    """asbuilt.plan_cells: no strap declared; the plan's ID cells in S drive u_b.id of A0 / A1 over two plan lanes.  The
    8 as-built constant bits become plan_driven (not tied), the cells are emitted, and the proof passes"""
    def edit(p):
        a = p["asbuilt"]
        a["straps"] = []
        a["plan_cells"] = str(EX / "plan_cells.json")
        a["files"] = a["files"] + [str(HERE.parents[1] / "rtl" / "lib" / "ot_dp_id.sv")]
        t = p["partition_types"]
        t["ts"]["buses"] += [dict(name="id0_o", dir="out", width=4, kind="ctl"), dict(name="id1_o", dir="out", width=4, kind="ctl")]
        t["ta"]["buses"] += [dict(name="id_i", dir="in", width=4, kind="ctl")]
        for k, dst in ((0, "A0"), (1, "A1")):
            p["ports"].append({"id": f"id{k}__0", "src": {"part": "S", "bus": f"id{k}_o"}, "dst": {"part": dst, "bus": "id_i"},
                               "width": 4, "kind": "ctl"})
            p["lanes"].append({"id": f"id{k}", "ports": [f"id{k}__0"]})
            p["latency"]["lanes"][f"id{k}"] = {"cycles": 2, "stations": 0, "boundary": 2}
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r, v = report(out), verify(out)
    assert r["proof"]["tied"] == 0 and r["proof"]["straps"] == 0 and r["proof"]["plan_driven"] == 8 and r["n_errors"] == 0
    assert r["plan_cells"]["cells_emitted"] == 2
    ts = (out / "rtl" / "bt_ts.sv").read_text()
    assert "ot_dp_id_src #(.V(5), .W(4)) u_u_id_src" in ts and "ot_dp_id_add #(.K(1), .W(4)) u_u_id_add" in ts
    ta = (out / "rtl" / "bt_ta.sv").read_text()
    assert ".id(id_i_q[3:0])" in ta and "4'b" not in ta.split(");", 1)[1]
    assert v["verdict"] == "PASS" and v["counts"]["plan_driven"] == 8, (v["counts"], v["mismatches"][:3])


def test_rewires_swap(tmp_path):
    """asbuilt.rewires: a plan-declared connectivity change (snk.d0 <-> d1 sources swapped) is applied, recorded with
    the as-built register stages of its template edge, and proven against the bound netlist"""
    def edit(p):
        p["asbuilt"]["rewires"] = {"file": str(EX / "rewires.json"), "classes": ["swap"]}
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    assert r["rewires"]["bits"] == {"swap (same-sink template)": 16, "swap dropped": 0} and r["n_errors"] == 0
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert sinks["snk.d0[3]"][1] == "p1.u_b.o[3]" and sinks["snk.d1[3]"][1] == "p0.u_b.o[3]"
    assert verify(out)["verdict"] == "PASS"


def test_die_io_and_kept_source_leaf(tmp_path):
    """die IO pads become bound-top inputs routed to the partitions that read them (io_<pad>); a source rule with
    keep_leaf instantiates the source (here the clock receiver) as a leaf of its partition while its clock output
    stays the partition clock"""
    src = tmp_path / "src"
    src.mkdir()
    for f in ("leaves.sv", "par.sv"):
        shutil.copy(EX / f, src / f)
    die = (EX / "die.v").read_text().replace("module tdie ();", "module tdie (input wire pad_ref, input wire [3:0] pad_id);")
    die = die.replace(".pll(1'b0)", ".pll(pad_ref)").replace(".id(4'd5)", ".id(pad_id)")
    (src / "die.v").write_text(die)
    (src / "clk.sv").write_text("module tclkrx (input wire pll, output wire ck);\n  assign ck = pll;\nendmodule\n")
    p = json.loads((EX / "die_plan.json").read_text())
    a = p["asbuilt"]
    a["base"] = str(src)
    a["files"] = a["files"] + ["clk.sv"]
    for r in a["sources"]:
        if r["module"] == "tclkrx":
            r["keep_leaf"] = True
            r.pop("drop_in", None)
    a["map"]["parts"]["clk_rx"] = "S"
    f = tmp_path / "die_plan.json"
    f.write_text(json.dumps(p))
    out = tmp_path / "o"
    assert run(f, out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r, v = report(out), verify(out)
    assert r["n_errors"] == 0 and r["load_bits"]["die_io"] == 5 and r["proof"]["straps"] == 4
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert "input  wire [3:0] pad_id;" in top and ".io_pad_id(pad_id)" in top and ".io_pad_ref(pad_ref)" in top
    assert "tclkrx u_clk_rx" in (out / "rtl" / "bt_ts.sv").read_text()
    assert v["verdict"] == "PASS", (v["counts"], v["mismatches"][:3])


def test_reset_spine(tmp_path):
    """asbuilt.reset_spines: a crossing bit with no lane whose driver matches a spine pin rides an async spine landed
    by ot_dp_rsync in the sink partition (not UNPLANNED); the proof counts its 2 release stages"""
    def edit(p):
        p["ports"] = [x for x in p["ports"] if x["id"] != "a1f__0"]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "a1f"]
        p["asbuilt"]["reset_spines"] = [{"pin": r"p1\.u_b\.flt", "sync_stages": 2}]
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    assert r["lanes"]["unplanned_bits"] == 0 and r["lanes"]["reset_spine_bits"] == {"p1.u_b.flt": 1} and r["n_errors"] == 0
    ts = (out / "rtl" / "bt_ts.sv").read_text()
    assert "ot_dp_rsync #(.W(1), .S(2))" in ts
    assert verify(out)["verdict"] == "PASS"


def test_land_align(tmp_path):
    """asbuilt.land_align = cell: snk.d0 is split over a 2-cycle lane (5 b) and a forwarded 5-cycle route (3 b); the
    5 early bits get 3 pad stages so the bus lands as built (all 8 bits at the same depth), and the proof holds"""
    def edit(p):
        p["asbuilt"]["land_align"] = "cell"
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
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    la = r["lanes"]["landing_alignment"]
    assert la["padded_bits"] == 5 and la["max_pad"] == 3 and r["lanes"]["unplanned_bits"] == 0
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert {sinks[f"snk.d0[{i}]"][2] for i in range(8)} == {5}
    lat = json.loads((out / "bind_latency.json").read_text())
    assert lat["landing_pads"]["snk.d0"] == {"src_part": "A0", "pads": [3, 3], "bits": 5}
    assert verify(out)["verdict"] == "PASS"


def test_substitute_parent(tmp_path):
    """asbuilt.substitute_parent: the dissolved parent p1 is elaborated as its plan variant par_nid (no id port): the
    as-built literal on p1.id is dropped (recorded, not tied), the variant's leaves bind, and the proof passes"""
    def edit(p):
        p["asbuilt"]["substitute_parent"] = [{"inst": "p1", "module": "par_nid"}]
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan.json", edit), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    assert r["parent_variants"] == [dict(inst="p1", master="par", variant="par_nid", dropped_literal_bits=4,
                                         dropped_net_ports=[], new_unconnected_ports=[])]
    assert r["proof"]["straps"] == 4 and r["proof"]["tied"] == 0 and r["n_errors"] == 0
    assert "lf_b_nid u_u_b" in "".join(f.read_text() for f in (out / "rtl").glob("bt_ta*.sv"))
    assert verify(out)["verdict"] == "PASS"


def test_portbind_strict(tmp_path):
    """bind.py portbind: the strict tools/die_port_bind.py check on the generated top passes (no stubs, no unbound,
    tied, undriven or multiply-driven bits) and writes port_bind_strict.json / .txt"""
    out = tmp_path / "o"
    assert run(EX / "die_plan_lanes.json", out, "elab", "bind", "portbind") == 0
    assert (out / "port_bind_strict.txt").read_text().startswith("DIE_PORT_BIND PASS")
    assert (out / "port_bind_strict.json").exists()


def test_bus_groups(tmp_path):
    """bus_groups.json (COORD R8): the split snk.d0 bus is one landing group, misaligned by the lanes (2 vs 5 cycles)
    and aligned after the land_align pads; A0's y goes to A1 and S at the same as-built depth = a replica set"""
    def edit(p):
        p["asbuilt"]["land_align"] = "cell"
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
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind") == 0
    bg = json.loads((out / "bus_groups.json").read_text())
    g = next(x for x in bg["landing"] if x["sink"] == "snk" and x["src_part"] == "A0")
    d0 = [m for m in g["members"] if m["sink_port"] == "d0"]
    assert {m["bound_stages"] for m in d0} == {2, 5} and {m["landed_stages"] for m in d0} == {5}
    assert g["aligned_landed"] and bg["summary"]["landing_groups"] >= 2


def test_param_regen_and_land_exclude(tmp_path):
    """asbuilt.param_regen: a die hook re-derives a leaf parameter from the bound lane depth (ctx.depth) before the
    types form, recorded in param_regen.json; land_align_exclude keeps the excluded sink unpadded"""
    hook = tmp_path / "regen.py"
    hook.write_text("def regen(ctx):\n"
                    "    d = ctx.depth('snk', 'd0')\n"
                    "    return dict(params={'p0.u_a': {'ID': max(d.values())}}, record=dict(d0=sorted(set(d.values()))))\n")

    def edit(p):
        p["asbuilt"]["land_align"] = "cell"
        p["asbuilt"]["land_align_exclude"] = [r"snk\.d[01]"]
        p["asbuilt"]["param_regen"] = {"file": str(hook)}
        for x in p["ports"]:            # split snk.d0 over two lanes of different depth (as test_bus_groups)
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
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind") == 0
    pr = json.loads((out / "param_regen.json").read_text())
    assert pr["changed"] and pr["changed"][0]["inst"] == "p0.u_a"
    assert report(out)["lanes"]["landing_alignment"]["padded_groups"] == 0 and pr["record"]["d0"] == [2, 5]
    top = "".join(f.read_text() for f in (out / "rtl").glob("*.sv"))
    assert f".ID({pr['changed'][0]['bound']})" in top


def test_and_reducer(tmp_path):
    """reducer op "and" (scoped by `inst`): the as-built join is re-emitted per sink partition as ot_dp_and; verify
    compares it as an AND of the same leaf pins"""
    def edit(p):
        for r in p["asbuilt"]["reducers"]:
            r["op"] = "and"
            r["inst"] = "for0"
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0
    top = "".join(f.read_text() for f in (out / "rtl").glob("*.sv"))
    assert "ot_dp_and #(.N(2))" in top and "ot_dp_or #(" not in top.split("module ot_dp_and")[1].split("endmodule", 1)[1]


def test_lane_pad(tmp_path):
    """a latency-table lane above its natural depth (R8 pad) is padded after the in-boundary flop (data + epoch);
    the bound lane reaches the table cycles (no LANE_CYCLES error) and verify still passes"""
    def edit(p):
        p["latency"]["lanes"]["a1s"].update(cycles=6, pad=4)
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), out, "elab", "bind", "verify") == 0
    top = "".join(f.read_text() for f in (out / "rtl").glob("*.sv"))
    assert ".D(4)) u_lpad_" in top
    assert not [e for e in report(out)["errors"] if e.startswith("LANE_CYCLES")]
    lat = json.loads((out / "bind_latency.json").read_text())
    assert any(b["lane"] == "a1s" and b["bound_stages"] == 6 for b in lat["buses"])


def _split_d0(p):
    for x in p["ports"]:                # snk.d0 split over a 2-cycle lane (5 b) and a forwarded 5-cycle route (3 b)
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


def test_land_r8(tmp_path):
    """asbuilt.land_align = r8 (COORD 16:58 R8 SOURCE OF TRUTH): the pads come from PLAN-TOOL3's r8 landing table
    (PLANDIR/r8/<die>_r8_landing.json made by r8.py from this bind's bus_groups.json), realised after the in flop:
    snk.d0 lands at one depth, the r8 G0 check passes on the bound bus groups, the proof holds; a table made for
    another bind (wrong bound depth) is R8_STALE"""
    import r8 as R8
    out0 = tmp_path / "o0"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", _split_d0), out0, "elab", "bind") == 0
    bg = json.loads((out0 / "bus_groups.json").read_text())

    def edit(p):
        _split_d0(p)
        p["asbuilt"]["land_align"] = "r8"
    plan = plan_copy(tmp_path, "die_plan_lanes.json", edit)
    raw = json.loads(plan.read_text())
    tab, sm = R8.write_pads(raw, bg, tmp_path / "r8")
    assert sm["max_pad"] == 3
    out = tmp_path / "o"
    assert run(plan, out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    la = r["lanes"]["landing_alignment"]
    assert la["mode"] == "r8" and la["stale"] == 0 and la["uncovered"] == 0 and la["padded_bits"] == 5
    sinks = json.loads((out / "bind_sinks.json").read_text())
    assert {sinks[f"snk.d0[{i}]"][2] for i in range(8)} == {5}
    bg2 = json.loads((out / "bus_groups.json").read_text())
    msgs, st = R8.check(bg2, raw)
    assert not [m for s, m in msgs if s == "ERROR"] and st["groups_unequal"] == 0
    assert verify(out)["verdict"] == "PASS"
    js = json.loads(tab.read_text())
    for m in js["members"]:
        m["bound"] += 1
    tab.write_text(json.dumps(js))
    out2 = tmp_path / "o2"
    run(plan, out2, "elab", "bind")
    assert any(e.startswith("R8_STALE") for e in report(out2)["errors"])


def test_land_r8_pad_tree(tmp_path):
    """asbuilt.land_pad_tree (QC-TOK 10-24, opt-in): the same r8 table realised as delay trees (pads hoisted into the
    source / forwarding partition's tapped line): every sink lands at the same depth as with per-sink chains, the
    independent proof holds, and the tree never uses more flops than the chains"""
    import r8 as R8
    out0 = tmp_path / "o0"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", _split_d0), out0, "elab", "bind") == 0
    bg = json.loads((out0 / "bus_groups.json").read_text())

    def edit(p, tree):
        _split_d0(p)
        p["asbuilt"]["land_align"] = "r8"
        if tree:
            p["asbuilt"]["land_pad_tree"] = True
    land = {}
    for tree in (False, True):
        plan = plan_copy(tmp_path, "die_plan_lanes.json", lambda p: edit(p, tree))
        R8.write_pads(json.loads(plan.read_text()), bg, tmp_path / "r8")
        out = tmp_path / f"o_{int(tree)}"
        assert run(plan, out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
        assert verify(out)["verdict"] == "PASS"
        sinks = json.loads((out / "bind_sinks.json").read_text())
        land[tree] = {k: v[2] for k, v in sinks.items() if v[0] == "pin"}
        la = report(out)["lanes"]["landing_alignment"]
        if tree:
            assert la["tree"]["pad_flops"] <= la["pad_flops"]
            assert la["tree"]["hoisted_bits"] > 0                 # the pads moved upstream of the sink
    assert land[False] == land[True]


def test_clock_roles(tmp_path):
    """per-quadrant clock domains (KV-P5 type-split ask): A0 runs on clk_q_A, A1 on clk_q_B (same partition type ta);
    the partition module names the clock by its role, so ta binds ONE module and the top feeds each instance its own
    die clock; the proof holds"""
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    v = (src / "die.v").read_text()
    v = v.replace("wire ck;", "wire ck; wire ckb;").replace(
        "tclkrx clk_rx (.pll(1'b0), .ck(ck));", "tclkrx clk_rx (.pll(1'b0), .ck(ck));\n  tclkrx2 clk_rx2 (.pll(1'b0), .ckb(ckb));")
    v = v.replace("par #(.K(2)) p1 (.ck(ck)", "par #(.K(2)) p1 (.ck(ckb)")
    (src / "die.v").write_text(v)

    def edit(p):
        p["asbuilt"]["sources"] = [{"module": "tclkrx", "kind": "clock", "outputs": {"ck": "clk_q_A"}, "drop_in": ["pll"]},
                                   {"module": "tclkrx2", "kind": "clock", "outputs": {"ckb": "clk_q_B"}, "drop_in": ["pll"]}] + \
            [x for x in p["asbuilt"]["sources"] if x["kind"] != "clock"]
        p["asbuilt"]["default_clock"] = "clk_q_A"
        p["asbuilt"]["clock_roles"] = [[r"clk_q_[AB]", "clk_q"]]
        # A0 <-> A1 lanes join two different die clocks through plain registers: refused (LANE_CDC) in the default
        # endpoint mode (TOK-QK/D); this test is about the role naming, so it binds in the legacy partition mode
        p["asbuilt"]["lane_clock"] = "partition"
    p = json.loads((EX / "die_plan.json").read_text())
    edit(p)
    p["asbuilt"]["base"] = str(src)
    f = tmp_path / "die_plan.json"
    f.write_text(json.dumps(p))
    out = tmp_path / "o"
    assert run(f, out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    assert not [t for t in r["type_splits"] if t["type"] == "ta"], r["type_splits"]
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert ".clk(clk_clk_q_B)" in top and ".clk(clk_clk_q_A)" in top
    assert verify(out)["verdict"] == "PASS"


def test_kit_rtl(tmp_path):
    """bind.py kit-rtl (COORD 18:04 G3 kit RTL): the bound partition module inside a wrapper with the plan type's module
    name and exact plan pins + a filelist; instances whose straps differ need --instance; gen.py phys --kit-rtl takes it"""
    plan = EX / "die_plan_lanes.json"
    out = tmp_path / "o"
    assert run(plan, out, "elab", "bind") == 0
    P = json.loads(plan.read_text())
    tn = "bt_ta" if "bt_ta" in P["partition_types"] else sorted(P["partition_types"])[0]
    t = P["partition_types"][tn]
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", tn]) != 0       # two instances, IDs differ
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    inst = re.findall(r"^\s*\w+ #\(.*?\) (\w+) \(", top, re.M)[0]
    kd = tmp_path / "kit"
    assert bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", tn, "--instance", inst, "--kit", str(kd)]) == 0
    fl = (kd / "kit_rtl.f").read_text().split()
    assert Path(fl[0]).name == f"{t['module']}.sv" and all(Path(f).is_file() for f in fl)
    w = (kd / f"{t['module']}.sv").read_text()
    assert re.search(rf"^module {t['module']} \(", w, re.M) and " u_bound (" in w
    for b in t.get("buses", []):
        assert re.search(rf"\b{b['name']}\b", w), b["name"]
    man = json.loads((kd / "kit_rtl.json").read_text())
    assert man["plan_module"] == t["module"] and man["params"]


def test_param_regen_declared_default_and_unknown(tmp_path):
    """A default-only leaf must accept its declared parameter, and reject a typo.

    Reproduces the real D2D TXDP=0 leaf, whose Yosys cell parameters are empty while
    its master declares TXDP. The old binder rejected every valid regeneration.
    """
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    leaf = src / "leaves.sv"
    leaf.write_text(leaf.read_text().replace("module lf_sink (",
        "module lf_sink #(parameter integer DELTA = 0) (").replace(
        "q <= {flt, d0 ^ d1};", "q <= {flt, d0 ^ d1} + DELTA;"))
    hook = tmp_path / "regen_default.py"
    hook.write_text("def regen(ctx):\n    return dict(params={'snk': {'DELTA': 3}})\n")
    plan = json.loads((EX / "die_plan_lanes.json").read_text())
    plan["asbuilt"]["base"] = str(src)
    plan["asbuilt"]["param_regen"] = {"file": str(hook)}
    pp = tmp_path / "plan.json"
    pp.write_text(json.dumps(plan))
    out = tmp_path / "out"
    assert run(pp, out, "elab", "bind") == 0
    pr = json.loads((out / "param_regen.json").read_text())
    assert pr["changed"] == [dict(inst="snk", param="DELTA", asbuilt="0", bound=3)]
    assert ".DELTA(3)" in "".join(f.read_text() for f in (out / "rtl").glob("*.sv"))
    hook.write_text("def regen(ctx):\n    return dict(params={'snk': {'NOT_A_PARAMETER': 3}})\n")
    assert bind.main(["bind", str(pp), "--out", str(out), "--strict"]) != 0
    assert any("NOT_A_PARAMETER: not a parameter" in e for e in report(out)["errors"])


def test_param_regen_variant_own_default(tmp_path):
    """A new variant control is legal; its predecessor-only parameter remains illegal."""
    src=tmp_path/'src';shutil.copytree(EX,src)
    leaf=src/'leaves.sv';text=leaf.read_text();start=text.index('module lf_sink (');end=text.index('endmodule',start)+9
    variant=text[start:end].replace('module lf_sink (','module lf_sink_bo1 #(parameter integer ORDER = 0) (').replace('q <= {flt, d0 ^ d1};','q <= {flt, d0 ^ d1} + ORDER;')
    leaf.write_text(text.replace('module lf_sink (','module lf_sink #(parameter integer OLD_ONLY = 0) (')+'\n'+variant+'\n')
    hook=tmp_path/'regen.py';hook.write_text("def regen(ctx):\n    return dict(params={'snk': {'ORDER': 1}})\n")
    p=json.loads((EX/'die_plan_lanes.json').read_text());p['asbuilt']['base']=str(src)
    p['asbuilt']['substitute_inst']=[dict(inst='snk',module='lf_sink_bo1')];p['asbuilt']['param_regen']=dict(file=str(hook))
    pp=tmp_path/'plan.json';pp.write_text(json.dumps(p));out=tmp_path/'out'
    assert run(pp,out,'elab','bind')==0
    assert json.loads((out/'param_regen.json').read_text())['changed']==[dict(inst='snk',param='ORDER',asbuilt='0',bound=1)]
    assert '.ORDER(1)' in ''.join(f.read_text() for f in (out/'rtl').glob('*.sv'))
    hook.write_text("def regen(ctx):\n    return dict(params={'snk': {'OLD_ONLY': 1}})\n")
    assert bind.main(['bind',str(pp),'--out',str(out),'--strict'])!=0
    assert any('OLD_ONLY: not a parameter' in e for e in report(out)['errors'])


def _glue_die(p):
    """die_glue.v: the fault bits of A0 / A1 joined by glue of a dissolved parent j0 (mapped to S), then 2 relays"""
    p["asbuilt"]["netlist"] = ["die_glue.v"]
    p["asbuilt"]["dissolve"] = ["par", "jn"]
    p["asbuilt"]["map"]["parts"]["j0"] = "S"


def test_glue_transport_absorbed(tmp_path):
    """TOK-QK/C 10-24 (KV boot C1): the as-built relays after a glue cell re-homed to the sink partition whose every
    input crosses into it (the KV SerDes rx_v = AND of the two PHY halves) were cross-die transport, now realised by the
    lanes: the binder must not keep them as an intra ot_dp_dly (that landed the KV valid 4 flits after its data).  They
    move to the glue's crossing inputs as as-built depth (bus_groups), so R8 lands the join with the same offset as the
    rest of that bus.  asbuilt.glue_transport = "keep" restores the old (wrong) delay = the mutant this test kills."""
    out = tmp_path / "o"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", _glue_die), out, "elab", "bind", "verify") == 0, \
        report(out)["errors"][:5]
    r = report(out)
    assert r["n_errors"] == 0 and r["proof"]["tied"] == 0 and r["proof"]["undriven"] == 0
    sinks = json.loads((out / "bind_sinks.json").read_text())
    flt = sinks["snk.flt[0]"]
    assert flt[0] == "pin" and flt[2] == 0 and flt[3] is True, flt          # glue -> sink: wire, no kept stages
    top = "".join(f.read_text() for f in (out / "rtl").glob("bt_ts*.sv"))
    assert "ot_dp_dly" not in top
    bg = json.loads((out / "bus_groups.json").read_text())
    gl = [m for g in bg["landing"] if g["sink"].startswith("j0.") for m in g["members"]]
    assert gl and {m["asbuilt_stages"] for m in gl} == {2}                  # 0 lane-side + 2 absorbed relays
    assert {m.get("bus_join", "").split("|")[0] for m in gl} == {"snk"}      # one bus with the consumer leaf
    assert verify(out)["verdict"] == "PASS"

    def keep(p):
        _glue_die(p)
        p["asbuilt"]["glue_transport"] = "keep"
    out2 = tmp_path / "o2"
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", keep), out2, "elab", "bind") == 0
    s2 = json.loads((out2 / "bind_sinks.json").read_text())
    assert s2["snk.flt[0]"][2] == 2                                          # the C1 bug: transport kept on top of lanes


def test_r8_bus_join_unions_split_halves():
    """r8 bus_key: members carrying one bind.py bus_join (one as-built port split over two source partitions, the KV
    SerDes W / E halves) form ONE bus: unequal offsets are an R8 ERROR and the pads equalise them (W +6 as on KV)"""
    import r8 as R8

    def grp(sink, sp, src, bound, bj):
        return dict(sink=sink, sink_part="hub", src_part=sp, members=[dict(
            sink_port="i", sink_bits=[[0, 0]], source=src, source_bits=[[0, 0]], asbuilt_stages=4, bound_stages=bound,
            landed_stages=bound, lane="l", **({"bus_join": bj} if bj else {}))])
    raw = dict(partitions=[dict(name=x, type=x) for x in ("hub", "W", "E")])
    for bj, nerr in (("host|serdes_host", 1), (None, 0)):
        bg = dict(landing=[grp("host", "W", "serdes_host.u_W.d", 30, bj), grp("host", "E", "serdes_host.u_E.d", 36, bj)],
                  replica=[])
        msgs, _ = R8.check(bg, raw)
        assert sum(1 for s, m in msgs if s == "ERROR" and "unequal" in m) == nerr
        if bj:
            mem, _ = R8.solve(bg, raw)
            assert sorted(x["pad"] for x in mem) == [0, 6]


# ---------------------------------------------------------------- TOK-QK/D 10-24: lane clock = endpoint domain
DIE_D = """// bind_tiny variant (TOK-QK/D 10-24): the KV kvpc <-> HBM PHY shape.  u_c (partition A) is a two-clock leaf whose
// po / pi ports live in its HBM clock domain; u_p (partition P) is the HBM PHY on the HBM clock only; u_s (partition S)
// takes u_c's core-domain output.  The as-built relays are removed by the binder.
module tdie ();
  wire ck; wire ckh; wire rs;
  wire [7:0] po; wire [7:0] po_r1; wire [7:0] pi; wire [7:0] pi_r1; wire [7:0] y; wire [7:0] sq;
  tclkrx clk_rx (.pll(1'b0), .ck(ck));
  tclkh clk_h (.pll(1'b0), .ckh(ckh));
  trstsync rst_s (.ck(ck), .q(rs));
  lf_hc u_c (.ck(ck), .hck(ckh), .rst_n(rs), .pi(pi_r1), .po(po), .y(y));
  trly_8 rly0 (.ck(ck), .a(po), .b(po_r1));
  lf_hp u_p (.hck(ckh), .po(po_r1), .pi(pi));
  trly_8 rly1 (.ck(ck), .a(pi), .b(pi_r1));
  lf_cs u_s (.clk(ck), .d(y), .q(sq));
endmodule
"""
LEAVES_D = """`timescale 1ns/1ps
module lf_hc (input wire ck, input wire hck, input wire rst_n, input wire [7:0] pi, output reg [7:0] po, output reg [7:0] y);
    reg [7:0] h, c;
    always @(posedge hck) begin h <= pi + 8'd1; po <= h; end
    always @(posedge ck or negedge rst_n) if (!rst_n) c <= 8'd0; else c <= c + 8'd1;
    always @(posedge ck) y <= c;
endmodule
module lf_hp (input wire hck, input wire [7:0] po, output reg [7:0] pi);
    always @(posedge hck) pi <= po ^ 8'h5a;
endmodule
module lf_cs (input wire clk, input wire [7:0] d, output reg [7:0] q);
    always @(posedge clk) q <= d;
endmodule
"""


def _plan_d(tmp_path, edit=None, s_on_hbm=False):
    src = tmp_path / "src"
    if not src.exists():
        src.mkdir()
    die = DIE_D.replace("lf_cs u_s (.clk(ck)", "lf_cs u_s (.clk(ckh)") if s_on_hbm else DIE_D
    (src / "die_d.v").write_text(die)
    (src / "leaves_d.sv").write_text(LEAVES_D)
    p = {"schema": "opentallas.die_plan.v1", "die": {"name": "bind_d"},
         "partition_types": {"ta": {"module": "bd_ta", "reset": {"sync_stages": 2}},
                             "tp": {"module": "bd_tp", "reset": {"sync_stages": 2}},
                             "ts": {"module": "bd_ts", "reset": {"sync_stages": 2}}},
         "partitions": [{"name": "A", "type": "ta"}, {"name": "P", "type": "tp"}, {"name": "S", "type": "ts"}],
         "ports": [], "lanes": [],
         "asbuilt": {"base": str(src), "netlist": ["die_d.v"], "top": "tdie", "rtl_roots": [], "files": ["leaves_d.sv"],
                     "transport": [{"module": "trly_\\d+", "map": {"b": "a"}, "drop_in": ["ck"], "stages": 1}],
                     "sources": [{"module": "tclkrx", "kind": "clock", "outputs": {"ck": "core"}, "drop_in": ["pll"]},
                                 {"module": "tclkh", "kind": "clock", "outputs": {"ckh": "clk_hbm_EN"}, "drop_in": ["pll"]},
                                 {"module": "trstsync", "kind": "reset", "outputs": {"q": "low"}, "drop_in": ["ck"]}],
                     "default_clock": "core", "clock_roles": [["clk_hbm_(EN|ES|WN|WS)", "clk_hbm"]],
                     "port_domains": [{"module": "lf_hc", "ports": {"pi|po": "hck"}, "default": "ck"}],
                     "map": {"parts": {"u_c": "A", "u_p": "P", "u_s": "S"}}}}
    if edit:
        edit(p)
    f = tmp_path / "die_plan_d.json"
    f.write_text(json.dumps(p))
    return f


def _flops(sv, clk):
    """names of the boundary flops (ot_dp_st) clocked by `clk` in a generated partition module"""
    return set(re.findall(rf"ot_dp_st #\(\.W\(\d+\)\) (u_\w+) \(\.clk\({clk}\)", sv))


def test_lane_clock_endpoint_domain(tmp_path):
    """D: a lane whose driver and sink are both in the HBM domain (kvpc po/pi <-> PHY) is registered on the HBM clock in
    BOTH partitions -- no crossing at all; the core-domain lane (y -> S) stays on the core clock; proof + lint PASS"""
    out = tmp_path / "o"
    assert run(_plan_d(tmp_path), out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r = report(out)
    assert r["n_errors"] == 0, r["errors"][:5]
    ld = r["lane_domains"]
    assert ld["mode"] == "endpoint" and ld["cdc_unsync_bits"] == 0 and not ld["undeclared"]
    assert ld["bits_by_domain"] == {"clk_hbm_EN": 16, "core": 8}
    a = (out / "rtl" / "bd_ta.sv").read_text()
    p = (out / "rtl" / "bd_tp.sv").read_text()
    hb = {x for x in _flops(a, "clk_clk_hbm")}
    assert any("po" in x for x in hb) and any("pi" in x for x in hb), a
    assert not {x for x in _flops(a, "clk") if "po" in x or "pi" in x}          # nothing of po / pi on the core clock
    assert any("y" in x for x in _flops(a, "clk"))
    assert "u_rst_sync_clk_hbm" in a and "ot_dp_lsync" in a                      # HBM-domain reset; epoch -> core check
    assert len(_flops(p, "clk")) == 2 and "clk_core" not in p                   # P is all HBM (its default clock)
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    assert re.search(r"bd_ta A \(\s*\.clk\(clk_core\),\s*\.arst_n\(rst_n\),\s*\.clk_clk_hbm\(clk_clk_hbm_EN\)", top)
    assert verify(out)["verdict"] == "PASS"


def test_lane_clock_undeclared_and_legacy(tmp_path):
    """a multi-clock leaf port with no declared domain is refused (never assumed); lane_clock "partition" reproduces the
    pre-D binding (po / pi boundary flops of A on the core clock = the KV bug, kept as the mutant)"""
    out = tmp_path / "o"
    assert run(_plan_d(tmp_path, lambda p: p["asbuilt"].pop("port_domains")), out, "elab", "bind") == 0
    r = report(out)
    assert any(e.startswith("PORT_DOMAIN_UNDECLARED lf_hc.po") for e in r["errors"]), r["errors"][:5]
    assert any(e.startswith("PORT_DOMAIN_UNDECLARED lf_hc.pi") for e in r["errors"])
    out2 = tmp_path / "o2"
    assert run(_plan_d(tmp_path, lambda p: p["asbuilt"].update(lane_clock="partition")), out2, "elab", "bind") == 0
    a = (out2 / "rtl" / "bd_ta.sv").read_text()
    assert {x for x in _flops(a, "clk") if "po" in x or "pi" in x} and not _flops(a, "clk_clk_hbm")


def test_lane_clock_cdc_refused_or_synchronised(tmp_path):
    """a genuine crossing (core-domain y into an HBM-clocked sink) through plain lane registers is refused (LANE_CDC);
    declaring the sink port a synchroniser ("sync") accepts it and records it"""
    out = tmp_path / "o"
    assert run(_plan_d(tmp_path, s_on_hbm=True), out, "elab", "bind") == 0
    r = report(out)
    assert r["lane_domains"]["cdc_unsync_bits"] == 8
    assert any(e.startswith("LANE_CDC ") and "core->clk_hbm_EN" in e and "lf_cs.d" in e for e in r["errors"]), r["errors"][:5]

    def sync(p):
        p["asbuilt"]["port_domains"].append({"module": "lf_cs", "ports": {}, "sync": ["d"]})
    out2 = tmp_path / "o2"
    assert run(_plan_d(tmp_path, sync, s_on_hbm=True), out2, "elab", "bind") == 0
    r2 = report(out2)
    assert r2["n_errors"] == 0 and r2["lane_domains"]["sync_port_bits"] == 8, r2["errors"][:5]
