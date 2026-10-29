"""DIE-HEAD-11 start_stage_emit: START-TREE-1 virtual start stages -> die-level flops beside their clock-tree node."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import start_stage_emit as E   # noqa: E402
import die_sta_related as DSR  # noqa: E402

A0, A1 = chr(0x100), chr(0x101)
P_ROOT, P_L, P_R = "h" + A0, "h" + A0 + A0, "h" + A0 + A1


def _tree(cell="BUFx24_ASAP7_75t_R"):
    # root -> b0 -> b1 (P_ROOT) -> {b2 (P_L), b3 (P_R)}; b2 -> tap a, b3 -> tap b
    v = ("module ctree (root, t_a__clk, t_b__clk);\n  input root;\n  output t_a__clk;\n  output t_b__clk;\n"
         "  wire n0;\n  wire n1;\n  wire n2;\n  wire n3;\n"
         f"  {cell} b0 (.A(root), .Y(n0));\n  {cell} b1 (.A(n0), .Y(n1));\n"
         f"  {cell} b2 (.A(n1), .Y(n2));\n  {cell} b3 (.A(n1), .Y(n3));\n"
         "  assign t_a__clk = n2;\n  assign t_b__clk = n3;\nendmodule\n")
    t = ("place_pin -pin_name root -layer M9 -location {50.000 50.000} -pin_size {0.04 0.32}\n"
         "place_pin -pin_name t_a__clk -layer M9 -location {10.000 50.000} -pin_size {0.04 0.32}\n"
         "place_pin -pin_name t_b__clk -layer M9 -location {90.000 50.000} -pin_size {0.04 0.32}\n"
         "place_inst -name b0 -location {50.000 50.000} -status PLACED\n"
         "place_inst -name b1 -location {50.000 60.000} -status PLACED\n"
         "place_inst -name b2 -location {30.000 60.000} -status PLACED\n"
         "place_inst -name b3 -location {33.780 60.000} -status PLACED\n"
         "set_wire_rc -signal\n")
    return v, t


def _meta():
    cell = {"h": "b0", P_ROOT: "b1", P_L: "b2", P_R: "b3"}
    xy = {"h": [50, 50], P_ROOT: [50, 60], P_L: [30, 60], P_R: [33.78, 60]}
    return dict(node_cell=cell, node_xy_um=xy, node_stages={"h": 1, P_ROOT: 2, P_L: 3, P_R: 3},
                node_late_ps={"h": 10.0, P_ROOT: 30.0, P_L: 50.0, P_R: 52.0},
                node_early_ps={"h": 9.0, P_ROOT: 28.0, P_L: 47.0, P_R: 49.0},
                taps=[dict(port="t_a__clk", part="a", late_ps=90.0, early_ps=85.0, cppr_node="a", tree_path=P_L + A0,
                           stages_from_root=4, xy_um=[10, 50]),
                      dict(port="t_b__clk", part="b", late_ps=92.0, early_ps=87.0, cppr_node="b", tree_path=P_R + A0,
                           stages_from_root=4, xy_um=[90, 50])])


def _bind():
    reg = {f"st:{P_ROOT}": dict(parent=None, tree_port=None, edge_fall=False, pad=0, virtual=True),
           f"st:{P_L}": dict(parent=f"st:{P_ROOT}", tree_port=f"start:st:{P_ROOT}->st:{P_L}", edge_fall=True, pad=2,
                             virtual=True),
           "a": dict(parent=f"st:{P_L}", tree_port=f"start:st:{P_L}->a", edge_fall=False, pad=0),
           "b": dict(parent=f"st:{P_ROOT}", tree_port=f"start:st:{P_ROOT}->b", edge_fall=False, pad=1)}
    sp = {r["tree_port"]: dict(src=r["parent"], dst=x, launch_part=None, capture_part=x if not x.startswith("st:")
                               else None) for x, r in reg.items() if r["tree_port"]}
    return dict(regions=reg, start_ports=sp)


def test_emit_stages_netlist_and_clock_taps():
    v, t = _tree()
    doc, sv, v2, t2 = E.emit(_bind(), _meta(), v, t)
    st = {s["region"]: s for s in doc["stages"]}
    assert doc["schema"] == E.SCHEMA and doc["counts"]["stages"] == 2
    r, l = st[f"st:{P_ROOT}"], st[f"st:{P_L}"]
    assert (r["id"], r["clock_net"], r["clock_from"], r["root"], r["flops"]) == ("b1", "n1", "Y", True, 7 + 1)
    assert (r["module"], r["settle"], doc["root_settle"]) == ("ot_dp_landing_root", 64, 64)
    assert (l["id"], l["clock_net"], l["flops"], l["pad"], l["edge_fall"]) == ("b2", "n2", 3 + 2 + 1, 2, True)
    assert l["parent"] == f"st:{P_ROOT}" and l["children"] == ["a"] and r["children"] == ["b", f"st:{P_L}"]
    # netlist: the root stage is the die root counter (no die-top root start), chain, outputs to the data regions
    assert ("ot_dp_landing_root #(.SETTLE(64)) u_st_b1 (.clk(t_st_b1__clk), .rst_raw_n(rst_raw_n), "
            ".start(st_b1_start), .start_d(st_b1_start_d))") in sv
    assert "    wire st_b1_start_d;" in sv and r["start_d_net"] == "st_b1_start_d"
    assert "root_p_start" not in sv
    assert "#(.PAD(2), .EDGE_FALL(1)) u_st_b2 (.clk(t_st_b2__clk), .rst_raw_n(rst_raw_n), .p_start(st_b1_start)" in sv
    assert "assign pst_a = st_b2_start;" in sv and "assign pst_b = st_b1_start;" in sv
    assert sorted(o["dst_region"] for o in doc["die_outputs"]) == ["a", "b"] and doc["die_inputs"] == []
    # clock tree: one tap port per stage on its node net, pin at the stage's clock pin
    assert re.search(r"module ctree \(root, t_a__clk, t_b__clk, t_st_b1__clk, t_st_b2__clk\);", v2)
    assert "  output t_st_b1__clk;" in v2 and "  assign t_st_b2__clk = n2;" in v2
    assert v2.replace("\n  output t_st_b1__clk;\n  output t_st_b2__clk;", "").replace(
        "  assign t_st_b1__clk = n1;\n  assign t_st_b2__clk = n2;\n", "").replace(
        ", t_st_b1__clk, t_st_b2__clk", "") == v
    x, y = l["clock_pin_xy_um"]
    assert f"place_pin -pin_name t_st_b2__clk -layer M9 -location {{{x:.3f} {y:.3f}}}" in t2
    assert t2.index("t_st_b2__clk") < t2.index("place_inst")


def test_root_stage_binds_every_master_port_nested_check():
    """DIE-HEAD-31 (DIE-HEAD-30 bind 0a054fa865 nested FAIL u_st_b0.start_d open): every port of every emitted stage
    instance, incl. the root counter's FSTART D-side output start_d, is bound (main port_bind_gate.nested_check)."""
    import port_bind_gate as PBG
    v, t = _tree()
    _, sv, _, _ = E.emit(_bind(), _meta(), v, t)
    rtl = (Path(__file__).resolve().parents[2] / "rtl" / "common" / "ot_dp_clk_landing_ca.sv").read_text()
    r = PBG.nested_check({"start_stages.sv": sv}, [rtl])
    assert (r["verdict"], r["instances"], r["unbound"], r["unknown"], r["width_mismatch"], r["unresolved"]) == \
        ("PASS", 2, 0, 0, 0, 0), r
    # the pre-fix netlist (root .start_d open) fails the same check on exactly that pin
    old = sv.replace(", .start_d(st_b1_start_d)", "")
    r = PBG.nested_check({"start_stages.sv": old}, [rtl])
    assert r["verdict"] == "FAIL" and r["examples"]["unbound"] == ["ot_die_start_stages.u_st_b1 (ot_dp_landing_root).start_d"]


