"""FLOW-20 11-01: cts_repair_protect.tcl keeps CTS-stage repair_timing off the clock tree (OpenSTA RequiredCmp assert)."""
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name('cts_repair_protect.tcl')

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc blk {m} {return {nck ndat}}
foreach o {nck ndat cb ff dbuf} { set ::dt($o) 0 }
proc nck {m args} {switch $m {getSigType {return CLOCK} getITerms {return {cbo ffc}} isDoNotTouch {return $::dt(nck)} setDoNotTouch {set ::dt(nck) [lindex $args 0]}}}
proc ndat {m args} {switch $m {getSigType {return SIGNAL} getITerms {return dbo}}}
proc cbo {m} {switch $m {isOutputSignal {return 1} getInst {return cb}}}
proc ffc {m} {switch $m {isOutputSignal {return 0} getInst {return ff}}}
proc dbo {m} {switch $m {isOutputSignal {return 1} getInst {return dbuf}}}
proc mbuf {m} {return BUFx24_ASAP7_75t_R}
foreach o {cb ff dbuf} { proc $o {m args} "switch \$m {getMaster {return mbuf} isDoNotTouch {return \$::dt($o)} setDoNotTouch {set ::dt($o) \[lindex \$args 0\]}}" }
proc repair_timing_helper {args} { set ::during [list $::dt(cb) $::dt(nck) $::dt(dbuf) $::dt(ff)]; return RT_$args }
'''


def run(extra=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = MOCK + extra + f'\nsource {{{HOOK}}}\nputs "R [repair_timing_helper -x]"\n' \
        + 'puts "DURING [expr {[info exists ::during] ? $::during : {none}}]"\nputs "AFTER $::dt(cb) $::dt(nck)"\n'
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_clock_tree_dont_touch_only_during_repair():
    p = run()
    assert p.returncode == 0, p.stderr
    assert 'R RT_-x' in p.stdout
    assert 'DURING 1 1 0 0' in p.stdout          # CTS buffer + clock net locked; data buffer and sink flop free
    assert 'AFTER 0 0' in p.stdout               # released for later stages
    assert 'dont_touch clock buffers/inverters=1 clock nets=1' in p.stdout


def test_opt_out_env():
    p = run('set ::env(OT_CTS_REPAIR_PROTECT) 0\n')
    assert p.returncode == 0, p.stderr
    assert 'OT_CTS_REPAIR_PROTECT off' in p.stdout and 'DURING 0 0 0 0' in p.stdout


def test_release_on_error():
    extra = 'proc repair_timing_helper {args} {error BOOM}\n'
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = MOCK + extra + f'\nsource {{{HOOK}}}\nputs "C [catch {{repair_timing_helper}} m] $m"\nputs "AFTER $::dt(cb) $::dt(nck)"\n'
    p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert 'C 1 BOOM' in p.stdout and 'AFTER 0 0' in p.stdout, p.stdout + p.stderr


def test_gen_phys_wires_hook():
    src = Path(__file__).with_name('gen_phys.py').read_text()
    assert '"cts_repair_protect.tcl", "pg_connect.tcl")' in src and 'source /work/cts_repair_protect.tcl' in src
