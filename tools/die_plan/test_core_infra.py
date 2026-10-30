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
    with pytest.raises(MS.SliceError,match="needs a slice with clock_entries"):  # R21: two root pins, single-entry slice
        MS.kit_apply(kd,s["type"],s["outline_um"],src,clock_ports=["ck","other"])


def test_wrapper_preserves_original_packed_bus_range():
    s=sample()
    v=CI.emit_wrapper(s,"logic_only",{"d":{"direction":"input","width":8,"offset":4,"upto":True}})
    assert "input wire [4:11] d" in v


def _tcl_eval_set(word):
    """value Tcl gives `set x <word>`: tkinter when the interpreter has it, else the system tclsh (the fleet
    pytest venv python has no _tkinter); skip only when neither Tcl is present."""
    try:
        import tkinter
        return tkinter.Tcl().eval("set x "+word)
    except ImportError:
        import shutil, subprocess
        tclsh=shutil.which("tclsh") or shutil.which("tclsh8.6")
        if not tclsh:
            pytest.skip("no Tcl interpreter (tkinter or tclsh)")
        r=subprocess.run([tclsh],input="puts -nonewline [set x "+word+"]\n",capture_output=True,text=True,check=True)
        return r.stdout


def test_tcl_word_preserves_real_yosys_sink_identity():
    name=r"c1_off\[0\]$_DFF_P_/CLK"
    assert _tcl_eval_set(CI.word(name)) == name
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


# ---- S81-CORE-LAT-R7: clock-gate copies on the same registered enable (COORD ruling R6 (3))
def icg_copy_tree():
    s = icg_tree()
    t = s["core_tree"]
    t["nodes"] += [dict(name="w2", master="BUFx12_ASAP7_75t_R", xy_um=[216, 300], parent="root")]
    t["gates"].append(dict(inst="ot_cgc_r0_1", clone_of="u_e.g_cgr.u_cg_r0.u_icg", master="ICGx1_ASAP7_75t_R",
                           parent="w2", xy_um=[216, 298], members=[f"m{i}/CLK" for i in range(600)]))
    t["leaves"].append(dict(node="ot_cgc_r0_1", load_class="gated_domain", domain_sinks=600))
    return s


def test_gate_copy_reads_original_enable_and_takes_named_members():
    s = icg_copy_tree()
    p = CI.compile_slice(s)["core_tree"]
    g = {x["inst"]: x for x in p["gates"]}
    assert g["ot_cgc_r0_1"]["enable_pins"] == ["ENA", "SE"] and g["u_e.g_cgr.u_cg_r0.u_icg"]["copies"] == ["ot_cgc_r0_1"]
    assert p["depth"] == 3
    tcl = CI.emit_tcl(s)
    line = ("ot_ci_tree_gate_copy {ot_cgc_r0_1} ICGx1_ASAP7_75t_R {u_e.g_cgr.u_cg_r0.u_icg} {w2} {CLK} {GCLK} 216 298 "
            "{0 0 864 864} {{ENA} {SE}} {" + " ".join("{m%d/CLK}" % i for i in range(600)) + "}")
    assert line in tcl
    # copies after every original gate, the domain census after the copies, the LEC netlist after the tree
    assert tcl.index("ot_ci_tree_gate {u_e.g_cgr.u_cg_r1.u_icg}") < tcl.index(line) < tcl.index("ot_ci_tree_domain")
    assert tcl.index("ot_ci_tree_finish") < tcl.index("ot_ci_lec_netlist /work/core_infra_post.v")
    assert "ot_ci_lec_netlist" not in CI.emit_tcl(icg_tree())


def _copy(t):
    return t["gates"][-1]


@pytest.mark.parametrize("mut,frag", [
    (lambda t: _copy(t).update(clone_of="nope"), "original RTL gate listed before"),
    (lambda t: _copy(t).update(master="ICGx2_ASAP7_75t_R"), "differs from"),
    (lambda t: _copy(t).update(members=[]), "non-empty list"),
    (lambda t: _copy(t).update(members=["m0/CLK", "m0/CLK"]), "distinct"),
    (lambda t: _copy(t).update(enable_pins=["CLK"]), "non-clock pins"),
    (lambda t: _copy(t).update(parent="root"), "unequal stage"),
    (lambda t: t["leaves"][-1].update(domain_sinks=601), "exactly its 600 members"),
    (lambda t: t["leaves"][2]["sinks"].append("m1/CLK"), "gate-copy member and a direct leaf"),
    (lambda t: t["gates"][0].update(members=["x/CLK"]), "only a gate copy"),
    (lambda t: t["gates"].append(dict(_copy(t), inst="ot_cgc_r0_2", clone_of="ot_cgc_r0_1")), "original RTL gate"),
    (lambda t: t["gates"].append(dict(_copy(t), inst="ot_cgc_r0_2", members=["m2/CLK"] * 1)), "two gate copies"),
])
def test_gate_copy_mutants_refused(mut, frag):
    s = icg_copy_tree(); mut(s["core_tree"])
    with pytest.raises(CI.InfraError, match=frag):
        CI.emit_tcl(s)


