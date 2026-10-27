"""Check the real ORFS default repair invocation keeps HB4 out of setup."""
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / 'physical/common_flow/hold_pad_hb4.tcl'

@pytest.mark.parametrize('selectors,expected', [('', ['-setup', '-hold']), ('-setup', ['-setup']), ('-hold', ['-hold']), ('-setup -hold', ['-setup', '-hold'])])
def test_hold_only_cells_in_both_default_and_explicit_repair(selectors, expected):
    # API stubs record the cell availability at each original-tool invocation.
    script = '''
set available 0
proc repair_timing {args} {puts "CALL [lindex $args 0] $::available"}
proc get_lib_cells {args} {return {HB4}}
proc unset_dont_use {args} {set ::available 1}
proc set_dont_use {args} {set ::available 0}
proc get_cells {args} {return {}}
'''
    script += 'source {' + str(HOOK) + '}\n'
    script += 'repair_timing ' + selectors + ' -setup_margin 0 -hold_margin 5 -max_buffer_percent 100\n'
    script += 'puts "FINAL $::available"\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    calls = [line.split()[1:] for line in result.stdout.splitlines() if line.startswith('CALL ')]
    assert calls == [[s, '1' if s == '-hold' else '0'] for s in expected]
    assert 'FINAL 0' in result.stdout
