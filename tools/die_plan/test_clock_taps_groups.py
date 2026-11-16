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


GROUP_ON = "set ::env(OT_TAP_GROUP_RE) {(?:^|[/.])(u_ft_[A-Za-z0-9]+_s[0-9]+)[/.]}"


def test_station_group_whole_and_relay_follows(tmp_path):
    # 60 filler flops on each tap so neither tap is "small"
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    p = run(tmp_path, STATION + fill, env=GROUP_ON)
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'GROUPS 1 groups' in out and '1 were split over taps by the nearest-flop pass' in out, out
    for b in range(3):
        assert f'NET ck_u_ft_ft0_s1/q_{b} nclk' in out
    assert 'NET ck_u_rrl_3/q nclk' in out          # relay re-hung on its station's tap
    assert 'followers 1' in out


def test_small_tap_merged_into_neighbour(tmp_path):
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(60)) + 'mkflop lone 1000\n'
    p = run(tmp_path, fill, env='set ::env(OT_TAP_PITCH_UM) 2400\nset ::env(OT_TAP_MIN_SINKS) 50')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_lone nclk' in p.stdout
    assert 'clk_t1(1)->clk' in p.stdout
    assert '"dropped": ["clk_t1"]' in (tmp_path / 'ot_clock_taps.json').read_text()


def test_small_tap_beyond_pitch_kept(tmp_path):
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(60)) + 'mkflop lone 1000\n'
    p = run(tmp_path, fill, env='set ::env(OT_TAP_PITCH_UM) 600\nset ::env(OT_TAP_MIN_SINKS) 50')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_lone nt1' in p.stdout
    assert 'WARN clk_t1 keeps 1 sinks' in p.stdout


def test_default_is_nearest_sink_no_group_no_merge(tmp_path):
    """FLOW-CANARY 10-25: grouping and the small-tap merge are opt-in; the default is the 202a nearest-sink
    assignment (on by default they regressed the s81/KV/QC canaries' structural FF hold gate)."""
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(60)) + 'mkflop lone 1000\n'
    p = run(tmp_path, STATION + fill, env='set ::env(OT_TAP_PITCH_UM) 2400')
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'GROUPS' not in out and 'MIN ' not in out, out
    assert 'NET ck_u_ft_ft0_s1/q_2 nt1' in out      # nearest flop, group not forced together
    assert 'NET ck_u_rrl_3/q nt1' in out            # relay not re-hung
    assert 'NET ck_lone nt1' in out                 # small tap not merged


MACRO = r'''
# hard macro: origin x=0 (nearest clk) but its clock pin at x=1000 (nearest clk_t1)
proc blkm {m} {if {$m eq "isBlock"} {return 1}; return PHY}
lappend INSTS u_core; set NET(ck_u_core) nclk
proc u_core {m args} {switch $m {getName {return u_core} getLocation {return {0 0}} getMaster {return blkm}
                                  getITerms {return ck_u_core}}}
proc ck_u_core {m args} {
  global NET
  switch $m {getMTerm {return inp} getInst {return u_core} getNet {return $NET(ck_u_core)} getAvgXY {return {1 1000 0}}
             disconnect {set NET(ck_u_core) NULL} connect {set NET(ck_u_core) [lindex $args 0]}}}
'''


def test_macro_clock_pin_goes_to_tap_nearest_the_pin(tmp_path):
    """DIE-KV-60 11-01: a hard macro is assigned by its clock PIN location (getAvgXY), not its origin."""
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    p = run(tmp_path, MACRO + fill, env='set ::env(OT_TAP_PITCH_UM) 2400')
    assert p.returncode == 0, p.stderr
    assert 'NET ck_u_core nt1' in p.stdout, p.stdout


HOPLATCH = r"""
# TYPE-SAFE-1 11-06: launch station flop at x=0 (tap clk) drives ft hop lockup latch u_fl_ft0_s0 at x=900 (nearest
# clk_t1) directly; the latch must follow its launch station's tap (clk), a plain flop at x=900 stays nearest (clk_t1)
proc dllm {m} {return DLLx1_ASAP7_75t_R}
proc dinp {m} {if {$m eq "getIoType"} {return INPUT}; return D}
mkflop u_ft_ft0_s0/q_0 0
mkflop u_fl_ft0_s0/q_0 900
mkflop plain 900
rename u_fl_ft0_s0/q_0 lat_orig
proc u_fl_ft0_s0/q_0 {m args} {if {$m eq "getMaster"} {return dllm}; lat_orig $m {*}$args}
proc nd {m args} "netproc nd \$m {*}\$args"
set NET(q_u_ft_ft0_s0/q_0) nd
proc q_u_ft_ft0_s0/q_0 {m args} {switch $m {getMTerm {return outp} getInst {return u_ft_ft0_s0/q_0} getNet {return nd}}}
set NET(d_u_fl_ft0_s0/q_0) nd
proc d_u_fl_ft0_s0/q_0 {m args} {switch $m {getMTerm {return dinp} getInst {return u_fl_ft0_s0/q_0} getNet {return nd}}}
"""