def test_cts_hook_written_with_plan_open_count(tmp_path):
    # S81-CORE-LAT-R12 (ODB-0370): a plan tree kit gets the PRE_CTS hook; leaf-complete tree -> 0 CTS-open nets
    s = sample()
    s["core_tree"] = {"clock_port": "clk", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[430,430], parent="port:clk"),
        dict(name="n0", master="BUFx8_ASAP7_75t_R", xy_um=[200,200], parent="root"),
        dict(name="n1", master="BUFx8_ASAP7_75t_R", xy_um=[600,600], parent="root")],
        "leaves": [dict(node="n0", sinks=["u0/CLK", "u1/CLK"]), dict(node="n1", sinks=["u2/CLK", "u3/CLK"])]}
    s["pg_obstructions_um"] = {}
    assert CI.install(tmp_path, s)
    hook = (tmp_path / CI.CTS_HOOK).read_text()
    assert "set ::ot_ci_cts_plan_open 0\n" in hook and "TritonCTS not run" in hook
    assert CI.emit_cts_tcl(CI.compile_slice(icg_tree())).count("set ::ot_ci_cts_plan_open 4\n") == 1
    # parses with a stand-in TritonCTS command; the wrapper replaces it exactly once
    prog = "proc clock_tree_synthesis {args} {}\n" + hook + hook + \
        "\nputs [llength [info commands ::ot_ci_tritoncts]]\nputs CTS_HOOK_PARSED\n"
    r = subprocess.run(["tclsh"], input=prog, text=True, capture_output=True)
    assert r.returncode == 0 and r.stdout.split() == ["1", "CTS_HOOK_PARSED"] and not r.stderr


def test_no_cts_hook_without_plan_tree(tmp_path):
    assert CI.install(tmp_path, sample())
    assert not (tmp_path / CI.CTS_HOOK).exists()


def test_installed_clock_entry_uses_same_track_and_access_as_kit_io(tmp_path):
    # Regression: the later pushdown hook used to undo io.tcl's track snap and
    # via-access shape, causing DRT-0255 at the centre clock entry.
    sl = sample()
    original = copy.deepcopy(sl)
    (tmp_path / "make_tracks.tcl").write_text(
        "make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048\n")
    CI.install(tmp_path, sl)
    p = json.loads((tmp_path / "core_infra_plan.json").read_text())
    assert p["clock_entry"]["xy_um"] == [432.012, 432.0]
    assert "ot_ci_clock_entry {clk} 432.012 432" in (tmp_path / "master_core_infra.tcl").read_text()
    impl = (tmp_path / "core_infra_impl.tcl").read_text()
    clock_proc = impl.split("proc ot_ci_clock_entry", 1)[1].split("proc ot_ci_port", 1)[0]
    assert "-pin_size {0.048 0.48}" in clock_proc
    assert sl == original  # the frozen slice stays byte-identical
    # A kit with a nondefault track grid must use that exact grid as io.tcl does.
    (tmp_path / "make_tracks.tcl").write_text(
        "make_tracks M5 -x_offset 0.02 -x_pitch 0.08 -y_offset 0.012 -y_pitch 0.048\n")
    CI.install(tmp_path, sl)
    assert json.loads((tmp_path / "core_infra_plan.json").read_text())["clock_entry"]["xy_um"] == [432.02, 432.0]


@pytest.mark.parametrize("cell,n,pitch", [("BUFx24_ASAP7_75t_R", 3, 1.674), ("BUFx16f_ASAP7_75t_R", 2, 1.242),
                                          ("BUFx12f_ASAP7_75t_R", 3, 1.08), ("BUFx4_ASAP7_75t_R", 4, 1.08)])
