"""tap_landing_seam.tcl (KV-HUB-HOLD 11-23): a landing's local-clock ring sinks and its u_bin capture go to ONE tap that
carries no hard clock pin; landings already on one hard-free tap, START copies without a u_bin, and hard cland macros are
left alone.  Tiny OpenDB mock, sourced from inside a proc as clock_taps.tcl does."""
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name('tap_landing_seam.tcl')

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc blk {m args} {return {}}
proc netproc {name m args} {
  global NET
  switch $m {
    getName {return $name}
    getITerms {set r {}; foreach {it n} [array get NET] {if {$n eq $name} {lappend r $it}}; return [lsort $r]}
  }
}
foreach n {tA tB tC} { proc $n {m args} "netproc $n \$m {*}\$args" }
proc clkm {m} {if {$m eq "getIoType"} {return INPUT}; return CLK}
proc dffm {m} {if {$m eq "isBlock"} {return 0}; return DFFHQNx1}
proc macm {m} {if {$m eq "isBlock"} {return 1}; return MAC}
set N 0
proc mk {name x net {master dffm}} {
  global NET LOC N
  incr N; set i i$N; set LOC($i) $x; set NET(ck$N) $net
  proc $i {m args} "global LOC; switch \$m {getName {return {$name}} getLocation {return \[list \$LOC($i) 0\]} getMaster {return $master}}"
  proc ck$N {m args} "global NET; switch \$m {getMTerm {return clkm} getInst {return $i} getNet {return \$NET(ck$N)} disconnect {set NET(ck$N) NULL} connect {set NET(ck$N) \[lindex \$args 0\]}}"
}
# taps: tA x=0 (carries the hard core pin), tB x=100, tC x=1000
set ct_taps {{tA tA 0 0} {tB tB 100 0} {tC tC 1000 0}}
mk u_bound.u_astk_ES 0 tA macm
# landing k: ring read side split tA/tB, capture on the hard tap tA (the hub_Eo -323 ps form)
mk {u_bound.u_cland_k/u_ring.dch[0].u_dsel/y[0]$_DFF_P_} 20 tA
mk {u_bound.u_cland_k/u_ring.dch[0].u_dsel/y[1]$_DFF_P_} 60 tB
mk {u_bound.u_cland_k/u_ring.rd_ptr[0]$_DFF_P_} 80 tB
mk {u_bound.u_bin_k/q[0]$_DFF_P_} 10 tA
mk {u_bound.u_bin_k/q[1]$_DFF_P_} 30 tA
# landing m: already on one hard-free tap
mk {u_bound.u_cland_m/u_ring.dch[0].u_dsel/y[0]$_DFF_P_} 990 tC
mk {u_bound.u_bin_m/q[0]$_DFF_P_} 1010 tC
# START copy (no u_bin of its key) and a hard cland macro: never moved
mk {u_bound.u_cland_reader_start_k_1/q$_DFF_P_} 5 tA
mk u_bound.u_cland_ft28_i 15 tA macm
'''


def run(env):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = (MOCK + env + f'\nproc wrap {{}} {{ global ct_taps; source {{{HOOK}}} }}\n'
              + 'if {[catch wrap msg]} {puts stderr $msg; exit 1}\n'
              + 'foreach i [lsort -dictionary [array names NET]] {puts "NET $i $NET($i)"}\n')
    r = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    nets = dict(l.split()[1:] for l in r.stdout.splitlines() if l.startswith('NET '))
    return r.stdout, nets


def test_off_by_default():
    out, nets = run('')
    assert 'OT_TAP_LANDING_SEAM' not in out
    assert nets['ck2'] == 'tA' and nets['ck5'] == 'tA'


def test_landing_moves_to_one_hard_free_tap():
    out, nets = run('set ::env(OT_TAP_LANDING_SEAM) 1')
    assert [nets[f'ck{i}'] for i in range(2, 7)] == ['tB'] * 5     # ring + bin of k together, not the hard tap tA
    assert nets['ck1'] == 'tA' and nets['ck10'] == 'tA'           # hard pins stay
    assert nets['ck7'] == 'tC' and nets['ck8'] == 'tC'            # m untouched
    assert nets['ck9'] == 'tA'                                     # START copy untouched
    assert 'landings 2, already one hard-free tap 1, sinks moved 3, warn 0' in out


def test_full_tap_prefers_room():
    fill = '\n'.join(f'mk u_bound.u_x/r{j} 100 tB' for j in range(3))
    out, nets = run(fill + '\nset ::env(OT_TAP_LANDING_SEAM) 1\nset ::env(OT_TAP_MAX_SINKS) 7\nset ::env(OT_TAP_SEAM_RADIUS_UM) 2000')
    # tB would hold 8 > cap 7; tC (7, inside the radius) wins over the full nearer tap
    assert [nets[f'ck{i}'] for i in range(2, 7)] == ['tC'] * 5


def test_typed_order_opt_in_exports_only_the_selected_dependency():
    from gen_phys import tap_landing_seam_exports

    seam = {"tap_landing_seam": True, "tap_reset_split": True}
    assert tap_landing_seam_exports({}) == []
    assert tap_landing_seam_exports({"clock": seam}) == ["export OT_TAP_LANDING_SEAM = 1"]
    assert tap_landing_seam_exports({"clock": dict(seam, tap_landing_seam_before_reset=True)}) == [
        "export OT_TAP_LANDING_SEAM = 1", "export OT_TAP_LANDING_SEAM_BEFORE_RESET = 1"]
    with pytest.raises(ValueError, match="requires tap_landing_seam and a reset tap pass"):
        tap_landing_seam_exports({"clock": {"tap_landing_seam_before_reset": True}})
