"""A clock check cannot pass when the real family has no measured active tap."""
from pathlib import Path
import os
import shutil
import subprocess
import pytest

HOOK=Path(__file__).with_name('tap_balance.tcl')


def run_balance(family='clk', sinks=True, report_only=True):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script=r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc ord::get_db {} {return db}
proc tech {m} {return 1000}
proc db {m args} {return master}
proc blk {m} {if {$m eq "getBTerms"} {return b0}}
proc b0 {m} {switch $m {getName {return ck} getNet {return net}}}
proc net {m} {global have_sinks; switch $m {getName {return ck} getITerms {if {$have_sinks} {return it};return {}}}}
proc it {m} {switch $m {getMTerm {return mt} getInst {return flop}}}
proc mt {m} {switch $m {getIoType {return INPUT} getName {return CK}}}
proc flop {m} {switch $m {getMaster {return master} getName {return u_state}}}
proc master {m} {return DFFHQNx1}
proc get_pins {args} {return [lindex $args end]}
proc get_property {pin property} {return clk}
proc get_full_name {pin} {return $pin}
proc all_clocks {} {return clk}
proc set_propagated_clock {args} {}
proc estimate_parasitics {args} {}
proc ot_cf_wire_transition {args} {return 250.0}
proc ot_cf_wire {args} {return 250.0}
proc ot_cf_refresh {} {}
'''
    script+=f'\nset have_sinks {int(sinks)}\n'
    script+=f'if {{[catch {{source {{{HOOK}}}}} message]}} {{puts stderr $message;exit 1}}\n'
    env={k:v for k,v in os.environ.items() if not k.startswith('OT_TAP_')}
    env.update(OT_TAP_PORT=family,OT_TAP_CLOCK='clk',OT_TAP_REPORT_ONLY=str(int(report_only)))
    return subprocess.run(['tclsh'],input=script,text=True,capture_output=True,env=env)


@pytest.mark.parametrize('report_only',[False,True])
@pytest.mark.parametrize('family,sinks',[('clk',True),('ck',False)])
def test_empty_measurement_fails_closed(report_only,family,sinks):
    p=run_balance(family,sinks,report_only)
    assert p.returncode!=0
    assert 'OT_TAP_CHECK FAIL: no active measured taps' in p.stderr
    assert 'available clock ports {ck}' in p.stderr
    assert 'OT_TAP_CHECK OK' not in p.stdout
    assert '1000000000' not in p.stdout


def test_actual_ck_family_with_clk_sdc_clock_is_measured():
    p=run_balance('ck',True,True)
    assert p.returncode==0,p.stderr
    assert 'ck=250(250-250,1)' in p.stdout
    assert 'sink insertion 250..250 ps' in p.stdout
