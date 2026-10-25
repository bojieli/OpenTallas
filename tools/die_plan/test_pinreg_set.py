"""CLOCK-RESET 10-25 (rule LC1): ONE boundary pin-register set (clock_family.tcl ot_cf_pinregs) for the pre-route
insertion gate and the pin-register pad, plus the per-pin-register window report (opt-in enforcement)."""
from pathlib import Path
import shutil
import subprocess

import pytest

HERE = Path(__file__).resolve().parent
CF = HERE.parents[1] / "physical/common_flow/clock_family.tcl"


def run(body):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    # mock OpenSTA: r_in (fanout of an input), r_out (fanin of an output), r_both (both), r_int (interior)
    text = f"""source {{{CF}}}
proc all_registers {{args}} {{ return {{r_in/CLK r_out/CLK r_both/CLK r_int/CLK}} }}
proc get_full_name {{p}} {{ return $p }}
proc all_inputs {{args}} {{ return {{a_i}} }}
proc all_outputs {{}} {{ return {{b_o}} }}
proc get_fanout {{args}} {{ return {{r_in/D r_both/D}} }}
proc get_fanin {{args}} {{ return {{r_out/CLK r_both/CLK}} }}
proc ot_cf_wire {{p c}} {{ if {{$p eq "r_out/CLK"}} {{ error nope }}; return 250.0 }}
proc get_property {{p k}} {{ return 1110.0 }}
""" + body
    p = subprocess.run(["tclsh"], input=text, text=True, capture_output=True)
    assert not p.stderr, p.stderr
    return p.stdout


def test_pinregs_inputs_and_outputs_once_interior_excluded():
    s = run('puts "SET [ot_cf_pinregs]"\n')
    assert "SET r_in r_in/CLK r_both r_both/CLK r_out r_out/CLK" in s


def test_arrival_signoff_measure_then_falling_edge_fold():
    s = run('puts "A [ot_cf_pinreg_arrival r_in/CLK clk 1200.0] B [ot_cf_pinreg_arrival r_out/CLK clk 1200.0]"\n')
    assert "A 250.0 B 510.0" in s


def test_gate_and_pad_share_the_set_no_private_copy():
    for f in ("postcts_gate.tcl", "pinreg_pad.tcl"):
        t = (HERE / f).read_text()
        assert "ot_cf_pinregs" in t and "ot_cf_pinreg_arrival" in t, f
        assert "get_fanout -from" not in t and "get_fanin -to" not in t, f


def test_window_reported_always_enforced_only_opt_in():
    t = (HERE / "postcts_gate.tcl").read_text()
    assert 'OT_POSTCTS_WINDOW %s pinreg late %d early %d' in t
    assert '"window\\": \\"%s\\"' in t or '\\"window\\": \\"%s\\"' in t
    i = t.index('set v [expr {$n && $dev <= $tol ? "PASS" : "FAIL"}]')
    j = t.index('if {[info exists ::env(OT_POSTCTS_WINDOW)] && $::env(OT_POSTCTS_WINDOW) && $wv ne "PASS"} { set v FAIL }')
    assert i < j
    assert "OT_POSTCTS_GRP_SPREAD_PS" in t and ": 20.0}" in t
