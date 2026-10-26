"""12.2a1 declared pushdown ft ports are die-timed (COORD 10-26 12:55 ruling QC-SU-BTAB ASK).
    python3 -m pytest -q tools/die_plan/test_ft_ports.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_infra as CI  # noqa: E402
import ft_ports as FT  # noqa: E402
import master_slice as MS  # noqa: E402
import sdc_lint  # noqa: E402
from test_core_infra import sample  # noqa: E402

# the gen_core_kit_qc / gen_phys generator form (all_inputs -no_clocks / all_outputs select every port)
GEN_SDC = """create_clock -name clk -period 833.0000 [get_ports {clk}]
create_clock -name vclk -period 833.0000
set_clock_latency -source 250.0000 [get_clocks vclk]
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5000
set non_clk_in [all_inputs -no_clocks]
set_input_delay -max 166.6000 -clock vclk $non_clk_in
set_output_delay -max 166.6000 -clock vclk [all_outputs]
set_input_delay -min -40.0000 -clock vclk $non_clk_in
set_output_delay -min 0.0000 -clock vclk [all_outputs]
set_load 2 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $non_clk_in
"""
CTX = dict(period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=40.0, clock_ports=["clk"], inputs=["d", "rst_n"],
           outputs=["q"], unc_setup_ps=60.0, unc_hold_ps=25.0, time_unit_ps=1.0,
           io_floor_ps={"d": 166.6, "rst_n": 166.6, "q": 166.6})


def _decl():
    return FT.from_core_infra_plan(CI.compile_slice(sample()))


def _kit(tmp_path, sdc=GEN_SDC):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "constraint.sdc").write_text(sdc)
    (kd / "sdc_lint.json").write_text(json.dumps(CTX, indent=1) + "\n")
    return kd


def test_declaration_from_the_slice():
    d = _decl()
    assert [(a["source"], a["sink"], a["kind"]) for a in d["arcs"]] == [
        ("mp_isl0_ck_i", "mp_isl0_ck_o", "clock"), ("mp_isl0_rst_i", "mp_isl0_rst_o", "reset")]
    assert FT.verify(d) == [] and len(d["sha256"]) == 64


def test_install_makes_ft_safe_sdc_that_lints(tmp_path):
    kd = _kit(tmp_path)
    assert FT.install(kd, _decl())
    sdc = (kd / "constraint.sdc").read_text()
    assert "all_inputs" not in sdc and "all_outputs" not in sdc.replace("[all_clocks]", "")
    assert "set non_clk_in [get_ports {d rst_n}]" in sdc and "[get_ports {q}]" in sdc
    assert "mp_isl0" not in sdc and "set_false_path" not in sdc
    assert sdc_lint.lint_kit_files(kd) == []
    m = json.loads((kd / "ft_interface.json").read_text())
    assert {(a["source"], a["kind"]) for a in m["arcs"]} == {("mp_isl0_ck_i", "clock"), ("mp_isl0_rst_i", "reset")}


def test_generator_form_on_a_declared_core_fails(tmp_path):
    """the btab_r6 bug: generic core IO budget on the ft ports (all_inputs / all_outputs include them)."""
    d = _decl()
    err = sdc_lint.lint(GEN_SDC, **CTX, ft_ports=d, ft_interface=FT.model_skeleton(d))
    assert any("mp_isl0_ck_o has a core IO delay" in e for e in err), err
    assert any("mp_isl0_rst_i has a core IO delay" in e for e in err), err
    assert any("set_load / set_driving_cell reaches declared ft port" in e for e in err), err


def test_undeclared_port_fails(tmp_path):
    """NEGATIVE: an ft port that is not in the plan's declaration gets no exemption."""
    kd = _kit(tmp_path)
    FT.install(kd, _decl())
    sdc = (kd / "constraint.sdc").read_text()
    # (a) an SDC line naming an undeclared ft port does not resolve -> FAIL
    bad = sdc + "set_input_delay -max 10 -clock vclk [get_ports {mp_isl9_ck_i}]\n"
    assert any("matches no port" in e for e in sdc_lint.lint(bad, **json.loads((kd / "sdc_lint.json").read_text()),
                                                               ft_interface=json.loads((kd / "ft_interface.json").read_text())))
    # (b) a port added to the declaration without re-hashing it (hand-edited exemption) -> FAIL
    ctx = json.loads((kd / "sdc_lint.json").read_text())
    ctx["ft_ports"]["ports"].append(dict(name="d", direction="INPUT"))
    (kd / "sdc_lint.json").write_text(json.dumps(ctx))
    err = sdc_lint.lint_kit_files(kd)
    assert any("sha256 does not match" in e for e in err), err
    # (c) a core IO port declared as ft (properly re-hashed) is refused: no IO port may be exempted
    d = FT.declaration([dict(cell="x", source="d", sink="q", kind="reset")], "test")
    (tmp_path / "c").mkdir()
    kd2 = _kit(tmp_path / "c")
    with pytest.raises(FT.FtError, match="also core IO"):
        FT.install(kd2, d)