def test_hop_latch_follows_launch_station_tap(tmp_path):
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    p = run(tmp_path, HOPLATCH + fill)
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'NET ck_u_fl_ft0_s0/q_0 nclk' in out, out
    assert 'NET ck_plain nt1' in out
    assert 'hop latches: 1 on their launch station' in out and '(1 re-hung)' in out, out


CORETAP = r"""
# DIE-HEAD-87 11-08: OpenDB stores generate-loop instance names with escaped brackets; core_taps.txt carries the
# plain name.  The core tap must still find the pair macro and move its clock pin to clk_c0.
proc dffm {m} {if {$m eq "isBlock"} {return 0}; return DFFHQNx1}
proc ckm {m} {if {$m eq "getName"} {return clk}; if {$m eq "getIoType"} {return INPUT}; return clk}
set PAIR {u_core.u.g_pp\[0\].u_pair}
set NET(ckp) nclk
proc ckp {m args} {
  global NET PAIR
  switch $m {getMTerm {return ckm} getInst {return $PAIR} getNet {return $NET(ckp)}
             disconnect {set NET(ckp) NULL} connect {set NET(ckp) [lindex $args 0]}}}
proc pairi {m args} {switch $m {getITerms {return ckp} getName {return $::PAIR}}}
proc bc0 {m args} {switch $m {getName {return clk_c0} getNet {return nc0}}}
proc nc0 {m args} "netproc nc0 \$m {*}\$args"
rename blk blk_orig
proc blk {m args} {
  switch $m {
    findBTerm {if {[lindex $args 0] eq "clk_c0"} {return bc0}; return [blk_orig findBTerm {*}$args]}
    findInst {if {[lindex $args 0] eq $::PAIR} {return pairi}; return NULL}
    default {return [blk_orig $m {*}$args]}
  }
}
"""


def test_core_tap_finds_escaped_generate_instance(tmp_path):
    """DIE-HEAD-87 11-08: hd_lep0N vF left all 4 pair core taps empty (plain name vs escaped OpenDB name)."""
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    taps = tmp_path / 'core_taps.txt'
    taps.write_text('# port inst pin|* early_ps insertion_ps\nclk_c0 u_core.u.g_pp[0].u_pair clk 79.22 529.22\n')
    p = run(tmp_path, CORETAP + fill, env=f'set ::env(OT_CORE_TAPS) {{{taps}}}\nset ::env(OT_TAP_PITCH_UM) 2400')
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert 'missing' not in out, out
    assert 'core tap clk_c0 <- u_core.u.g_pp[0].u_pair/clk: 1 clock pin(s)' in out, out
    assert 'NET ckp' not in out or 'NET ckp nc0' in out


SKIPMAC = r'''
# KV-PC-DELTA-1115: a hard macro covers the clk_t1 port (x=1000, y=0)
proc blkm {m} {if {$m eq "isBlock"} {return 1}; return PHY}
proc macbox {m} {switch $m {xMin {return 900} xMax {return 1100} yMin {return -10} yMax {return 10}}}
lappend INSTS u_mac
proc u_mac {m args} {switch $m {getName {return u_mac} getMaster {return blkm} getBBox {return macbox} getITerms {return {}}}}
'''


def test_tap_over_macro_takes_no_sink_when_opted_in(tmp_path):
    fill = ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    p = run(tmp_path, SKIPMAC + fill, env='set ::env(OT_TAP_PITCH_UM) 2400\nset ::env(OT_TAP_SKIP_MACRO) 1')
    assert p.returncode == 0, p.stderr
    assert 'skip tap clk_t1 over macro u_mac' in p.stdout, p.stdout
    assert 'NET ck_f100 nclk' in p.stdout
    off = run(tmp_path, SKIPMAC + fill, env='set ::env(OT_TAP_PITCH_UM) 2400')
    assert 'NET ck_f100 nt1' in off.stdout, off.stdout        # default unchanged


