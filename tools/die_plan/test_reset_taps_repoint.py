"""C-RST-TAP-REPOINT: behavioural test of the TAP-PAIR AFFINITY acceptance in reset_taps.tcl.  The two procs are cut out of the shipped file and run in tclsh
on fixtures (no OpenROAD needed); the call site is pinned by source checks and mutants."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = (Path(__file__).parent / "reset_taps.tcl").read_text()
TCL = shutil.which("tclsh")
pytestmark = pytest.mark.skipif(TCL is None, reason="tclsh not installed")


def procs(src):
    out = []
    for name in ("rt_aff_accept", "rt_aff_choose", "rt_net_driver_xy"):
        m = re.search(r"^proc %s \{.*?\n\}\n" % name, src, re.S | re.M)
        assert m, name
        out.append(m.group(0))
    return "\n".join(out)


def run(script, src=SRC):
    r = subprocess.run([TCL], input=procs(src) + "\n" + script, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout.split()


def test_accept_table():
    # d_launch reach d_drv lim : reach and driver limit both apply, "" = off
    cases = [("100 400 150 180", 1), ("100 400 205 180", 0), ("500 400 10 180", 0), ("100 400 205 {}", 1), ("500 {} 10 {}", 1), ("100 {} 205 180", 0),
             ("100 400 180 180", 1)]
    script = "".join('puts [rt_aff_accept %s]\n' % c for c, _ in cases)
    assert run(script) == [str(w) for _, w in cases]


def test_default_off_changes_nothing():
    """with no driver limit the decision equals the pre-change rule (launch flop within reach)"""
    for d in (0, 100, 400, 401, 900):
        want = "1" if d <= 400 else "0"
        assert run("puts [rt_aff_accept %d 400 99999 {}]" % d) == [want]


def test_driver_locator_uses_the_output_iterm():
    script = """
proc fakenet {} { return NET }
proc NET {sub} { if {$sub eq "getITerms"} { return {IT_A IT_B} } }
proc IT_A {sub} { if {$sub eq "isOutputSignal"} { return 0 } ; if {$sub eq "getInst"} { return INST_A } }
proc IT_B {sub} { if {$sub eq "isOutputSignal"} { return 1 } ; if {$sub eq "getInst"} { return INST_B } }
proc INST_A {sub} { return {1 1} }
proc INST_B {sub} { return {656700 576700} }
puts [rt_net_driver_xy NET]
puts [llength [rt_net_driver_xy NET2]]
proc NET2 {sub} { return {} }
puts [llength [rt_net_driver_xy NET2]]
"""
    out = run(script)
    assert out[:2] == ["656700", "576700"] and out[-1] == "0"


CHOOSE = [  # best bd ck_i d_launch reach d_drv drv_known lim -> best bd status
    ("7 50 9 100 400 150 1 180", "9 100 ok"),          # accepted: the clock tap relay is taken
    ("7 50 9 100 400 205 1 180", "7 50 refused"),      # driver too far: nearest tap kept (best and bd untouched)
    ("7 50 9 500 400 10 1 180", "7 50 reach"),         # outside the leaf reach: nearest tap kept, not counted as refused
    ("7 50 9 100 400 0 0 180", "7 50 refused"),        # unmeasurable driver under a limit: refused, never fail-open
    ("7 50 9 100 400 0 0 {}", "9 100 ok"),             # no limit: unmeasurable driver is irrelevant (default off)
    ("7 50 9 100 {} 205 1 180", "7 50 refused"),
    ("7 50 9 100 400 165 1 165", "9 100 ok"),
    ("7 50 9 100 400 166 1 165", "7 50 refused"),
]


def test_choose_table():
    out = subprocess.run([TCL], input=procs(SRC) + "\n" + "".join("puts [rt_aff_choose %s]\n" % c for c, _ in CHOOSE), capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
    assert out == [w for _, w in CHOOSE]


def _choose_out(src):
    return subprocess.run([TCL], input=procs(src) + "\n" + "".join("puts [rt_aff_choose %s]\n" % c for c, _ in CHOOSE), capture_output=True, text=True, timeout=30).stdout.strip().splitlines()


@pytest.mark.parametrize("old,new", [
    ("if {$reach_dbu ne \"\" && $d_launch > $reach_dbu} { return [list $best $bd reach] }", ""),
    ("if {$lim_dbu ne \"\" && !$drv_known} { return [list $best $bd refused] }", ""),
    ("return [list $ck_i $d_launch ok]", "return [list $ck_i $d_launch ok]; set x 1"),
    ("  return [list $best $bd refused]\n}", "  return [list $ck_i $d_launch ok]\n}"),
    ("if {[rt_aff_accept $d_launch $reach_dbu $d_drv $lim_dbu]} {", "if {1} {"),
])
def test_choose_mutants(old, new):
    assert old in SRC
    if new.endswith("set x 1"):
        pytest.skip("equivalent mutant")
    assert _choose_out(SRC.replace(old, new, 1)) != [w for _, w in CHOOSE]


def test_call_site_pinned():
    assert "lassign [rt_aff_choose $best $bd $ck_i $d $reach_dbu $d_drv $drv_known $lim_dbu] best bd aff_st" in SRC   # argument order pinned
    assert "set d_drv 0; set drv_known 0" in SRC and "set drv_known 1" in SRC and "set lim_dbu [expr" in SRC
    assert '$aff_st eq "refused"' in SRC and "incr rt_aff_refused" in SRC
    assert "OT_RESET_AFFINITY_REFUSED" in SRC
    assert "OT_RESET_REPOINT_MAX_UM" not in SRC             # the first guard is gone: nearest-tap re-points are never refused


@pytest.mark.parametrize("old,new", [
    ("if {$lim_dbu ne \"\" && $d_drv > $lim_dbu} { return 0 }", ""),
    ("if {$reach_dbu ne \"\" && $d_launch > $reach_dbu} { return 0 }", ""),
    ("if {$lim_dbu ne \"\" && $d_drv > $lim_dbu}", "if {$lim_dbu ne \"\" && $d_drv < $lim_dbu}"),
])
def test_mutants_killed(old, new):
    assert old in SRC
    mut = SRC.replace(old, new, 1)
    with pytest.raises(AssertionError):
        _table_src(mut)


def _table_src(src):
    cases = [("100 400 150 180", 1), ("100 400 205 180", 0), ("500 400 10 180", 0), ("100 {} 205 180", 0)]
    script = "".join('puts [rt_aff_accept %s]\n' % c for c, _ in cases)
    assert run(script, src) == [str(w) for _, w in cases]
