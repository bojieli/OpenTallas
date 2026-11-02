import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).with_name('grt_final_full.tcl')


def run(extra='', special=0, clocks=1, route_error=False):
    tcl = f'''
namespace eval ord {{proc get_db_block {{}} {{return block}}}}
proc block {{method}} {{return {{ {'net' if clocks else ''} }}}}
proc net {{method}} {{
  switch $method {{getSigType {{return CLOCK}} isSpecial {{return {special}}} getName {{return clk}}}}
}}
proc global_route {{args}} {{puts "ROUTE $args"; {'error overflow' if route_error else ''}}}
proc estimate_parasitics {{args}} {{puts "ESTIMATE $args"}}
proc write_guides {{args}} {{puts "GUIDES $args"}}
{extra}
if {{[catch {{source {{{SCRIPT}}}}} msg]}} {{puts stderr $msg;exit 1}}
'''
    env = {k:v for k,v in os.environ.items() if k not in ('OT_GRT_FINAL_FULL','GRT_OVERFLOW_ITERS')}
    return subprocess.run(['tclsh'], input=tcl, text=True, capture_output=True, env=env)


ON = 'set ::env(OT_GRT_FINAL_FULL) 1\nset ::env(RESULTS_DIR) /results\nset ::env(REPORTS_DIR) /reports'


def test_default_off():
    assert run().returncode == 0
    assert 'ROUTE' not in run().stdout


def test_final_full_graph_keeps_clock_routing_and_reports():
    r=run(ON)
    assert r.returncode == 0, r.stderr
    assert 'ROUTE -congestion_iterations 50' in r.stdout
    assert '-end_incremental' not in r.stdout and '-allow_congestion' not in r.stdout
    assert 'GUIDES /results/route.guide' in r.stdout


@pytest.mark.parametrize('extra,special,clocks,why', [
    (ON+'\nset ::env(GRT_OVERFLOW_ITERS) 49',0,1,'>=50'),
    (ON,1,1,'SPECIAL'),(ON,0,0,'no CLOCK'),
    ('set ::env(OT_GRT_FINAL_FULL) 1',0,1,'RESULTS_DIR')])
def test_invalid_context_refuses(extra,special,clocks,why):
    r=run(extra,special,clocks)
    assert r.returncode != 0 and why in r.stderr
    assert 'ROUTE' not in r.stdout


def test_overflow_failure_propagates_without_writing_guides():
    r=run(ON,route_error=True)
    assert r.returncode != 0 and 'overflow' in r.stderr
    assert 'GUIDES' not in r.stdout
