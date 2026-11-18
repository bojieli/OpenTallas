"""PAD-ABUT-STRIP-1: PRE_FINAL_REPORT hook line / chain, hook text, staged by the generator for macro_pin pad kits."""
import tempfile
from pathlib import Path

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
