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


def test_kit_rtl_spare_ft_bits_ride_stations(tmp_path):
    """QC-A0 10-24 (face_guard on coll_ftc): spare bits of an ft slot narrow on BOTH sides go through the slot's station
    chain (ot_dp_st x stations) instead of an unread input + a constant output"""
    plan = EX / "die_plan_lanes.json"
    out = tmp_path / "o"
    assert run(plan, out, "elab", "bind") == 0
    P = json.loads(plan.read_text())
    sl = P["partition_types"]["tf"]["ft_slots"][0]
    sl["width"] += 2
    sl["stations"] = 2
    wide = tmp_path / "wide.json"
    wide.write_text(json.dumps(P))
    kd = tmp_path / "kit"
    assert bind.main(["kit-rtl", str(wide), "--out", str(out), "--type", "tf", "--kit", str(kd)]) == 0
    man = json.loads((kd / "kit_rtl.json").read_text())
    n = sl["name"]
    assert man["spare_ft_passthrough"] == [dict(slot=n, bits=2, stations=2)] and man["spare_out_bits"] == [], man
    w = (kd / f"{P['partition_types']['tf']['module']}.sv").read_text()
    assert f"u_ft_spare_{n}_o_s0" in w and f"u_ft_spare_{n}_o_s1" in w and "'d0;  // spare plan bits" not in w


def test_kit_closure_needed_only_and_strip_dups(tmp_path):
    """QC-KITS 10-25: a file picked for one module must not drag in its unrelated siblings' instantiations, and a
    module defined in two kit files keeps the closure-picked definition only (sle_ctl ot_hdc_qadd)."""
    import bind_elab as E
    r = tmp_path / "rtl"
    r.mkdir()
    (r / "top_leaf.sv").write_text("module leaf_a (input wire a, output wire y);\n  helper u_h (.a(a), .y(y));\nendmodule\n"
                                   "module sibling (input wire a, output wire y);\n  big_unused u_b (.a(a), .y(y));\nendmodule\n")
    (r / "helper.sv").write_text("module helper (input wire a, output wire y);\n  assign y = a;\nendmodule\n"
                                 "module qadd (input wire a, output wire y);\n  assign y = ~a;\nendmodule\n")
    (r / "big.sv").write_text("module big_unused (input wire a, output wire y);\n  assign y = a;\nendmodule\n")
    (r / "other.sv").write_text("module needs_qadd (input wire a, output wire y);\n  qadd u_q (.a(a), .y(y));\nendmodule\n"
                                "module qadd (input wire a, output wire y);\n  assign y = a;\nendmodule\n")
    idx = E.module_index([str(r)], [], str(tmp_path))
    picks = {}
    files, missing, macros = bind.kit_closure(["leaf_a"], idx, [], picks)
    names = sorted(Path(f).name for f in files)
    assert names == ["helper.sv", "top_leaf.sv"], names          # big.sv (sibling's child) not dragged in
    assert not missing and not macros
    # two needed files both define qadd: the picked definition stays, the other file gets a stripped copy
    picks = {}
    files, _, _ = bind.kit_closure(["leaf_a", "needs_qadd"], idx, [str(r / "other.sv")], picks)
    assert Path(picks["qadd"]).name == "other.sv"
    kd = tmp_path / "kit"
    kd.mkdir()
    out, rec = bind.kit_strip_dups([Path(f) for f in files], kd, picks)
    defs = {}
    for f in out:
        for m in E.MOD_RE.finditer(E._strip(Path(f).read_text())):
            defs.setdefault(m.group(1), []).append(Path(f))
    assert all(len(v) == 1 for v in defs.values()), defs
    assert defs["qadd"][0].name == "other.sv" and defs["qadd"][0].parent == r
    assert defs["helper"][0].parent == kd / "dedup"                # helper.sv copy without qadd
    assert list(rec.values())[0]["removed"] == ["qadd"]
    assert (r / "helper.sv").read_text().count("module qadd") == 1  # original unchanged


def test_kit_inline_includes(tmp_path):
    """QC-KITS 10-25: a flattened kit cannot open `include "sub/x.svh"`: kit-rtl inlines it (recursively, relative to
    the including file) into KIT/inline/, and a missing include is a BindError."""
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "a.svh").write_text('localparam A = 1;\n`include "b.svh"\n')
    (src / "sub" / "b.svh").write_text("localparam B = 2;\n")
    top = src / "top.sv"
    top.write_text('module top;\n  `include "sub/a.svh"\nendmodule\n')
    plain = src / "plain.sv"
    plain.write_text("module plain; endmodule\n")
    kd = tmp_path / "kit"
    kd.mkdir()
    out, rec = bind.kit_inline_includes([top, plain], kd)
    assert out[1] == plain and out[0] == kd / "inline" / "top.sv"
    t = out[0].read_text()
    assert "localparam A = 1;" in t and "localparam B = 2;" in t and "`include \"" not in t.replace("inlined `include", "")
    assert len(rec[str(out[0])]["includes"]) == 2
    top.write_text('module top;\n`include "nope.svh"\nendmodule\n')
    try:
        bind.kit_inline_includes([top], kd)
        raise AssertionError("missing include must raise")
    except bind.BindError:
        pass