def test_cap_spill_reach_is_opt_in(tmp_path):
    fill = ''.join(f'mkflop f{i} 0\n' for i in range(100))
    env = 'set ::env(OT_TAP_PITCH_UM) 600\nset ::env(OT_TAP_MAX_SINKS) 40'
    p = run(tmp_path, fill, env=env)
    assert p.returncode == 0, p.stderr
    assert 'WARN clk keeps 100 sinks > cap 40' in p.stdout, p.stdout       # half-pitch reach 300 < 1000: stuck (as before)
    q = run(tmp_path, fill, env=env + '\nset ::env(OT_TAP_SPILL_UM) 1500')
    assert q.returncode == 0, q.stderr
    assert 'spill reach 1500 um' in q.stdout, q.stdout


RESET_COHORT = r"""
# Adjacent same-logical-clock source/collector, with a remote descendant.
# Without atomic group ownership, ct_follow drags only the reset source
# to the descendant tap, splitting the deliberately compact cohort.
mkflop u_rrl_94/q 10
mkflop u_cland_collect_rst_rl_94/ready_o 20
mkflop distant0 990 rq
mkflop distant1 1000 rq
proc q_u_rrl_94/q {m args} {switch $m {getMTerm {return outp} getInst {return u_rrl_94/q} getNet {return rq}}}
set NET(q_u_rrl_94/q) rq
"""


def test_explicit_reset_cohort_survives_both_follower_passes(tmp_path):
    env = "set ::env(OT_TAP_GROUP_RE) {(?:^|[/.])(u_)(?:rrl_94|cland_collect_rst_rl_94)[/.]}"
    p = run(tmp_path, RESET_COHORT, env=env)
    assert p.returncode == 0, p.stderr
    assert "NET ck_u_rrl_94/q nclk" in p.stdout
    assert "NET ck_u_cland_collect_rst_rl_94/ready_o nclk" in p.stdout
    assert "followers after cap pass:" in p.stdout


def test_atomic_reset_cohort_negative_control_detects_original_split(tmp_path, monkeypatch):
    global HOOK
    mutant = tmp_path / "clock_taps_mutant.tcl"
    original = HOOK
    text = original.read_text()
    guard = "    if {[dict exists $ct_group_owned $cit]} continue\n"
    assert text.count(guard) == 1
    mutant.write_text(text.replace(guard, "    # mutant: original unprotected follower\n"))
    monkeypatch.setitem(globals(), "HOOK", mutant)
    env = "set ::env(OT_TAP_GROUP_RE) {(?:^|[/.])(u_)(?:rrl_94|cland_collect_rst_rl_94)[/.]}"
    p = run(tmp_path, RESET_COHORT, env=env)
    assert p.returncode == 0, p.stderr
    assert "NET ck_u_rrl_94/q nt1" in p.stdout
    assert "NET ck_u_cland_collect_rst_rl_94/ready_o nclk" in p.stdout



def test_fixed_output_group_uses_declared_forwarded_clock(tmp_path):
    env = GROUP_ON + "\nset ::env(OT_TAP_GROUP_FIXED) {u_ft_ft0_s1:clk_t1}"
    p = run(tmp_path, STATION, env=env)
    assert p.returncode == 0, p.stderr
    for bit in range(3):
        assert f"NET ck_u_ft_ft0_s1/q_{bit} nt1" in p.stdout


def test_fixed_output_group_survives_cap_and_min_merges(tmp_path):
    env = (GROUP_ON + "\nset ::env(OT_TAP_GROUP_FIXED) {u_ft_ft0_s1:clk_t1}"
           "\nset ::env(OT_TAP_MAX_SINKS) 3"
           "\nset ::env(OT_TAP_REASSIGN_UM) 1500"
           "\nset ::env(OT_TAP_MIN_SINKS) 50"
           "\nset ::env(OT_TAP_POST_MIN_SINKS) 50"
           "\nset ::env(OT_TAP_POST_MIN_UM) 1500")
    p = run(tmp_path, STATION, env=env)
    assert p.returncode == 0, p.stderr
    for bit in range(3):
        assert f"NET ck_u_ft_ft0_s1/q_{bit} nt1" in p.stdout


def test_fixed_output_unknown_clock_port_refuses(tmp_path):
    p = run(tmp_path, STATION, env=GROUP_ON +
            "\nset ::env(OT_TAP_GROUP_FIXED) {u_ft_ft0_s1:clk_t99}")
    assert p.returncode != 0
    assert "unknown or non-grid clock port" in p.stderr


def test_fixed_output_missing_group_refuses(tmp_path):
    p = run(tmp_path, STATION, env=GROUP_ON +
            "\nset ::env(OT_TAP_GROUP_FIXED) {missing:clk_t1}")
    assert p.returncode != 0
    assert "group has no sinks" in p.stderr
