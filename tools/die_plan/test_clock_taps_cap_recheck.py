"""clock_taps.tcl S7 cap recheck (VSN6-B 11-11).  HBM vsN6 form3 ran the 3,000-sink cap pass BEFORE the two hop-latch
passes; the capture-tap re-hang then left clk_t14 at 4,004 and clk_t12 at 3,044 sinks with no WARN.  The recheck after
both latch passes re-balances (launch flop + its latches move as one unit) or prints a loud WARN, and the final count
never passes over the cap silently.  Indexed OpenDB mock (thousands of sinks), sourced from inside a proc as ORFS does."""
import json
import re
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
set BT {}; set INSTS {}
proc blk {m args} {
  switch $m {
    getBTerms {return $::BT}
    getInsts {return $::INSTS}
    findBTerm {set n [lindex $args 0]; if {[info exists ::BTN($n)]} {return $::BTN($n)}; return NULL}
    findNet {return [lindex $args 0]}
    findInst {return NULL}
  }
}
proc netp {name m args} {switch $m {getName {return $name} setSigType {} getITerms {return $::MEM($name)}}}
proc mknet {name} {if {![info exists ::MEM($name)]} {set ::MEM($name) {}; interp alias {} $name {} netp $name}}
proc bbp {x m} {if {$m in {xMin xMax}} {return $x}; return 0}
proc btp {port m args} {switch $m {getName {return $port} getBBox {return bb_$port} getNet {return n_$port}}}
proc addtap {port x} {
  lappend ::BT bt_$port; set ::BTN($port) bt_$port
  mknet n_$port
  interp alias {} bt_$port {} btp $port
  interp alias {} bb_$port {} bbp $x
}
proc mt_ck {m} {switch $m {getIoType {return INPUT} getName {return CLK}}}
proc mt_d {m} {switch $m {getIoType {return INPUT} getName {return D}}}
proc mt_q {m} {switch $m {getIoType {return OUTPUT} getName {return QN}}}
proc m_ff {m} {switch $m {getName {return DFFHQNx1_ASAP7_75t_R} isBlock {return 0}}}
proc m_dl {m} {switch $m {getName {return DLLx1_ASAP7_75t_R} isBlock {return 0}}}
proc itp {id m args} {
  switch $m {
    getMTerm {return $::ITM($id)}
    getInst {return $::ITI($id)}
    getNet {return $::ITN($id)}
    getAvgXY {return 0}
    disconnect {
      set n $::ITN($id)
      set k [lsearch -exact $::MEM($n) $id]
      if {$k >= 0} {set ::MEM($n) [lreplace $::MEM($n) $k $k]}
      set ::ITN($id) NULL
    }
    connect {set n [lindex $args 0]; set ::ITN($id) $n; lappend ::MEM($n) $id}
  }
}
proc mkit {id inst mterm net} {
  set ::ITM($id) $mterm; set ::ITI($id) $inst; set ::ITN($id) $net; lappend ::MEM($net) $id
  lappend ::II($inst) $id
  interp alias {} $id {} itp $id
}
proc instp {name m args} {
  switch $m {
    getName {return $name}
    getLocation {return [list $::X($name) 0]}
    getMaster {return $::MS($name)}
    getITerms {return $::II($name)}
  }
}
# every sink starts on the root clk net, as after synthesis
proc mkinst {name master x} {
  lappend ::INSTS $name; set ::X($name) $x; set ::MS($name) $master; set ::II($name) {}
  interp alias {} $name {} instp $name
  mkit ck.$name $name mt_ck n_clk
}
proc link {drv snk} {
  mknet w.$drv
  if {![info exists ::ITM(q.$drv)]} {mkit q.$drv $drv mt_q w.$drv}
  mkit d.$snk $snk mt_d w.$drv
}
proc ff {name x} {mkinst $name m_ff $x}
proc fills {pre n x} {for {set i 0} {$i < $n} {incr i} {ff $pre$i $x}}
'''


def run(tmp_path, body, env=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = (MOCK + body + f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n{env}\n'
              + f'proc wrap {{}} {{ source {{{HOOK}}} }}\n'
              + 'if {[catch wrap msg]} {puts stderr $::errorInfo; exit 1}\n'
              + 'foreach i [lsort [array names ITN ck.*]] {puts "NET $i $ITN($i)"}\n')
    p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr[-3000:]
    nets = dict(re.findall(r'^NET ck\.(\S+) (\S+)$', p.stdout, re.M))
    return p.stdout, nets, json.loads((tmp_path / 'ot_clock_taps.json').read_text())


# vsN6 form3 shape: after the nearest + cap pass clk_t12 and clk_t14 hold exactly 3,000 sinks; 1,048 hop latches sit
# near clk_t9 beside their launch flops, and their capture flops are 1,004 on clk_t14 and 44 on clk_t12.  The
# capture-tap re-hang (OT_HOP_LATCH_CAPTURE_TAP u_fl_) then gives clk_t14 4,004 and clk_t12 3,044.
FORM3 = r'''
addtap clk 0; addtap clk_t12 1000; addtap clk_t14 2000; addtap clk_t9 3000
fills pr 100 0
fills p12_ 2956 1000
fills p14_ 1996 2000
for {set i 0} {$i < 1048} {incr i} {
  ff lau$i 3000
  mkinst u_bound.u_fl_L$i m_dl 2900
  if {$i < 1004} {ff cap14_$i 2000; set c cap14_$i} else {ff cap12_$i 1000; set c cap12_$i}
  link lau$i u_bound.u_fl_L$i
  link u_bound.u_fl_L$i $c
}
'''
FORM3_ENV = 'set ::env(OT_TAP_PITCH_UM) 4000\nset ::env(OT_HOP_LATCH_CAPTURE_TAP) u_fl_'


def test_form3_reproduced_4004_3044_without_recheck(tmp_path):
    out, nets, js = run(tmp_path, FORM3, FORM3_ENV + '\nset ::env(OT_TAP_CAP_RECHECK) 0')
    # the cap pass itself saw nothing over 3,000 (it runs before the latch passes)
    assert '0 sinks re-assigned' in out, out
    assert 'hop latches on capture tap (OT_HOP_LATCH_CAPTURE_TAP): 1048 re-hung' in out, out
    assert js['sinks']['clk_t14'] == 4004 and js['sinks']['clk_t12'] == 3044, js
    # never silent now: the recheck WARN, the final WARN and the JSON all name both taps
    assert 'WARN cap recheck after hop latches: 2 taps over cap 3000: clk_t12 3044, clk_t14 4004' in out, out
    assert 'WARN OVER_CAP 2 taps > cap 3000' in out, out
    assert sorted(js['over_cap']) == ['clk_t12', 'clk_t14'] and js['cap'] == 3000


def test_form3_rebalanced_by_recheck(tmp_path):
    out, nets, js = run(tmp_path, FORM3, FORM3_ENV)
    assert max(js['sinks'].values()) <= 3000 and js['over_cap'] == [], js
    assert sum(js['sinks'].values()) == 100 + 2956 + 1996 + 3 * 1048
    assert 'over cap now: none' in out and 'OVER_CAP' not in out, out
    # capture-tap latches and their capture sinks were not moved: latch -> capture still shares one tap
    for i in range(1048):
        cap = f'cap14_{i}' if i < 1004 else f'cap12_{i}'
        assert nets[f'u_bound.u_fl_L{i}'] == nets[cap] == ('n_clk_t14' if i < 1004 else 'n_clk_t12')
    # what moved were plain sinks
    assert sum(1 for k, v in nets.items() if k.startswith('p14_') and v != 'n_clk_t14') == 1004
    assert sum(1 for k, v in nets.items() if k.startswith('p12_') and v != 'n_clk_t12') == 44


# form4 shape (launch tap only): 200 launch flops at x=1400 (nearest clk_t1) drive latches at x=1600 (nearest clk_t2).
# The launch-tap pass pulls the latches onto clk_t1 (3,200 > 3,000); the recheck moves 100 launch UNITS (flop + latch)
# to clk_t2, the cheapest target, so flop -> latch keeps one tap (CRPR).
FORM4 = r'''
addtap clk 0; addtap clk_t1 1000; addtap clk_t2 2000
fills p1_ 2800 1000
fills p2_ 100 2000
for {set i 0} {$i < 200} {incr i} {
  ff lau$i 1400
  mkinst u_fl_L$i m_dl 1600
  ff cap$i 2000
  link lau$i u_fl_L$i
  link u_fl_L$i cap$i
}
'''


def test_launch_tap_overflow_moves_whole_launch_units(tmp_path):
    out, nets, js = run(tmp_path, FORM4, 'set ::env(OT_TAP_PITCH_UM) 4000')
    assert 'hop latches: 200 on their launch station' in out and '(200 re-hung)' in out, out
    assert 'WARN cap recheck after hop latches: 1 taps over cap 3000: clk_t1 3200' in out, out
    assert js['sinks']['clk_t1'] == 3000 and js['over_cap'] == [], js
    for i in range(200):
        assert nets[f'u_fl_L{i}'] == nets[f'lau{i}'], i       # never split from its launch flop
    assert sum(1 for i in range(200) if nets[f'lau{i}'] == 'n_clk_t2') == 100
    assert all(nets[f'p1_{i}'] == 'n_clk_t1' for i in range(2800))


def test_no_room_within_reach_warns_loudly(tmp_path):
    body = r'''
addtap clk 0; addtap clk_t1 1000
fills a 8 0
fills b 8 1000
for {set i 0} {$i < 2} {incr i} {
  ff lau$i 1000
  mkinst u_fl_L$i m_dl 100
  link lau$i u_fl_L$i
}
'''
    out, nets, js = run(tmp_path, body, 'set ::env(OT_TAP_PITCH_UM) 1000\nset ::env(OT_TAP_MAX_SINKS) 10')
    assert 'WARN CAP_AFTER_HOP_LATCH clk_t1 keeps 12 sinks > cap 10' in out, out
    assert 'WARN OVER_CAP 1 taps > cap 10 sinks in the final assignment: "clk_t1"' in out, out
    assert js['over_cap'] == ['clk_t1'] and js['sinks'] == {'clk': 8, 'clk_t1': 12}


def test_under_cap_prints_recheck_pass(tmp_path):
    body = 'addtap clk 0; addtap clk_t1 1000\nfills a 5 0\nfills b 5 1000\n'
    out, nets, js = run(tmp_path, body, 'set ::env(OT_TAP_PITCH_UM) 1000')
    assert 'cap recheck after hop latches: all 2 taps <= cap 3000' in out, out
    assert js['over_cap'] == [] and 'WARN' not in out
