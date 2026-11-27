"""tap_relay_cohort.tcl (QC-TTC-R2 11-23): consecutive reset/run relays at one site share one clock tap (the launching relay
follows the relay it feeds); relays far apart keep their own tap; no effect unless the kit opts in.  Tiny OpenDB mock."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
HOOK = HERE / 'tap_relay_cohort.tcl'

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc dff {m} {return DFFHQNx1}
proc inv {m} {return INVx3}
proc din {m} {return D}
set INSTS {}
proc blk {m args} {global INSTS; return $INSTS}
proc tapproc {name m args} {if {$m eq "getName"} {return $name}; return {}}
foreach n {tA tB} {proc $n {m args} "tapproc $n \$m"}
# a relay: clock pin ck<k>, output pin q<k> on net n<k> (loads listed in LOAD(n<k>)), data pin d<k>
proc mk {k name x tap} {
  global NET LOC INSTS
  set LOC($k) $x; set NET($k) $tap; lappend INSTS i$k
  proc i$k {m args} "global LOC; switch \$m {getName {return {$name}} getLocation {return \[list \$LOC($k) 0\]} getMaster {return dff} findITerm {return ck$k} getITerms {return {q$k}}}"
  proc ck$k {m args} "global NET; switch \$m {getNet {return \$NET($k)} disconnect {set NET($k) NULL} connect {set NET($k) \[lindex \$args 0\]}}"
  proc q$k {m args} "switch \$m {isOutputSignal {return 1} getNet {return n$k} default {return 0}}"
  proc d$k {m args} "switch \$m {isInputSignal {return 1} getInst {return i$k} getMTerm {return din} default {return 0}}"
  proc n$k {m args} "global LOAD; switch \$m {getName {return n$k} getITerms {return \[expr {\[info exists LOAD($k)\] ? \$LOAD($k) : {}}\]}}"
}
set ct_taps {{tA tA 0 0} {tB tB 100 0}}
mk 1 {u_bound.u_rrl_77/q$_DFF_P_} 10 tA
mk 2 {u_bound.u_rrl_78/q$_DFF_P_} 11 tB
mk 3 {u_bound.u_rrl_79/q$_DFF_P_} 12 tA
mk 4 {u_bound.u_srl_9/q$_DFF_P_} 900 tB
mk 5 {u_bound.u_core.u_7/q$_DFF_P_} 11 tB
set LOAD(1) d2
set LOAD(2) d3
set LOAD(3) d4
set LOAD(4) d5
'''


def run(env=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = (MOCK + env + f'\nproc wrap {{}} {{ global ct_taps; source {{{HOOK}}} }}\n'
              + 'if {[catch wrap msg]} {puts stderr $msg; exit 1}\n'
              + 'foreach k [lsort -integer [array names NET]] {puts "NET $k $NET($k)"}\n')
    r = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout, dict(x.split()[1:] for x in r.stdout.splitlines() if x.startswith('NET '))


def test_same_site_chain_shares_the_tail_tap_and_far_hop_is_left():
    out, nets = run()
    assert nets == {'1': 'tA', '2': 'tA', '3': 'tA', '4': 'tB', '5': 'tB'}
    assert 'clock pins moved 1' in out


def test_site_radius_bounds_the_cohort():
    _, nets = run('set ::env(OT_TAP_RELAY_COHORT_UM) 0.5\n')
    assert nets['2'] == 'tB'


def test_wiring_is_opt_in():
    import json
    c = (HERE / 'clock_taps.tcl').read_text()
    assert re.search(r'OT_TAP_RELAY_COHORT\) eq "1"\} \{\n source .*tap_relay_cohort\.tcl\]', c)
    g = (HERE / 'gen_phys.py').read_text()
    assert 'tap_relay_cohort_on(t, P.name)' in g and '"tap_relay_cohort.tcl"' in g
    assert '"tap_relay_cohort": {"type": "boolean"}' in (HERE / 'schema.py').read_text()
    assert 'tap_relay_cohort' in (HERE / 'die_plan.schema.json').read_text()


def test_default_on_for_s81_with_explicit_override():
    src = (HERE / 'gen_phys.py').read_text()
    m = re.search(r'^def tap_relay_cohort_on\(t, die=None\):.*?(?=^def )', src, re.S | re.M)
    ns = {}
    exec(m.group(0), ns)
    f = ns['tap_relay_cohort_on']
    assert f({}, 's81') is True and f({'clock': {}}, 's81') is True
    assert f({'clock': {'tap_relay_cohort': False}}, 's81') is False     # per-kit opt-out
    assert f({}, 's81_head') is False and f({}, 'qwen_compute') is False and f({}, None) is False
    assert f({'clock': {'tap_relay_cohort': True}}, 'qwen_compute') is True
