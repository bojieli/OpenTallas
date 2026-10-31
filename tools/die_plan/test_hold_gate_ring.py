"""FLOW-16 10-31: hold_gate.tcl keeps source-synchronous landing-ring inputs (# OT_FWD_RING_INPUTS) on their forwarded
write clock, like signoff._fwd_ring_tcl; kits without the tag keep the old vclk overlay on every data input.
    python3 -m pytest -q tools/die_plan/test_hold_gate_ring.py"""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

STUBS = """proc read_liberty {args} {}
proc read_db {args} {}
proc read_sdc {args} {}
proc set_propagated_clock {args} {}
proc estimate_parasitics {args} {}
proc source {args} {}
proc all_clocks {} {return {clk fclk_in_t_i vclk}}
proc get_property {o k} { if {$o eq "vclk"} {return {}}; if {$o eq "clk"} {return {clk}}; return {fclk_in_t_i} }
proc get_full_name {x} {return $x}
proc all_inputs {} {return {clk fclk_in_t_i a b t_i[0] t_i[1] cland_dn_ready_t_i}}
proc all_outputs {} {return {}}
proc get_clocks {x} {return $x}
proc get_ports {x} { regsub {\[\*\]$} $x {\[*\]} x; set out {}; foreach p [all_inputs] { if {[string match $x $p]} { lappend out $p } }; return $out }
proc set_input_delay {args} { puts "SID $args" }
proc set_output_delay {args} {}
namespace eval sta {}
proc sta::time_sta_ui {x} {return $x}
proc sta::worst_slack_cmd {args} {return 1}
proc sta::endpoint_violation_count {args} {return 0}
set ::env(PLIBS) x.lib
set ::env(ODB) x.odb
set ::env(SDC) x.sdc
set ::env(PLATFORM_DIR) /nonexistent
"""


def _run(tmp_path, golden):
    if shutil.which("tclsh") is None:
        pytest.skip("no tclsh")
    (tmp_path / "hold_gate.tcl").write_text(STUBS + (HERE / "hold_gate.tcl").read_text())
    if golden is not None:
        (tmp_path / "constraint.sdc").write_text(golden)
    return subprocess.run(["tclsh", str(tmp_path / "hold_gate.tcl")], capture_output=True, text=True)


def test_ring_inputs_keep_forwarded_clock(tmp_path):
    r = _run(tmp_path, "create_clock -name clk\n# OT_FWD_RING_INPUTS fclk_in_t_i t_i[*] cland_dn_ready_t_i\n")
    assert r.returncode == 0, r.stderr
    sid = [ln for ln in r.stdout.splitlines() if ln.startswith("SID")]
    vclk = [ln for ln in sid if "-clock vclk" in ln]
    assert vclk == ["SID -min -40 -clock vclk {a b}"]                      # ring ports left the vclk overlay
    assert "SID -min -40 -clock fclk_in_t_i {{t_i[0]} {t_i[1]}}" in sid
    assert "SID -min -40 -clock fclk_in_t_i cland_dn_ready_t_i" in sid
    assert "OT_HOLD_GATE forwarded ring inputs 3 on 1 clock(s), min -40" in r.stdout


def test_no_tag_is_unchanged(tmp_path):
    for golden in (None, "create_clock -name clk\n"):
        r = _run(tmp_path, golden)
        assert r.returncode == 0, r.stderr
        sid = [ln for ln in r.stdout.splitlines() if ln.startswith("SID")]
        assert sid == ["SID -min -40 -clock vclk {a b {t_i[0]} {t_i[1]} cland_dn_ready_t_i}"]
        assert "forwarded ring inputs" not in r.stdout


def test_malformed_tag_fails_closed(tmp_path):
    r = _run(tmp_path, "# OT_FWD_RING_INPUTS fclk_in_t_i\n")
    assert r.returncode != 0 and "malformed OT_FWD_RING_INPUTS" in r.stderr