def test_bump_ports(tmp_path):
    """B2 (PATH-QC-B12 10-25): a hard core's declared line side (contents[].bump_ports) is absent from the as-built die
    and becomes die-top ports <partition>_<pin>, wired straight to the hard core's pins through partition ports
    bump_<leaf>_<pin> (no register, no constant); bind_verify proves the line-side input is driven by its die port.
    The same plan without the declaration binds byte-identically except for those lines."""
    src = tmp_path / "src"
    src.mkdir()
    for f in ("leaves.sv", "par.sv"):
        shutil.copy(EX / f, src / f)
    (src / "phy.sv").write_text(
        "module lf_phy (input wire clk, input wire [7:0] i, output reg [7:0] o,\n"
        "               output wire [7:0] link, input wire [7:0] far);\n"
        "    assign link = i;\n    always @(posedge clk) o <= far;\nendmodule\n")
    die = (EX / "die.v").read_text().replace("  lf_sink snk", "  wire [7:0] po;\n  lf_phy phy (.clk(ck), .i(y1), .o(po));\n"
                                              "  lf_sink snk")
    (src / "die.v").write_text(die)

    def plan(declare):
        p = json.loads((EX / "die_plan.json").read_text())
        a = p["asbuilt"]
        a["base"] = str(src)
        a["files"] = a["files"] + ["phy.sv"]
        a["map"]["parts"]["phy"] = "S"
        c = dict(inst="phy", module="lf_phy", status="reuse")
        if declare:
            c["bump_ports"] = [dict(pin="link", dir="output", width=8), dict(pin="far", dir="input", width=8)]
        p["partition_types"]["ts"]["contents"] = [c]
        f = tmp_path / f"die_plan_{int(declare)}.json"
        f.write_text(json.dumps(p))
        return f

    o0, o1 = tmp_path / "o0", tmp_path / "o1"
    assert run(plan(False), o0, "elab", "bind") == 0, report(o0)["errors"][:5]
    assert run(plan(True), o1, "elab", "bind", "verify") == 0, (report(o1)["errors"][:5], verify(o1).get("mismatches", [])[:3])
    r, v = report(o1), verify(o1)
    assert r["n_errors"] == 0 and r["proof"]["unbound"] == 0 and r["proof"]["tied"] == 0
    assert v["verdict"] == "PASS", (v["counts"], v["mismatches"][:3])
    assert {(b["die_port"], b["dir"], b["width"], b["leaf"], b["pin"]) for b in r["bump_ports"]} == {
        ("S_link", "output", 8, "S.u_phy", "link"), ("S_far", "input", 8, "S.u_phy", "far")}
    top = (o1 / "rtl" / "tiny_bound_top.sv").read_text() if (o1 / "rtl" / "tiny_bound_top.sv").exists() else \
        next((o1 / "rtl").glob("*_bound_top.sv")).read_text()
    assert "output wire [7:0] S_link;" in top and "input  wire [7:0] S_far;" in top
    assert ".bump_phy_link(S_link)" in top and ".bump_phy_far(S_far)" in top
    ts = (o1 / "rtl" / "bt_ts.sv").read_text()
    assert "output wire [7:0] bump_phy_link" in ts and "input  wire [7:0] bump_phy_far" in ts
    assert re.search(r"lf_phy u_phy \([^;]*\.link\(bump_phy_link\)", ts, re.S)
    assert re.search(r"lf_phy u_phy \([^;]*\.far\(bump_phy_far\)", ts, re.S)
    sinks = json.loads((o1 / "bind_sinks.json").read_text())
    assert all(sinks[f"phy.far[{i}]"] == ["top", "S_far"] for i in range(8))
    # without the declaration: no die port, and every generated file equals the declared bind minus the bump lines
    assert "bump_ports" not in report(o0)
    for f0 in sorted((o0 / "rtl").glob("*.sv")):
        a = f0.read_text()
        b = (o1 / "rtl" / f0.name).read_text()
        assert "bump_" not in a and "S_link" not in a and "S_far" not in a
        def strip(t):
            t = re.sub(r", S_(?:link|far)\b", "", t)
            return [ln.rstrip(",") for ln in t.splitlines() if not re.search(r"bump_phy_|S_(?:link|far)\b", ln)]
        assert strip(a) == strip(b), f0.name

    # a declared bump pin that the as-built netlist already connects is refused (it is not the line side)
    p = json.loads(plan(True).read_text())
    p["partition_types"]["ts"]["contents"][0]["bump_ports"] = [dict(pin="i", dir="input", width=8)]
    f = tmp_path / "die_plan_bad.json"
    f.write_text(json.dumps(p))
    run(f, tmp_path / "o2", "elab", "bind")
    assert any("as-built pin" in e for e in report(tmp_path / "o2")["errors"])


