"""clock_taps.tcl (CLOCK-RESET 10-25): a station register group is assigned WHOLE to one tap, its reset relay
follows the station's tap, small taps merge into a neighbour.  Tiny OpenDB mock, sourced from inside a proc as ORFS
does (so the hook state must be global)."""
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name('clock_taps.tcl')

MOCK = r'''
namespace eval ord {}
namespace eval odb {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
# ports: clk at x=0, clk_t1 at x=1000 (y=0)
proc blk {m args} {
  global INSTS
  switch $m {
    getBTerms {return {b0 b1}}
    getInsts {return $INSTS}
    findBTerm {if {[lindex $args 0] eq "clk"} {return b0}; return NULL}
  }
}
proc b0 {m args} {switch $m {getName {return clk} getBBox {return box0} getNet {return nclk}}}
proc b1 {m args} {switch $m {getName {return clk_t1} getBBox {return box1} getNet {return nt1}}}
proc box0 {m} {return 0}
proc box1 {m} {if {$m in {xMin xMax}} {return 1000}; return 0}
proc netproc {name m args} {
  global NET
  switch $m {
    getName {return $name}
    setSigType {}
    getITerms {set r {}; foreach {it n} [array get NET] {if {$n eq $name} {lappend r $it}}; return [lsort $r]}
  }
}
foreach n {nclk nt1 rq} { proc $n {m args} "netproc $n \$m {*}\$args" }
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return CLK}
proc outp {m} {if {$m eq "getIoType"} {return OUTPUT}; return Q}
proc rin {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dffm {m} {return DFFHQNx1}
# iterm proc: ck_<inst> (clock pin), q_<inst>, r_<inst>
proc mkflop {name x {rst ""}} {
  global INSTS NET LOC
  lappend INSTS $name; set LOC($name) $x
  set NET(ck_$name) nclk
  proc $name {m args} "
    global LOC
    switch \$m {getName {return $name} getLocation {return \[list \$LOC($name) 0\]} getMaster {return dffm}
                getITerms {return \[lsort \[info commands *_$name\]\]}}"
  proc ck_$name {m args} "
    global NET
    switch \$m {getMTerm {return inp} getInst {return $name} getNet {return \$NET(ck_$name)}
                disconnect {set NET(ck_$name) NULL} connect {set NET(ck_$name) \[lindex \$args 0\]}}"
  if {$rst ne ""} {
    set NET(r_$name) $rst
    proc r_$name {m args} "switch \$m {getMTerm {return rin} getInst {return $name} getNet {return $rst}}"
  }
}
set INSTS {}
'''


def run(tmp_path, body, env=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = (MOCK + body + f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n{env}\n'
              + f'proc wrap {{}} {{ source {{{HOOK}}} }}\n'
              + 'if {[catch wrap msg]} {puts stderr $msg; exit 1}\n'
              + 'foreach i [lsort [array names NET ck_*]] {puts "NET $i $NET($i)"}\n')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


STATION = '''
# station u_ft_ft0_s1: 3 bits at x 400/480/560 (centroid 480 -> clk), nearest-flop would split 560 onto clk_t1
mkflop u_ft_ft0_s1/q_0 400
mkflop u_ft_ft0_s1/q_1 480
mkflop u_ft_ft0_s1/q_2 560 rq
# relay u_rrl_3 at x 900 (nearest clk_t1) resets the station via rq
mkflop u_rrl_3/q 900
proc q_u_rrl_3/q {m args} {switch $m {getMTerm {return outp} getInst {return u_rrl_3/q} getNet {return rq}}}
set NET(q_u_rrl_3/q) rq
'''


def test_station_group_whole_and_relay_follows(tmp_path):
    # 60 filler flops on each tap so neither tap is "small"
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    p = run(tmp_path, STATION + fill)
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'GROUPS 1 groups' in out and '1 were split over taps by the nearest-flop pass' in out, out
    for b in range(3):
        assert f'NET ck_u_ft_ft0_s1/q_{b} nclk' in out
    assert 'NET ck_u_rrl_3/q nclk' in out          # relay re-hung on its station's tap
    assert 'followers 1' in out


def test_small_tap_merged_into_neighbour(tmp_path):
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(60)) + 'mkflop lone 1000\n'
    p = run(tmp_path, fill, env='set ::env(OT_TAP_PITCH_UM) 2400')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_lone nclk' in p.stdout
    assert 'clk_t1(1)->clk' in p.stdout
    assert '"dropped": ["clk_t1"]' in (tmp_path / 'ot_clock_taps.json').read_text()


def test_small_tap_beyond_pitch_kept(tmp_path):
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(60)) + 'mkflop lone 1000\n'
    p = run(tmp_path, fill, env='set ::env(OT_TAP_PITCH_UM) 600')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_lone nt1' in p.stdout
    assert 'WARN clk_t1 keeps 1 sinks' in p.stdout
