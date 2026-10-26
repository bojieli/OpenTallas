import copy
import json
import subprocess
from pathlib import Path

import pytest
import core_infra as CI
import master_slice as MS
from test_master_slice import good_slice


def sample():
    sl = good_slice(kind="core", outline_um=[864,864], bays=[], entry_pins=[])
    sl["core_clock_port"] = "clk"
    sl["pushdown"] = {"islands": [{"name": "isl0", "centre_um": [432,432], "rect_um": [427.68,427.68,436.32,436.32],
        "driver": {"cell": "BUFx16f_ASAP7_75t_R", "parallel": 1}, "ft_ports": [
        {"name": "mp_isl0_ck_i", "dir": "in", "layer": "M5", "xy_um": [429.84,434.16]},
        {"name": "mp_isl0_ck_o", "dir": "out", "layer": "M5", "xy_um": [434.16,434.16]},
        {"name": "mp_isl0_rst_i", "dir": "in", "layer": "M5", "xy_um": [429.84,429.84]},
        {"name": "mp_isl0_rst_o", "dir": "out", "layer": "M5", "xy_um": [434.16,429.84]}]}]}
    return sl


def test_feedthroughs_and_no_island_hole(tmp_path):
    sl = sample()
    p = CI.compile_slice(sl)
    assert len(p["cells"]) == 2 and len(p["ports"]) == 4
    assert {c["master"] for c in p["cells"]} == {"BUFx16f_ASAP7_75t_R", "BUFx4_ASAP7_75t_R"}
    tcl = MS.emit_tcl(sl)
    assert "# placement blockage: island" not in tcl
    assert "# placement blockage: keepout isl_c" not in tcl
    assert "source /work/master_core_infra.tcl" in tcl
    assert CI.install(tmp_path, sl)
    assert (tmp_path / "native_pg_binding.tcl").exists()
    assert "ot_ci_arc {mp_isl0_ck0} {mp_isl0_ck_i} {mp_isl0_ck_o}" in (tmp_path / "master_core_infra.tcl").read_text()


@pytest.mark.parametrize("mut,frag", [
    (lambda s: s["pushdown"]["islands"][0]["driver"].update(cell="INVx1_ASAP7_75t_R"), "polarity"),
    (lambda s: s["pushdown"]["islands"][0]["ft_ports"][0].update(dir="out"), "directions"),
    (lambda s: s["pushdown"]["islands"][0]["ft_ports"][0].update(xy_um=[900,1]), "outside"),
    (lambda s: s["pushdown"]["islands"][0]["driver"].update(parallel=0), "positive"),
    (lambda s: s.update(bays=[dict(name="b", bits=16)]), "assignments"),
])
def test_mutant_refused_before_kit_write(tmp_path, mut, frag):
    sl = sample(); mut(sl)
    with pytest.raises(CI.InfraError, match=frag): CI.install(tmp_path, sl)
    assert list(tmp_path.iterdir()) == []


def test_tree_assignments_are_explicit_equal_depth_and_equal_load():
    s = sample()
    s["core_tree"] = {"clock_port": "ck", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[430,430], parent="port:ck"),
        dict(name="n0", master="BUFx8_ASAP7_75t_R", xy_um=[200,200], parent="root"),
        dict(name="n1", master="BUFx8_ASAP7_75t_R", xy_um=[600,600], parent="root")],
        "leaves": [dict(node="n0", sinks=["u0/CLK", "u1/CLK"]), dict(node="n1", sinks=["u2/CLK", "u3/CLK"])]}
    s["pg_obstructions_um"] = {}          # explicit: no macro PG on the trunk layers
    tcl = CI.emit_tcl(s)
    assert "ot_ci_tree_sink {n0} {u0/CLK}" in tcl and "nearest" not in tcl
    assert CI.compile_slice(s)["core_tree"]["depth"] == 2
    bad = copy.deepcopy(s); bad["core_tree"]["leaves"][1]["sinks"][0] = "u0/CLK"
    with pytest.raises(CI.InfraError, match="twice"): CI.compile_slice(bad)
    bad = copy.deepcopy(s); bad["core_tree"]["nodes"][2]["parent"] = "port:ck"
    with pytest.raises(CI.InfraError, match="stage"): CI.compile_slice(bad)
    bad = copy.deepcopy(s); bad["core_tree"]["leaves"][1]["sinks"] += ["u4/CLK", "u5/CLK"]
    with pytest.raises(CI.InfraError, match="unequal"): CI.compile_slice(bad)


def test_tcl_library_has_no_parse_error():
    p = subprocess.run(["tclsh"], input=(Path(CI.__file__).with_suffix(".tcl").read_text() + "\nputs CORE_INFRA_TCL_PARSED\n"),
                       text=True, capture_output=True)
    assert p.returncode == 0 and "CORE_INFRA_TCL_PARSED" in p.stdout and not p.stderr


def test_rtl_wrapper_keeps_logic_and_feedthroughs_separate():
    s = sample()
    v = CI.emit_wrapper(s, "logic_only", {"clk": {"direction": "input"}, "rst_n": {"direction": "input"},
        "d": {"direction": "input", "width": 16}, "q": {"direction": "output", "width": 16}})
    logic_line = next(line for line in v.splitlines() if "u_logic" in line)
    assert ".clk(clk)" in logic_line and ".rst_n(rst_n)" in logic_line and "mp_isl" not in logic_line
    assert "output wire [15:0] q" in v and "always" not in v
    assert '.A(mp_isl0_rst_i), .Y(mp_isl0_rst_o)' in v
    with pytest.raises(CI.InfraError, match="already uses"):
        CI.emit_wrapper(s, "logic_only", {"mp_isl0_rst_i": {"direction":"input"}})


