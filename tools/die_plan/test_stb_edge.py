"""STB-EDGE-1 (FABLE-KVRING-HOLD 11-14): subtree_balance.tcl measures every sink from the same source edge.
A sink below an odd number of inverters reads arrival_max_fall; vclk_measured_hold.tcl's property fallback does the same.
    python3 -m pytest -q tools/die_plan/test_stb_edge.py"""
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_stb_tracks_parity_and_reads_fall():
    s = (HERE / "subtree_balance.tcl").read_text()
    assert 'set todo [list [list PORT [$bt getNet] 0]]' in s
    assert 'lassign [lindex $todo end] node net par' in s
    assert re.search(r'\? !\$par : \$par', s)
    assert 'set ::stb::par([$i getName]/[[$it getMTerm] getName]) $par' in s
    assert '"arrival_max_fall" : "arrival_max_rise"' in s
    assert "get_property $p arrival_max_rise]" not in s


def test_stb_parity_expression_in_tcl():
    tclsh = shutil.which("tclsh")
    if not tclsh:
        return
    script = r'''
foreach {mn par want} {BUFx4_ASAP7_75t_R 0 0  INVx1_ASAP7_75t_R 0 1  INVx1_ASAP7_75t_R 1 0  CKINVDCx5p33_ASAP7_75t_R 0 1  HB1xp67_ASAP7_75t_R 1 1} {
  set got [expr {([string match "INV*" $mn] || [string match "CKINV*" $mn]) ? !$par : $par}]
  if {$got != $want} { puts "BAD $mn $par $got"; exit 1 }
}
puts OK
'''
    r = subprocess.run([tclsh], input=script, capture_output=True, text=True)
    assert r.stdout.strip() == "OK", r.stdout + r.stderr


def test_vclk_fallback_is_parity_aware():
    s = (HERE / "vclk_measured_hold.tcl").read_text()
    assert "proc ot_vmh_odd_parity" in s
    assert '[ot_vmh_odd_parity $p] ? "arrival_max_fall" : "arrival_max_rise"' in s
    assert "get_property $p arrival_max_rise]} }" not in s