def test_parallel_island_drivers_never_overlap(cell, n, pitch):
    """HBM-CORES-REBAL-1: SM/programme_store islands (3 x BUFx24 at the fixed 1.08 um pitch) hit
    OT_CORE_INFRA_PLANNED_OVERLAP; the pitch now clears the footprint, legacy 1.08 kept where it already fits."""
    s = sample(); s["pushdown"]["islands"][0]["driver"].update(cell=cell, parallel=n)
    ck = sorted((c for c in CI.compile_slice(s)["cells"] if "_ck" in c["name"]), key=lambda c: c["xy_um"][0])
    assert len(ck) == n
    w = CI.BUF_WIDTH_UM[cell.split("_ASAP7")[0]]
    for a, b in zip(ck, ck[1:]):
        assert b["xy_um"][0] - a["xy_um"][0] == pytest.approx(pitch)
        assert b["xy_um"][0] - a["xy_um"][0] >= w + CI.SITE_UM - 1e-9 or pitch == CI.PARALLEL_PITCH_UM
        assert b["xy_um"][0] - a["xy_um"][0] > w
    assert sum(c["xy_um"][0] for c in ck) / n == pytest.approx(432)


def test_driver_rect_places_drivers_in_channel_pins_unchanged():
    """HBM-CORES-REBAL-5: island driver_rect_um (master_plan.pushdown_island driver_rect) -> the ck/rst drivers are
    centred in that rect (their OT_CORE_INFRA_PLANNED_OVERLAP footprint is the channel, not the SRAM under the island),
    the ft ports, arcs and pin coordinates are unchanged; a rect outside the core is refused."""
    base = CI.compile_slice(sample())
    s = sample()
    s["pushdown"]["islands"][0]["driver_rect_um"] = [450.0, 427.68, 458.64, 436.32]
    p = CI.compile_slice(s)
    assert p["ports"] == base["ports"] and p["arcs"] == base["arcs"]
    for c in p["cells"]:
        assert 450.0 <= c["xy_um"][0] <= 458.64 and 427.68 <= c["xy_um"][1] <= 436.32
        assert c["rect_um"] == [450.0, 427.68, 458.64, 436.32]
    assert sorted(c["xy_um"][0] for c in p["cells"]) == [454.32, 454.32]
    assert [c["xy_um"][1] - b["xy_um"][1] for c, b in zip(p["cells"], base["cells"])] == [0, 0]
    s["pushdown"]["islands"][0]["driver_rect_um"] = [860.0, 427.68, 868.64, 436.32]
    with pytest.raises(CI.InfraError, match="outside"):
        CI.compile_slice(s)
    s["pushdown"]["islands"][0]["driver_rect_um"] = [458.64, 427.68, 450.0, 436.32]
    with pytest.raises(CI.InfraError, match="driver_rect_um"):
        CI.compile_slice(s)


# ---- CORES-EARLY-5 form C: ICG copy as a PLANNED stage (domain "planned"), planned leaves below the gate
def icg_planned_tree():
    s = sample()
    s["pg_obstructions_um"] = {}
    g0 = "u_e.g_cgr.u_cg_r0.u_icg"
    s["core_tree"] = {"clock_port": "ck", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[432, 432], parent="port:ck"),
        dict(name="w", master="BUFx12_ASAP7_75t_R", xy_um=[216, 432], parent="root"),
        dict(name="e", master="BUFx12_ASAP7_75t_R", xy_um=[648, 432], parent="root"),
        dict(name="bw", master="BUFx8_ASAP7_75t_R", xy_um=[216, 500], parent="w"),
        dict(name="lw", master="BUFx8_ASAP7_75t_R", xy_um=[216, 520], parent="bw"),
        dict(name="lg0", master="BUFx8_ASAP7_75t_R", xy_um=[216, 400], parent=g0),
        dict(name="lc1", master="BUFx8_ASAP7_75t_R", xy_um=[648, 400], parent="ot_cgc_r0_1")],
        "gates": [dict(inst=g0, master="ICGx1_ASAP7_75t_R", parent="w", xy_um=[216, 420], domain="planned"),
                  dict(inst="ot_cgc_r0_1", clone_of=g0, master="ICGx1_ASAP7_75t_R", parent="e", xy_um=[648, 420],
                       members=["m0/CLK", "m1/CLK"], domain="planned")],
        "leaves": [dict(node="lw", sinks=["u0/CLK", "u1/CLK"]), dict(node="lg0", sinks=["a/CLK", "b/CLK"]),
                   dict(node="lc1", sinks=["m0/CLK", "m1/CLK"])]}
    return s