def test_separate_core_and_feedthrough_pins_cannot_overlap():
    s=sample()
    s["pushdown"]["islands"][0]["ft_ports"][0]["xy_um"]=[432,432]
    with pytest.raises(CI.InfraError, match="pin shapes overlap"): CI.compile_slice(s)


def test_kit_manifest_binds_clock_without_rewriting_slice(tmp_path):
    s = sample(); s.pop("core_clock_port")
    src = tmp_path/"slices"; src.mkdir()
    path = src / (s["type"]+".json")
    path.write_text(json.dumps(s, indent=1))
    kd = tmp_path/"kit";kd.mkdir()
    stamp = MS.kit_apply(kd,s["type"],s["outline_um"],src,clock_ports=["clk"],reset_ports=["rst_n"])
    assert stamp["slice_sha256"] == MS.digest(s)
    assert (kd/"master_slice.json").read_bytes() == path.read_bytes()
    assert "ot_ci_clock_entry {clk}" in (kd/"master_core_infra.tcl").read_text()
    with pytest.raises(MS.SliceError,match="exactly one"):
        MS.kit_apply(kd,s["type"],s["outline_um"],src,clock_ports=["ck","other"])


def test_wrapper_preserves_original_packed_bus_range():
    s=sample()
    v=CI.emit_wrapper(s,"logic_only",{"d":{"direction":"input","width":8,"offset":4,"upto":True}})
    assert "input wire [4:11] d" in v


def test_tcl_word_preserves_real_yosys_sink_identity():
    import tkinter
    interp=tkinter.Tcl()
    name=r"c1_off\[0\]$_DFF_P_/CLK"
    assert interp.eval("set x "+CI.word(name)) == name
    with pytest.raises(CI.InfraError): CI.word("unsafe"+chr(92))


def icg_tree():
    s = sample()
    s["pg_obstructions_um"] = {}
    s["core_tree"] = {"clock_port": "ck", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[432, 432], parent="port:ck"),
        dict(name="w", master="BUFx12_ASAP7_75t_R", xy_um=[216, 432], parent="root"),
        dict(name="e", master="BUFx12_ASAP7_75t_R", xy_um=[648, 432], parent="root"),
        dict(name="tw", master="BUFx8_ASAP7_75t_R", xy_um=[216, 433], parent="w"),
        dict(name="te", master="BUFx8_ASAP7_75t_R", xy_um=[648, 433], parent="e")],
        "gates": [dict(inst="u_e.g_cgr.u_cg_r0.u_icg", master="ICGx1_ASAP7_75t_R", parent="w", xy_um=[216, 430]),
                  dict(inst="u_e.g_cgr.u_cg_r1.u_icg", master="ICGx1_ASAP7_75t_R", parent="e", xy_um=[648, 430])],
        "leaves": [dict(node="u_e.g_cgr.u_cg_r0.u_icg", load_class="gated_domain", domain_sinks=6000),
                   dict(node="u_e.g_cgr.u_cg_r1.u_icg", load_class="gated_domain", domain_sinks=5800),
                   dict(node="tw", sinks=["a/CLK", "b/CLK"], cts_open=True, domain_sinks=1500),
                   dict(node="te", sinks=["c/CLK", "d/CLK"], cts_open=True, domain_sinks=1500)]}
    return s


def test_icg_gates_are_equal_depth_tree_stages_with_open_domains():
    s = icg_tree()
    p = CI.compile_slice(s)["core_tree"]
    assert p["depth"] == 3 and len(p["gates"]) == 2
    assert p["cts_open"] == ["te", "tw", "u_e.g_cgr.u_cg_r0.u_icg", "u_e.g_cgr.u_cg_r1.u_icg"]
    tcl = CI.emit_tcl(s)
    assert "ot_ci_tree_gate {u_e.g_cgr.u_cg_r0.u_icg} ICGx1_ASAP7_75t_R {w} {CLK} {GCLK} 216 430" in tcl
    assert "ot_ci_tree_domain {u_e.g_cgr.u_cg_r1.u_icg} 5800" in tcl and "ot_ci_tree_open {tw}" in tcl
    # gates hang from a node, not the port, and are not created cells
    assert not any(c["name"].startswith("u_e") for c in CI.compile_slice(s)["cells"])


@pytest.mark.parametrize("mut,frag", [
    (lambda t: t["gates"][0].update(parent="root"), "unequal stage"),
    (lambda t: t["gates"][0].update(parent="port:ck"), "planned root only"),
    (lambda t: t["gates"][0].update(master="BUFx4_ASAP7_75t_R"), "ICG master"),
    (lambda t: t["leaves"].pop(0), "without a gated_domain"),
    (lambda t: t["leaves"][0].update(sinks=["x/CLK"]), "stay on the gate"),
    (lambda t: t["leaves"][2].update(domain_sinks=20), "local stage counts"),
    (lambda t: t["gates"].append(dict(t["gates"][0])), "duplicate"),
])
def test_icg_tree_mutants_refused(mut, frag):
    s = icg_tree(); mut(s["core_tree"])
    with pytest.raises(CI.InfraError, match=frag):
        CI.emit_tcl(s)