def test_missing_interface_arc_fails(tmp_path):
    kd = _kit(tmp_path)
    FT.install(kd, _decl())
    m = json.loads((kd / "ft_interface.json").read_text())
    m["arcs"] = [a for a in m["arcs"] if a["kind"] != "clock"]
    (kd / "ft_interface.json").write_text(json.dumps(m))
    assert any("missing from the interface model" in e for e in sdc_lint.lint_kit_files(kd))
    (kd / "ft_interface.json").unlink()
    assert any("interface model missing" in e for e in sdc_lint.lint_kit_files(kd))


def test_characterised_model_required_at_signoff():
    d = _decl()
    m = FT.model_skeleton(d)
    assert FT.model_errors(d, m) == []
    assert any("not characterised" in e for e in FT.model_errors(d, m, require_characterised=True))
    import signoff as SO
    log = "".join(f"SO_FT_ARC {a['source']} {a['sink']} 10.5 11.1\n" for a in d["arcs"])
    SO.ft_fill_model(d, m, {"tt": dict(ft_arcs=SO.ft_parse(log)), "ff": dict(ft_arcs=SO.ft_parse(log))})
    assert m["status"] == "characterised" and FT.model_errors(d, m, require_characterised=True) == []
    assert m["arcs"][0]["tt_ps"] == dict(min=10.5, max=11.1)


def test_signoff_session_excludes_ft_ports_only_when_declared():
    import signoff as SO
    plain = SO.session_tcl("ff", [], None)
    assert plain == SO.session_tcl("ff", [], None, ft_decl=None) and "so_ft" not in plain
    t = SO.session_tcl("ff", [], None, ft_decl=_decl())
    assert "set so_ft_in {mp_isl0_ck_i mp_isl0_rst_i}; set so_ft_out {mp_isl0_ck_o mp_isl0_rst_o}" in t
    assert "-clock [lindex $so_vclk 0] [all_outputs]" not in t and "$so_dout" in t
    assert t.index("SO_FT_ARC mp_isl0_ck_i") > t.index("check_setup -verbose")
    assert "set_false_path" not in t.replace(plain, "")


def test_signoff_unconstrained_counts_only_undeclared():
    import signoff as SO
    txt = "Warning: There are 3 unconstrained endpoints.\n  ft_ck_o\n  ft_rst_o\n  q_bad\n"
    c = SO.check_setup_counts(txt, ["ft_ck_o", "ft_rst_o"])
    assert c["unconstrained"] == 1 and c["ft_die_timed"] == 2
    assert SO.check_setup_counts(txt)["unconstrained"] == 3          # no declaration: unchanged


def test_false_path_still_banned_on_ft_ports(tmp_path):
    kd = _kit(tmp_path)
    FT.install(kd, _decl())
    sdc = (kd / "constraint.sdc").read_text() + "set_false_path -from [get_ports {mp_isl0_ck_i}] -to [get_ports {mp_isl0_ck_o}]\n"
    (kd / "constraint.sdc").write_text(sdc)
    assert any("forbidden" in e for e in sdc_lint.lint_kit_files(kd))


def test_ft_port_as_clock_source_fails(tmp_path):
    kd = _kit(tmp_path)
    FT.install(kd, _decl())
    sdc = (kd / "constraint.sdc").read_text() + "create_clock -name ftck -period 833 [get_ports {mp_isl0_ck_i}]\n"
    (kd / "constraint.sdc").write_text(sdc)
    err = sdc_lint.lint_kit_files(kd)
    assert any("mp_isl0_ck_i is a clock source" in e for e in err), err


def test_no_declaration_is_byte_identical(tmp_path):
    """kits without an ft declaration: install is a no-op and the lint result is unchanged."""
    kd = _kit(tmp_path)
    before = {p.name: p.read_bytes() for p in kd.iterdir()}
    assert FT.install(kd) is False
    assert {p.name: p.read_bytes() for p in kd.iterdir()} == before
    assert sdc_lint.lint_kit_files(kd) == []


def test_fail_closed_on_other_all_inputs_forms(tmp_path):
    with pytest.raises(FT.FtError, match="all_inputs"):
        FT.apply_sdc(GEN_SDC + "set_load 1 [all_inputs]\n", ["d"], ["q"])


def test_kit_apply_installs_ft_for_a_pushdown_core(tmp_path):
    sl = dict(sample(), type="core_m", module="core_m")
    sl["islands"] = [dict(name="clock_entry", rect_um=[427.68, 427.68, 436.32, 436.32], centre_um=[432, 432],
                          clock_pin=dict(layer="M5", xy_um=[432, 432]))]
    sd = tmp_path / "slices"
    sd.mkdir()
    (sd / "core_m.json").write_text(json.dumps(sl))
    kd = _kit(tmp_path)
    (kd / "io.tcl").write_text("place_pin -pin_name {clk} -layer M4 -location {0.016 100}\n")
    (kd / "face_flops.tcl").write_text("# gpl hook\n")
    (kd / "config.mk").write_text("export DIE_AREA = 0 0 864 864\n")
    MS.kit_apply(kd, "core_m", sl["outline_um"], sd, None, False, kind="core", gpl_hook=kd / "face_flops.tcl",
                 clock_ports=["clk"])
    assert (kd / "ft_ports.json").is_file() and sdc_lint.lint_kit_files(kd) == []
    rep = MS.check_kit(kd)
    assert rep["verdict"] == "PASS", rep["issues"]
    (kd / "ft_ports.json").unlink()
    assert any("ft_ports.json missing" in i for i in MS.check_kit(kd)["issues"])