def test_root_counter_settle_from_bind_or_option():
    v, t = _tree()
    b = dict(_bind(), root_settle_cycles=16)
    doc, sv, _, _ = E.emit(b, _meta(), v, t)
    r = next(s for s in doc["stages"] if s["root"])
    assert (r["settle"], r["flops"]) == (16, 5 + 1) and "ot_dp_landing_root #(.SETTLE(16)) u_st_b1 " in sv
    doc, sv, _, _ = E.emit(b, _meta(), v, t, root_settle=3)
    assert "ot_dp_landing_root #(.SETTLE(3)) u_st_b1 " in sv
    with pytest.raises(E.StageError, match="SETTLE"):
        E.emit(b, _meta(), v, t, root_settle=0)


def test_root_counter_simulates_release_chain(tmp_path):
    """iverilog: raw release -> root counter start after SETTLE+1 edges -> child stage start a few cycles later"""
    import shutil
    import subprocess
    iv = shutil.which("iverilog")
    if iv is None:
        pytest.skip("iverilog not installed")
    v, t = _tree()
    _, sv, _, _ = E.emit(_bind(), _meta(), v, t, root_settle=4)
    rtl = Path(__file__).resolve().parents[2] / "rtl" / "common" / "ot_dp_clk_landing_ca.sv"
    (tmp_path / "s.sv").write_text(sv)
    (tmp_path / "tb.sv").write_text(
        "module tb; reg clk = 0, rst = 0; wire a, b; integer c = 0, ta = -1, tb_ = -1;\n"
        " always #5 clk = ~clk;\n"
        " ot_die_start_stages u (.rst_raw_n(rst), .t_st_b1__clk(clk), .t_st_b2__clk(clk), .pst_a(a), .pst_b(b));\n"
        " always @(posedge clk) begin c <= c + 1; if (b && tb_ < 0) tb_ <= c; if (a && ta < 0) ta <= c; end\n"
        " initial begin #22 rst = 1; #400 $display(\"B %0d A %0d\", tb_, ta); $finish; end\nendmodule\n")
    r = subprocess.run([iv, "-g2012", "-s", "tb", "-o", str(tmp_path / "a.out"), str(rtl), str(tmp_path / "s.sv"),
                        str(tmp_path / "tb.sv")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = subprocess.run(["vvp", str(tmp_path / "a.out")], capture_output=True, text=True).stdout
    m = re.search(r"B (-?\d+) A (-?\d+)", out)
    assert m, out
    tb_, ta = int(m.group(1)), int(m.group(2))
    assert tb_ > 4 and ta > tb_, out     # root start after SETTLE counts; the child stage (PAD 2) releases later


def test_stage_rows_clear_clock_cells_and_each_other():
    v, t = _tree()
    doc, *_ = E.emit(_bind(), _meta(), v, t)
    cells = [(30.0, 31.62, 60.0), (33.78, 35.4, 60.0), (50.0, 51.62, 60.0), (50.0, 51.62, 50.0)]
    rects = [s["rect_um"] for s in doc["stages"]]
    for x0, y0, x1, y1 in rects:
        assert abs((x1 - x0) - E.FLOP_W_UM * [s for s in doc["stages"] if s["rect_um"][0] == x0][0]["flops"]) < 1e-6
        for a, b, cy in cells:
            assert not (abs(cy - y0) < 1e-6 and x0 < b and x1 > a)
    (a0, ay, a1, _), (b0, by, b1, _) = rects
    assert not (abs(ay - by) < 1e-6 and a0 < b1 and a1 > b0)
    # b2 (6 flops) does not fit right of b2 (b3 at 33.78) -> left of it on the same row
    l = [s for s in doc["stages"] if s["id"] == "b2"][0]
    assert l["rect_um"][2] <= 30.0 and l["rect_um"][1] == 60.0
    assert doc["counts"]["max_cell_to_stage_um"] < 10


def test_inverting_tree_takes_true_polarity_net():
    v, t = _tree("CKINVDCx16_ASAP7_75t_R")
    doc, sv, v2, _ = E.emit(_bind(), _meta(), v, t)
    st = {s["id"]: s for s in doc["stages"]}
    # b1 = 2 inverters from root (true) -> Y; b2 = 3 (inverted) -> its input net n1 (true)
    assert (st["b1"]["clock_net"], st["b1"]["clock_from"]) == ("n1", "Y")
    assert (st["b2"]["clock_net"], st["b2"]["clock_from"]) == ("n1", "A")
    assert "assign t_st_b2__clk = n1;" in v2


def test_proof_with_measured_stage_taps(tmp_path):
    v, t = _tree()
    doc, *_ = E.emit(_bind(), _meta(), v, t)
    pr = tmp_path / "proof"
    pr.mkdir()
    for c in ("TT", "FF"):
        (pr / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(_meta(), corner=c)))
    (pr / "droop_regions.json").write_text("{}")
    arr = tmp_path / "arr_TT.txt"
    arr.write_text("T t_a__clk 90 85 20\nT t_st_b1__clk 33.5 31.0 18\nT t_st_b2__clk 61.25 57.0 19\nN b0 1 1 1 1\n")
    arf = tmp_path / "arr_FF.txt"
    arf.write_text("T t_st_b1__clk 25 23 15\nT t_st_b2__clk 44 41 16\n")
    out = E.proof_with_stages(pr, doc, {"TT": arr, "FF": arf}, tmp_path / "proof_st")
    meta, taps = DSR.load_taps(out, "TT")
    k = f"__st__{P_L}"
    assert taps[k]["late_ps"] == 61.25 and taps[k]["early_ps"] == 57.0 and taps[k]["tree_path"] == P_L
    assert taps[k]["part"] is None and taps[k]["stages_from_root"] == 3
    # the shared model keeps the measured stage tap (virtual_tap only models an ABSENT stage)
    leg = DSR.tap_leg(meta, taps)
    assert DSR.virtual_tap(meta, taps, P_L, leg) == k and taps[k]["late_ps"] == 61.25
    assert DSR.load_taps(out, "FF")[1][f"__st__{P_ROOT}"]["late_ps"] == 25.0
    assert (out / "droop_regions.json").exists()
    with pytest.raises(E.StageError):
        E.proof_with_stages(pr, doc, {"TT": tmp_path / "missing.txt"}, tmp_path / "proof_st")


def test_proof_stage_taps_take_measured_fall(tmp_path):
    # DIE-HEAD-12: a FLOW-ONEMODEL-2 both-edge readout (T + F rows) gives each stage tap its own measured fall arrival;
    # a T-only readout keeps the stage tap rise-only (unchanged)
    v, t = _tree()
    doc, *_ = E.emit(_bind(), _meta(), v, t)
    pr = tmp_path / "proof"
    pr.mkdir()
    (pr / "tap_arrivals_TT.json").write_text(json.dumps(dict(_meta(), corner="TT")))
    arr = tmp_path / "arr_TT.txt"
    arr.write_text("# OT_EDGES v1\nT t_st_b1__clk 33.5 31.0 18\nF t_st_b1__clk 450.0 447.5 19\n"
                   "T t_st_b2__clk 61.25 57.0 19\nF t_st_b2__clk 470.5 466.0 20\nM b0 1 1\n")
    taps = DSR.load_taps(E.proof_with_stages(pr, doc, {"TT": arr}, tmp_path / "p2"), "TT")[1]
    k = f"__st__{P_L}"
    assert taps[k]["late_ps"] == 61.25 and taps[k]["fall_late_ps"] == 470.5 and taps[k]["fall_early_ps"] == 466.0
    assert taps[f"__st__{P_ROOT}"]["fall_late_ps"] == 450.0
    arr.write_text("T t_st_b1__clk 33.5 31.0 18\nT t_st_b2__clk 61.25 57.0 19\n")
    taps = DSR.load_taps(E.proof_with_stages(pr, doc, {"TT": arr}, tmp_path / "p3"), "TT")[1]
    assert "fall_late_ps" not in taps[k]


def test_rejects_non_stage_virtual_region_and_missing_node():
    v, t = _tree()
    b = _bind()
    b["regions"]["x"] = dict(parent=None, tree_port=None, virtual=True)
    with pytest.raises(E.StageError):
        E.emit(b, _meta(), v, t)
    m = _meta()
    del m["node_cell"][P_L]
    with pytest.raises(E.StageError):
        E.emit(_bind(), m, v, t)
    with pytest.raises(E.StageError):
        E.path_id("hx")


def test_explicit_die_trial_base36_path_labels():
    assert E.path_id('h', 'base36') == 'h'
    assert E.path_id('h0az', 'base36') == 'h_0_10_35'
    with pytest.raises(E.StageError):
        E.path_id('h0a')
    with pytest.raises(E.StageError):
        E.path_id('hA', 'base36')


def test_source_specific_retime_stages_keep_distinct_physical_pins(tmp_path):
    import copy
    b = _bind()
    old = f'st:{P_L}'
    new = old + '@origin2'
    b['regions'][new] = dict(b['regions'][old], tree_port=f'start:st:{P_ROOT}->{new}')
    b['start_ports'][b['regions'][new]['tree_port']] = dict(src=f'st:{P_ROOT}', dst=new,
                                                           launch_part=None, capture_part=None)
    v, t = _tree()
    doc, sv, _, _ = E.emit(b, _meta(), v, t)
    a, c = [next(x for x in doc['stages'] if x['region'] == n) for n in (old, new)]
    assert a['node_cell'] == c['node_cell'] and a['clock_net'] == c['clock_net']
    assert a['id'] != c['id'] and a['clock_port'] != c['clock_port']
    assert a['rect_um'] != c['rect_um']
    src = tmp_path/'src'
    src.mkdir()
    (src/'tap_arrivals_TT.json').write_text(json.dumps(_meta()))
    arr = tmp_path/'arr'
    arr.write_text(''.join(f"T {s['clock_port']} {100+i} {90+i}\nF {s['clock_port']} {110+i} {95+i}\n"
                           for i,s in enumerate(doc['stages'])))
    E.proof_with_stages(src, doc, {'TT':str(arr)}, tmp_path/'out')
    ts = {x['port']:x for x in json.loads((tmp_path/'out/tap_arrivals_TT.json').read_text())['taps']}
    aa, cc = ts[f'__st__{P_L}'], ts[f'__st__{P_L}@origin2']
    assert aa['tree_path'] == cc['tree_path'] == P_L
    assert aa['late_ps'] != cc['late_ps'] and aa['xy_um'] != cc['xy_um']
def test_real_partition_root_drives_virtual_stages_without_duplicate_counter():
    b = _bind()
    root = f"st:{P_ROOT}"
    b["regions"]["hub_C"] = b["regions"].pop(root)
    b["regions"]["hub_C"]["virtual"] = False
    b["root"] = "hub_C"
    for r in b["regions"].values():
        if r.get("parent") == root:
            r["parent"] = "hub_C"
    for c in b["start_ports"].values():
        if c["src"] == root:
            c["src"] = "hub_C"
    v, t = _tree()
    doc, sv, _, _ = E.emit(b, _meta(), v, t)
    assert doc["counts"]["stages"] == 1
    assert all(not r["root"] for r in doc["stages"])
    assert "ot_dp_landing_root #" not in sv
    assert "input  wire rs_hub_C" in sv and ".p_start(rs_hub_C)" in sv
    assert {r["net"] for r in doc["die_inputs"]} == {"rs_hub_C"}
    for invalid in ({}, {"virtual": True, "parent": None}, {"virtual": False, "parent": "other"}):
        b["regions"]["hub_C"] = invalid
        with pytest.raises(E.StageError):
            E.emit(b, _meta(), v, t)


def _real_root_bind():
    b = _bind()
    root = f'st:{P_ROOT}'
    b['root'] = 'hub_C'
    b['regions']['hub_C'] = dict(b['regions'].pop(root), virtual=False)
    for r in b['regions'].values():
        if r.get('parent') == root:r['parent'] = 'hub_C'
    for e in b['start_ports'].values():
        if e['src'] == root:e.update(src='hub_C', launch_part='hub_C')
    return b


def test_bounded_reset_removes_global_star_and_counts_ordinary_relays():
    v,t = _tree()
    d,sv,*_ = E.emit(_real_root_bind(), _meta(),v,t,reset_wave=True)
    assert 'input  wire rst_raw_n' not in sv
    assert 'input  wire rraw_hub_C' in sv and '.rst_raw_n(st_b2_rraw)' in sv
    assert d['counts']['flops'] == 9  # original 3+PAD2+fall1, reset2+fall1
    assert d['stages'][0]['reset_flops'] == 3
    assert 'async_reg' not in sv and 'negedge rst' not in sv
    assert d['reset_inputs'] == [dict(region='hub_C',part='hub_C',net='rraw_hub_C')]
    d,sv,*_ = E.emit(_bind(),_meta(),v,t,reset_wave=True)
    assert sv.count('.rst_raw_n(rst_raw_n)') == 1  # virtual root only, no global reset star
    assert '.rst_raw_n(st_b2_rraw)' in sv


def test_bounded_reset_cold_warm_protocol_and_bad_parent_control(tmp_path):
    import subprocess,shutil
    iv=shutil.which('iverilog')
    if iv is None:pytest.skip('iverilog not installed')
    v,t=_tree();b=_real_root_bind()
    _,ref,*_=E.emit(b,_meta(),v,t)
    _,wave,*_=E.emit(b,_meta(),v,t,reset_wave=True)
    ref=ref.replace('module ot_die_start_stages','module reference_stages')
    # Root uses its delivered synchronous reset, START settle 8 edges. Assert is
    # held 12 edges for cold and warm reset: longer than the 3-edge relay+PAD flush.
    tb='''module tb;
reg clk=0, raw=0;reg parent_raw=0;wire parent_start,a,g;
integer compares=0,errors=0;
always #5 clk=~clk;
always @(posedge clk) parent_raw<=raw;
ot_dp_landing_root #(.SETTLE(8)) root(.clk(clk),.rst_raw_n(parent_raw),.start(parent_start));
reference_stages ref0(.rst_raw_n(parent_raw),.t_st_b2__clk(clk),.rs_hub_C(parent_start),.pst_a(g));
ot_die_start_stages dut(.rraw_hub_C(parent_raw),.t_st_b2__clk(clk),.rs_hub_C(parent_start),.pst_a(a));
always @(posedge clk) begin #1;if(raw)begin compares=compares+1;if(a!==g)errors=errors+1;end end
initial begin repeat(12)@(negedge clk);raw=1;repeat(60)@(negedge clk);raw=0;
repeat(12)@(negedge clk);raw=1;repeat(60)@(negedge clk);
$display("COMPARES %0d ERRORS %0d",compares,errors);if(errors)$fatal(1,"mismatch");$finish;end
endmodule\n'''
    common=Path(__file__).resolve().parents[2]/'rtl/common/ot_dp_clk_landing_ca.sv'
    (tmp_path/'ref.sv').write_text(ref);(tmp_path/'tb.sv').write_text(tb)
    results=[]
    for mutant in (False,True):
        # A wrong parent contract feeds START in place of delivered reset. It
        # releases the local reset late and changes the first valid start edge.
        candidate=wave.replace('.d(rraw_hub_C)', '.d(rs_hub_C)') if mutant else wave
        (tmp_path/'dut.sv').write_text(candidate)
        p=subprocess.run([iv,'-g2012','-s','tb','-o',str(tmp_path/'sim'),str(common),str(tmp_path/'ref.sv'),str(tmp_path/'dut.sv'),str(tmp_path/'tb.sv')],capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        q=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True)
        results.append(q)
    assert results[0].returncode==0,results[0].stdout+results[0].stderr
    assert results[1].returncode!=0 and 'mismatch' in results[1].stdout


def test_virtual_root_reset_cold_warm_phase_coupon_and_undriven_control(tmp_path):
    import subprocess,shutil
    iv=shutil.which('iverilog')
    if iv is None:pytest.skip('iverilog not installed')
    v,t=_tree();b=_bind()
    _,ref,*_=E.emit(b,_meta(),v,t,root_settle=8)
    doc,wave,*_=E.emit(b,_meta(),v,t,root_settle=8,reset_wave=True)
    assert 'wire st_b1_rraw = rst_raw_n;' in wave
    assert next(s for s in doc['stages'] if s['root'])['reset_output']=='st_b1_rraw'
    ref=ref.replace('module ot_die_start_stages','module reference_stages')
    common=Path(__file__).resolve().parents[2]/'rtl/common/ot_dp_clk_landing_ca.sv'
    (tmp_path/'ref.sv').write_text('`default_nettype none\n'+ref)
    for phase in (0,2,4,7):
        tb=f'''module tb;
reg clk=0,child=0,raw=0; wire a,b,ga,gb; integer errors=0,compares=0;
always #5 clk=~clk;
initial begin #{phase};forever #5 child=~child;end
reference_stages ref0(.rst_raw_n(raw),.t_st_b1__clk(clk),.t_st_b2__clk(child),.pst_a(ga),.pst_b(gb));
ot_die_start_stages dut(.rst_raw_n(raw),.t_st_b1__clk(clk),.t_st_b2__clk(child),.pst_a(a),.pst_b(b));
always @(posedge child) begin #1;if(raw)begin compares=compares+1;if(a!==ga || b!==gb)errors=errors+1;end end
initial begin repeat(12)@(negedge clk);raw=1;repeat(60)@(negedge clk);raw=0;
repeat(12)@(negedge clk);raw=1;repeat(60)@(negedge clk);
$display("COMPARES %0d ERRORS %0d",compares,errors);if(errors)$fatal(1,"mismatch");$finish;end
endmodule\n'''
        (tmp_path/'tb.sv').write_text(tb)
        for mutant in ('nominal','missing_alias','wrong_parent'):
            candidate=wave
            if mutant=='missing_alias':candidate=candidate.replace('wire st_b1_rraw = rst_raw_n;','')
            if mutant=='wrong_parent':candidate=candidate.replace('.d(st_b1_rraw)', '.d(st_b1_start)')
            (tmp_path/'dut.sv').write_text('`default_nettype none\n'+candidate)
            p=subprocess.run([iv,'-g2012','-Wimplicit','-s','tb','-o',str(tmp_path/'sim'),str(common),str(tmp_path/'ref.sv'),str(tmp_path/'dut.sv'),str(tmp_path/'tb.sv')],capture_output=True,text=True)
            if mutant=='missing_alias':
                assert p.returncode!=0 and 'st_b1_rraw' in p.stderr
                continue
            assert p.returncode==0,p.stderr
            assert 'implicit' not in p.stderr.lower(),p.stderr
            q=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True)
            if mutant=='nominal':assert q.returncode==0,q.stdout+q.stderr
            else:assert q.returncode!=0 and 'mismatch' in q.stdout


