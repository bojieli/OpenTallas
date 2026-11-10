"""HBM-COLLECT-1/PTW-C 11-09: opt-in repeater pitch (--max-wire-um) for HBM core kits, wired through core_grt_pre.tcl."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
SRC = (HERE / "gen_core_kit_hbm.py").read_text()


def _g():
    spec = importlib.util.spec_from_file_location("g", HERE / "gen_core_kit_hbm.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    return g


def test_option_and_hook_text():
    assert 'ap.add_argument("--max-wire-um", type=float, default=None' in SRC
    assert 'shutil.copyfile(TOOL / "grt_maxwire.tcl", kd / "grt_maxwire.tcl")' in SRC
    assert '("source /work/grt_maxwire.tcl\\n" if mw else "")' in SRC
    assert 'cfg += [f"export OT_MAXWIRE_UM = {max_wire_um(a):g}"]' in SRC


def test_hook_source_is_shipped_and_reads_env():
    g = _g()
    t = (g.TOOL / "grt_maxwire.tcl").read_text()
    assert "OT_MAXWIRE_UM" in t and "-max_wire_length" in t


def test_default_off_and_values():
    g = _g()
    assert g.max_wire_um(argparse.Namespace()) == 0.0
    assert g.max_wire_um(argparse.Namespace(max_wire_um=None)) == 0.0
    assert g.max_wire_um(argparse.Namespace(max_wire_um=80.0)) == 80.0


def test_negative_refused():
    g = _g()
    try:
        g.max_wire_um(argparse.Namespace(max_wire_um=-5.0))
    except SystemExit:
        return
    raise AssertionError("negative pitch accepted")


def test_relay_line_parse_and_hook():
    g = _g()
    assert g.relay_line(argparse.Namespace()) is None
    assert g.relay_line(argparse.Namespace(relay_line="u_rln,u_bkdn:2")) == (["u_rln", "u_bkdn"], 2)
    for bad in ("u_rln", "u_rln:0", ":2", "u_r;ln:2"):
        try:
            g.relay_line(argparse.Namespace(relay_line=bad))
        except SystemExit:
            continue
        raise AssertionError(bad)
    t = (g.TOOL / "relay_line_place.tcl").read_text()
    assert "OT_RELAY_LINE_PORTS" in t and "setLocation" in t and "swapMaster" in t
    assert '"override export PRE_RESIZE_TCL = /work/core_pre_resize.tcl"' in SRC
    assert 'shutil.copyfile(TOOL / "relay_line_place.tcl", kd / "relay_line_place.tcl")' in SRC


def test_grt_layer_adjust_parse_and_hook():
    g = _g()
    assert g.grt_layer_adjust(argparse.Namespace()) == []
    assert g.grt_layer_adjust(argparse.Namespace(grt_layer_adjust=["M2-M3=0.75", "M4=0.3"])) == [("M2-M3", 0.75), ("M4", 0.3)]
    for bad in ("M2-M3", "M2-M3=1.2", "X2=0.5", "M2-M3-M4=0.5", "M2=abc"):
        try:
            g.grt_layer_adjust(argparse.Namespace(grt_layer_adjust=[bad]))
        except SystemExit:
            continue
        raise AssertionError(bad)
    assert '("source /work/grt_layer_adjust.tcl\\n" if gla else "")' in SRC
