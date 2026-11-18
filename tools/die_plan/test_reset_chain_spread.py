"""FABLE-FIX-S81-COLTAP 11-16: reset_replicate copy_depth chains are spread on the line common flop -> region copy after
global placement (reset_chain_spread.tcl at PRE_RESIZE).  r2 pilot: hop 1 was 836..1,174 um (-181 ps at CTS) because GPL
puts every chain flop at its loads; with the hook the longest hop is 315 um."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as G  # noqa: E402

TCL = (HERE / "reset_chain_spread.tcl").read_text()


def _kit(tmp_path, pre=True):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "config.mk").write_text("export A = 1\n" + ("export PRE_RESIZE_TCL = /work/gp_noconverge_gate.tcl\n" if pre else ""))
    if pre:
        (kd / "gp_noconverge_gate.tcl").write_text("# gate\n")
    return kd


def test_depth():
    assert G.reset_chain_depth({}) == 0 == G.reset_chain_depth(None)
    assert G.reset_chain_depth({"reset_replicate": [{"driver_re": "x"}]}) == 1
    assert G.reset_chain_depth({"reset_replicate": [{"driver_re": "x"}, {"driver_re": "y", "copy_depth": 3}]}) == 3


def test_no_chain_is_byte_identical(tmp_path):
    kd = _kit(tmp_path)
    before = {f.name: f.read_bytes() for f in kd.iterdir()}
    assert G.install_reset_chain_spread(kd, {"reset_replicate": [{"driver_re": "x", "grid_um": 300}]}) is False
    assert G.install_reset_chain_spread(kd, {}) is False
    assert {f.name: f.read_bytes() for f in kd.iterdir()} == before


def test_chain_appends_to_the_existing_pre_resize_hook(tmp_path):
    kd = _kit(tmp_path)
    assert G.install_reset_chain_spread(kd, {"reset_replicate": [{"driver_re": "x", "copy_depth": 3}]}) is True
    assert (kd / "reset_chain_spread.tcl").read_text() == TCL
    gate = (kd / "gp_noconverge_gate.tcl").read_text()
    assert gate.startswith("# gate\n") and gate.rstrip().endswith("source /work/reset_chain_spread.tcl")
    mk = (kd / "config.mk").read_text()
    assert mk.count("PRE_RESIZE_TCL") == 1 and mk.rstrip().endswith("export OT_RESET_CHAIN_SPREAD = 1")


def test_chain_is_the_hook_when_the_kit_has_none(tmp_path):
    kd = _kit(tmp_path, pre=False)
    assert G.install_reset_chain_spread(kd, {"reset_replicate": [{"driver_re": "x", "copy_depth": 2}]})
    mk = (kd / "config.mk").read_text()
    assert "export PRE_RESIZE_TCL = /work/reset_chain_spread.tcl\n" in mk and "export OT_RESET_CHAIN_SPREAD = 1" in mk


def test_missing_hook_file_fails_closed(tmp_path):
    kd = _kit(tmp_path)
    (kd / "gp_noconverge_gate.tcl").unlink()
    with pytest.raises(ValueError):
        G.install_reset_chain_spread(kd, {"reset_replicate": [{"driver_re": "x", "copy_depth": 3}]})


def test_tcl_form():
    # opt-in gate, runs at global scope, never touches fixed cells, reports hops over the limit
    assert 'if {[info exists ::env(OT_RESET_CHAIN_SPREAD)] && $::env(OT_RESET_CHAIN_SPREAD) eq "1"} {' in TCL
    assert TCL.lstrip().startswith("#") and "uplevel #0 {" in TCL
    assert "if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue" in TCL
    assert "OT_RESET_CHAIN_MAX_HOP_UM" in TCL and ": 390.0}]" in TCL
    assert r"{^(.+)_r([0-9]+)_s([0-9]+)[./]}" in TCL                       # the names reset_replicate.py gives the chain flops
    assert "OT_RESET_CHAIN done:" in TCL and TCL.count("{") == TCL.count("}")


def test_tcl_removes_only_the_reset_data_buffers():
    # v5: timing-driven GPL has already buffered the 2-pin chain nets (r2: 468 BUF, a 1,606 ps tree); only BUF cells reached
    # from a chain / common flop Q are removed, polarity inverters and every clock net and clock pin are checked unchanged
    assert "remove_buffers {*}[dict keys $rc_bufs]" in TCL
    assert "refuses empty explicit buffer set" not in TCL                  # no buffer reached = nothing to prune, not an error
    assert "nothing to prune" in TCL and "  if {[dict size $rc_bufs]} {\n    set selected" in TCL
    assert "RESET v5 removed INV" in TCL and "RESET v5 changed clock net" in TCL and "RESET v5 changed clock connectivity" in TCL
    assert "RESET v3 removed unrelated buffer" in TCL
    assert "proc rc_joint" in TCL                                          # stage sites follow the real neighbours around macros


def test_gen_calls_the_installer_after_reset_relay_full():
    src = Path(G.__file__).read_text()
    i = src.index('        reset_relay_full(kd / "rtl")\n    install_reset_chain_spread(kd, t)\n')
    assert i > 0 and src.count("    install_reset_chain_spread(kd, t)\n") == 1


def test_names_match_reset_replicate():
    rr = (HERE / "reset_replicate.py").read_text()
    assert "_s{j}" in rr and "copy_depth" in rr
