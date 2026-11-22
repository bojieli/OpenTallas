"""PAD-ABUT-STRIP-1: PRE_FINAL_REPORT hook line / chain, hook text, staged by the generator for macro_pin pad kits."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import gen_phys as G

HERE = Path(__file__).resolve().parent


def test_config_adds_the_hook_line():
    kd = tempfile.mkdtemp()
    out = G.pad_abut_strip_config("export A = 1\n", kd)
    assert out.endswith("export PRE_FINAL_REPORT_TCL = /work/pad_abut_strip.tcl\n") and not list(Path(kd).iterdir())
    assert G.pad_abut_strip_config(out, kd) == out


def test_existing_hook_is_chained_strip_first():
    kd = tempfile.mkdtemp()
    out = G.pad_abut_strip_config("override export PRE_FINAL_REPORT_TCL = /work/own.tcl\n", kd)
    assert "PRE_FINAL_REPORT_TCL = /work/pre_final_chain.tcl" in out
    assert [l for l in (Path(kd) / "pre_final_chain.tcl").read_text().splitlines() if l.startswith("source")] == [
        "source /work/pad_abut_strip.tcl", "source /work/own.tcl"]
    assert G.pad_abut_strip_config(out, kd) == out


def test_hook_only_destroys_wires_of_pad_nets_and_is_wired_with_the_wire_hook():
    t = (HERE / "pad_abut_strip.tcl").read_text()
    assert "dbWire_destroy" in t and "OT_PAD_ABUT_STRIP" in t
    code = "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#"))
    for banned in ("dbInst_", "dbNet_create", "detailed_route", "global_route"):
        assert banned not in code
    gp = (HERE / "gen_phys.py").read_text()
    assert gp.index("pad_abut_wire_config(mk, kd)") < gp.index("pad_abut_strip_config((kd")


@pytest.mark.parametrize("macro_pad_kit", [False, True])
@pytest.mark.parametrize("warm_spef", [False, True])
def test_prd_count_strips_native_pad_wires_before_reading_parasitics(tmp_path, macro_pad_kit, warm_spef):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh needed to exercise the standalone count")
    shutil.copyfile(HERE / "post_route_drv" / "prd_count.tcl", tmp_path / "prd_count.tcl")
    if macro_pad_kit:
        (tmp_path / "pad_abut_strip.tcl").write_text("puts stripped\n")
    if warm_spef:
        (tmp_path / "res.spef").touch()
    run = subprocess.run([tclsh], cwd=tmp_path, text=True, capture_output=True, check=True, input="""
array set ::env {OT_LEFS {} OT_LIBS {} ODB route.odb SDC route.sdc SPEF res.spef RCX_RULES rules TAG test CHKPL 0}
proc read_db {args} { puts read_db }
proc read_sdc {args} {}
proc all_clocks {} { return {} }
proc set_propagated_clock {args} {}
proc extract_parasitics {args} { puts extract }
proc write_spef {args} {}
proc read_spef {args} { puts read_spef }
namespace eval sta {
    proc max_slew_violation_count {} { return 0 }
    proc max_capacitance_violation_count {} { return 0 }
}
source prd_count.tcl
""")
    expected = ["read_db"]
    if macro_pad_kit:
        expected.append("stripped")
    if not warm_spef:
        expected.append("extract")
    assert not run.stderr
    assert run.stdout.splitlines() == expected + ["read_spef", "OT_PRD_COUNT test slew 0 cap 0 placement ok"]
