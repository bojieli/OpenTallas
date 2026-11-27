"""C-RST-TAP-REPOINT relay (default off): rt_relay_needed / rt_relay_seat / rt_insert_relay of reset_taps.tcl, run in tclsh against a fake odb."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = (Path(__file__).parent / "reset_taps.tcl").read_text()
TCL = shutil.which("tclsh")
pytestmark = pytest.mark.skipif(TCL is None, reason="tclsh not installed")

FAKE = r'''
set ::LOG {}
namespace eval ord { proc get_db {} { return DB } }
proc DB {sub args} { if {$sub eq "findMaster"} { return [expr {[lindex $args 0] eq "BUFx2_ASAP7_75t_R" ? "MASTER" : "NULL"}] } }
namespace eval odb {
  proc dbInst_create {blk m n} { lappend ::LOG [list inst $n]; return BINS }
  proc dbNet_create {blk n} { lappend ::LOG [list net $n]; return NET2 }
}
proc BINS {sub args} {
  if {$sub eq "findITerm"} { return ITERM_[lindex $args 0] }
  lappend ::LOG [list buf $sub {*}$args]
}
proc ITERM_A {sub args} { lappend ::LOG [list A $sub {*}$args] }
proc ITERM_Y {sub args} { lappend ::LOG [list Y $sub {*}$args] }
proc FIT {sub args} {
  if {$sub eq "getInst"} { return FINS }
  if {$sub eq "getNet"} { return NET1 }
  lappend ::LOG [list flop $sub {*}$args]
}
proc FINS {sub args} { if {$sub eq "getLocation"} { return {100 200} } }
'''


def procs(src):
    out = []
    for name in ("rt_relay_needed", "rt_relay_seat", "rt_insert_relay"):
        m = re.search(r"^proc %s \{.*?\n\}\n" % name, src, re.S | re.M)
        assert m, name
        out.append(m.group(0))
    return "\n".join(out)


def run(script, src=SRC):
    r = subprocess.run([TCL], input=FAKE + procs(src) + "\n" + script, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip().splitlines()


NEEDED = [("150 1 165", 0), ("166 1 165", 1), ("165 1 165", 0), ("0 0 165", 1), ("999 1 {}", 0), ("0 0 {}", 0)]


def needed_out(src=SRC):
    return run("".join("puts [rt_relay_needed %s]\n" % c for c, _ in NEEDED), src)


def test_needed_table():
    assert needed_out() == [str(w) for _, w in NEEDED]


def test_seat_is_the_midpoint():
    assert run("puts [rt_relay_seat 100 200 300 400]\nputs [rt_relay_seat 0 0 -50 10]") == ["200 300", "-25 5"]


def test_insert_relay_rewires_the_flop_through_a_buffer():
    out = run("puts [rt_insert_relay BLK FIT {300 400} u_ft/eq.x]\nputs $::LOG")
    assert out[0] == "1"
    log = out[1]
    assert "inst u_rstrelay_u_ft_eq_x" in log and "net rst_relay_net_u_ft_eq_x" in log
    assert "buf setLocation 200 300" in log and "buf setPlacementStatus PLACED" in log
    assert "A connect NET1" in log and "Y connect NET2" in log               # buffer input on the old net, output on the new net
    assert log.index("flop disconnect") < log.index("flop connect NET2")      # the flop ends on the relay output


def test_missing_master_inserts_nothing():
    out = run("proc DB {sub args} { return NULL }\nputs [rt_insert_relay BLK FIT {300 400} t]\nputs $::LOG")
    assert out[0] == "0" and (len(out) == 1 or "flop" not in out[1])


def test_call_site_and_default_off_pinned():
    assert 'set ::env(OT_RESET_RELAY) eq "1"' not in SRC and '$::env(OT_RESET_RELAY) eq "1"' in SRC          # insertion only with its own flag
    assert "lappend rt_relay_todo" in SRC and "OT_RESET_RELAY candidates" in SRC
    assert "rt_relay_needed $rd $rknown [expr {$::env(OT_RESET_AFFINITY_MAX_DRIVER_UM) * $rt_dbu}]" in SRC


@pytest.mark.parametrize("old,new", [
    ("  if {$lim_dbu eq \"\"} { return 0 }\n", ""),
    ("  if {!$drv_known} { return 1 }\n", ""),
    ("return [expr {$d_drv > $lim_dbu}]", "return [expr {$d_drv < $lim_dbu}]"),
])
def test_needed_mutants_die(old, new):
    assert old in SRC
    assert needed_out(SRC.replace(old, new, 1)) != [str(w) for _, w in NEEDED]


@pytest.mark.parametrize("old,new", [
    ("  $it disconnect\n  $it connect $n2\n", "  $it connect $n2\n"),
    ("  [$b findITerm A] connect $net\n", ""),
    ("  [$b findITerm Y] connect $n2\n", "  [$b findITerm Y] connect $net\n"),
    ("  if {$master eq \"NULL\"} { return 0 }\n", ""),
    ("  $b setPlacementStatus PLACED\n", ""),
    ("  return [list [expr {($x + $dx) / 2}] [expr {($y + $dy) / 2}]]", "  return [list $dx $dy]"),
])
def test_insert_mutants_die(old, new):
    assert old in SRC, old
    mut = SRC.replace(old, new, 1)
    good = run("puts [rt_insert_relay BLK FIT {300 400} t]\nputs $::LOG\nputs [rt_relay_seat 100 200 300 400]")
    try:
        bad = run("puts [rt_insert_relay BLK FIT {300 400} t]\nputs $::LOG\nputs [rt_relay_seat 100 200 300 400]", mut)
    except AssertionError:
        return                                                                # crashes: killed
    try:
        nm = run("proc DB {sub args} { return NULL }\nputs [rt_insert_relay BLK FIT {300 400} t]\nputs $::LOG", mut)
        nm_good = run("proc DB {sub args} { return NULL }\nputs [rt_insert_relay BLK FIT {300 400} t]\nputs $::LOG")
    except AssertionError:
        return
    assert bad != good or nm != nm_good, "mutant survived: " + old[:50]