@pytest.mark.parametrize("enabled,named_tie", [(False, False), (True, False), (True, True)])
def test_internal_primitive_constants_preserve_boundary_audit(tmp_path, enabled, named_tie):
    """Arithmetic literals survive emission; named boundary constants remain forbidden."""
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    par = src / "par.sv"
    text = par.read_text().replace(".i(x)", ".i(x + 8'h01)")
    if named_tie:
        text = text.replace(".i(a_o)", ".i(8'h01)")
    par.write_text(text)
    plan = json.loads((src / "die_plan.json").read_text())
    plan["asbuilt"]["base"] = str(src)
    plan["asbuilt"]["internal_primitive_constants"] = enabled
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    out = tmp_path / "out"
    assert run(pf, out, "elab") == 0
    rc = run(pf, out, "bind")
    r = report(out)
    if enabled and not named_tie:
        assert rc == 0 and r["proof"]["tied"] == 0
        assert r["internal_primitive_literals"] > 0
        assert run(pf, out, "verify") == 0
        assert verify(out)["verdict"] == "PASS"
    else:
        assert r["n_errors"] > 0 and r["proof"]["tied"] > 0
        assert bind.main(["bind", str(pf), "--out", str(out), "--strict"]) != 0
        if enabled:
            assert any("lf_b.i" in str(x) for x in r.get("tied_by_port", [])) or r["proof"]["tied"] >= 16


def test_repeated_phy_io_roles_keep_separate_pads_and_outputs(tmp_path):
    """One hardened PHY type may share a port ABI, while its die pads stay distinct."""
    src = tmp_path / 'phy_src'
    src.mkdir()
    (src / 'phy.sv').write_text('''
module ck_source(output wire ck); endmodule
module rs_source(output wire rn); endmodule
module tiny_phy(input wire clk,rst_n,input wire [3:0] pma_rx,output reg [3:0] pma_tx);
always @(posedge clk) if(!rst_n)pma_tx<=0;else pma_tx<=pma_rx^4'h5;
endmodule
''')
    (src / 'die.v').write_text('''
module phy_die(input wire [3:0] a_pma_rx,b_pma_rx,output wire [3:0] a_pma_tx,b_pma_tx);
wire ck,rn;
ck_source c(.ck(ck));rs_source r(.rn(rn));
tiny_phy u0(.clk(ck),.rst_n(rn),.pma_rx(a_pma_rx),.pma_tx(a_pma_tx));
tiny_phy u1(.clk(ck),.rst_n(rn),.pma_rx(b_pma_rx),.pma_tx(b_pma_tx));
endmodule
''')
    p = dict(schema='opentallas.die_plan.v1', die=dict(name='phy_io'),
             partition_types=dict(phy=dict(module='bound_phy', reset=dict(sync_stages=2))),
             partitions=[dict(name='P0', type='phy'), dict(name='P1', type='phy')], ports=[], lanes=[],
             asbuilt=dict(base=str(src), netlist=['die.v'], top='phy_die', files=['phy.sv'], rtl_roots=[],
                          sources=[dict(module='ck_source', kind='clock', outputs=dict(ck='core')),
                                   dict(module='rs_source', kind='reset', outputs=dict(rn='low'))],
                          map=dict(parts=dict(u0='P0', u1='P1')),
                          io_roles=[[r'[ab]_(pma_.*)', r'\1']]))
    f = tmp_path / 'phy.json'
    f.write_text(json.dumps(p))
    out = tmp_path / 'bound'
    assert run(f, out, 'elab', 'bind', 'verify') == 0, report(out)['errors']
    assert report(out)['type_splits'] == []
    assert verify(out)['verdict'] == 'PASS'
    body = (out / 'rtl/bound_phy.sv').read_text()
    top = (out / 'rtl/phy_io_bound_top.sv').read_text()
    assert 'input wire [3:0] io_pma_rx' in body and 'output wire [3:0] io_pma_tx' in body
    assert 'assign io_pma_tx =' in body
    assert '.io_pma_rx(a_pma_rx)' in top and '.io_pma_rx(b_pma_rx)' in top
    assert '.io_pma_tx(a_pma_tx)' in top and '.io_pma_tx(b_pma_tx)' in top
    assert 'output wire [3:0] a_pma_tx;' in top and 'output wire [3:0] b_pma_tx;' in top
    # Causal control: without roles these two different external names must still split.
    del p['asbuilt']['io_roles']
    f2 = tmp_path / 'no_roles.json'
    f2.write_text(json.dumps(p))
    out2 = tmp_path / 'no_roles'
    assert run(f2, out2, 'elab') == 0
    assert bind.main(['bind', str(f2), '--out', str(out2), '--mem', '4', '--strict']) == 1
    assert report(out2)['type_splits']


def test_glue_source_names_share_only_same_typed_source(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    p = src / "par.sv"
    p.write_text(p.read_text().replace(".i(x)", ".i(x + 8'h01)"))
    plan = json.loads((src / "die_plan.json").read_text())
    plan["asbuilt"].update(base=str(src), internal_primitive_constants=True, glue_source_names=True)
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    out = tmp_path / "out"
    assert run(pf, out, "elab") == 0
    assert bind.main(["bind", str(pf), "--out", str(out), "--strict"]) == 0
    assert not report(out)["type_splits"]
    assert run(pf, out, "verify") == 0 and verify(out)["verdict"] == "PASS"