def test_planned_domain_gates_drive_planned_leaves():
    s = icg_planned_tree()
    p = CI.compile_slice(s)["core_tree"]
    assert p["depth"] == 4 and p["under_gate"] == {"lg0": "u_e.g_cgr.u_cg_r0.u_icg", "lc1": "ot_cgc_r0_1"}
    assert p["cts_open"] == []
    tcl = CI.emit_tcl(s)
    copy = tcl.index("ot_ci_tree_gate_copy {ot_cgc_r0_1}")
    pl0 = tcl.index("ot_ci_tree_gate_planned {u_e.g_cgr.u_cg_r0.u_icg}")
    pl1 = tcl.index("ot_ci_tree_gate_planned {ot_cgc_r0_1}")
    # copies first, then the planned-domain census, then the nodes below the gates, then the leaf sinks
    assert copy < pl0 < pl1 < tcl.index("ot_ci_tree_node {lg0} {u_e.g_cgr.u_cg_r0.u_icg}") < tcl.index("ot_ci_tree_sink {lg0} {a/CLK}")
    assert tcl.index("ot_ci_tree_node {lw} {bw}") < copy
    assert "ot_ci_tree_domain" not in tcl and "ot_ci_lec_netlist /work/core_infra_post.v" in tcl


def test_open_gate_trees_emit_unchanged_without_planned_lines():
    assert "ot_ci_tree_gate_planned" not in CI.emit_tcl(icg_copy_tree())
    assert "under_gate" in CI.compile_slice(icg_tree())["core_tree"] and not CI.compile_slice(icg_tree())["core_tree"]["under_gate"]


@pytest.mark.parametrize("mut,frag", [
    (lambda t: t["gates"][0].update(domain="weird"), "open or planned"),
    (lambda t: t["leaves"].append(dict(node="ot_cgc_r0_1", load_class="gated_domain", domain_sinks=2)), "planned-domain gate drives"),
    (lambda t: t["leaves"][2].update(sinks=["m0/CLK", "x/CLK"]), "exactly its members"),
    (lambda t: (t["leaves"].pop(1), t["nodes"].pop(5)), "no planned leaf below"),
    (lambda t: t["gates"][0].update(domain="open"), "parent must precede child"),
    (lambda t: t["nodes"][5].update(parent="nope"), "parent must precede child"),
    (lambda t: t["nodes"][3].update(parent="root"), "unequal stage"),
])
def test_planned_domain_mutants_refused(mut, frag):
    s = icg_planned_tree(); mut(s["core_tree"])
    with pytest.raises(CI.InfraError, match=frag):
        CI.emit_tcl(s)


def test_typed_clock_feedthroughs_use_via_access_shape():
    sl = sample()
    tcl = CI.emit_tcl(sl)
    for name in ("mp_isl0_ck_i", "mp_isl0_ck_o"):
        line = next(v for v in tcl.splitlines() if v.startswith("ot_ci_port {" + name + "}"))
        assert line.endswith("{0.048 0.48}")
    for name in ("mp_isl0_rst_i", "mp_isl0_rst_o"):
        line = next(v for v in tcl.splitlines() if v.startswith("ot_ci_port {" + name + "}"))
        assert not line.endswith("{0.048 0.48}")
    # An unconnected misleading port name cannot acquire clock access geometry.
    island = sl["pushdown"]["islands"][0]
    island["ft_ports"].append(dict(name="unused_clk", dir="in", xy_um=[400, 400]))
    with pytest.raises(CI.InfraError, match="every feedthrough port"):
        CI.emit_tcl(sl)


def test_tcl_clock_ft_generic_ft_and_m7_entry_shapes_execute():
    impl = Path(CI.__file__).with_suffix(".tcl")
    script = "source {%s}\n" % impl + r"""
proc block {cmd name} {return bt}
proc bt {cmd} {return INPUT}
proc place_pin {args} {puts $args}
set ::ot_ci_b block
set ::ot_ci_ports {}
ot_ci_port ck INPUT 1 2 {0.048 0.48}
ot_ci_port rst INPUT 1 2
ot_ci_entry entry 1 2
"""
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert not run.stderr
    lines = run.stdout.splitlines()
    assert "-layer M5" in lines[0] and "-pin_size {0.048 0.48}" in lines[0]
    assert "-layer M5" in lines[1] and "-pin_size {0.032 0.192}" in lines[1]
    assert "-layer M7" in lines[2] and "-pin_size {0.032 0.192}" in lines[2]