def test_actual_clock_driver_path_and_root_input_have_no_extra_inv_credit(tmp_path, monkeypatch):
    v, t = _tree('INVx1_ASAP7_75t_R')
    b = _bind()
    b['regions']['st:h'] = dict(parent=None, virtual=True, pad=0, edge_fall=False)
    # Keep a single virtual root; make the old root its child.
    b['regions'][f'st:{P_ROOT}']['parent'] = 'st:h'
    b['start_ports']['root_to_child'] = dict(src='st:h', dst=f'st:{P_ROOT}')
    doc, *_ = E.emit(b, _meta(), v, t)
    stages = {s['region']: s for s in doc['stages']}
    assert stages['st:h']['clock_source_path'] == '__source__'
    assert stages['st:h']['clock_source_stages'] == 0
    assert stages[f'st:{P_ROOT}']['clock_source_path'] == P_ROOT  # two inversions: Y
    assert stages[f'st:{P_L}']['clock_source_path'] == P_ROOT  # three inversions: A, driven by b1
    assert stages[f'st:{P_L}']['node_cell'] == 'b2'  # physical identity stays at b2
    pr = tmp_path/'p'; pr.mkdir()
    (pr/'tap_arrivals_TT.json').write_text(json.dumps(_meta()))
    arr = tmp_path/'arr'
    arr.write_text(''.join(f"T {s['clock_port']} 60 50\n" for s in doc['stages']))
    meta, taps = DSR.load_taps(E.proof_with_stages(pr, doc, {'TT': arr}, tmp_path/'out'), 'TT')
    root, a, y = (taps['__st__'+x] for x in ('h', P_L, P_ROOT))
    monkeypatch.setattr(DSR, 'CPPR_LCA', True)
    assert a['tree_path'] == P_ROOT and a['stages_from_root'] == 2
    assert a['leaf_cell'] == 'b1' and a['placement_cell'] == 'b2'
    assert root['leaf_cell'] is None
    assert DSR.pair_node(a, y) == P_ROOT
    assert DSR.pair_node(root, a) == '__source__'
    assert meta['node_stages']['__source__'] == 0
    assert meta['cppr_node_range_ps']['__source__'] == 0
    # Mutant source path would improperly credit b2 and an extra clock stage.
    assert a['tree_path'] != P_L and a['stages_from_root'] != 3
    legacy = json.loads(json.dumps(doc))
    for s in legacy['stages']:
        s.pop('clock_source_path')
    with pytest.raises(E.StageError, match='re-emit'):
        E.proof_with_stages(pr, legacy, {'TT': arr}, tmp_path/'legacy')


def test_node_cell_region_alias_is_not_a_second_clock_path():
    v, t = _tree('INVx1_ASAP7_75t_R')
    meta = _meta()
    meta['node_cell']['hub_C'] = 'b0'
    doc, *_ = E.emit(_bind(), meta, v, t)
    assert next(s for s in doc['stages'] if s['node_cell'] == 'b2')['clock_source_path'] == P_ROOT


def test_current_native_home_converter_ot_place():
    v, t = _tree()
    native = re.sub(r'place_inst -name (\S+) -location \{([-\d.]+) ([-\d.]+)\} -status PLACED',
                    r'ot_place {\1} \2 \3 R0', t)
    assert E.ctree_cells(v, native) == E.ctree_cells(v, t)
    doc, *_ = E.emit(_bind(), _meta(), v, native)
    assert len(doc['stages']) == 2
