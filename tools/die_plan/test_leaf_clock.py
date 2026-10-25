from pathlib import Path
import re
import shutil
import subprocess
import pytest


def test_leaf_affinity_never_crosses_real_clock_identity():
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    text = Path(__file__).with_name('leaf_affinity.tcl').read_text()
    proc = re.search(r'proc la_same_clock \{members\} \{.*?\n\}', text, re.S).group()
    script = proc + '''
set la_clock [dict create a clk_a b clk_a c clk_b unknown {}]
foreach {members expected} {{a b} 1 {a c} 0 {a unknown} 0 {a missing} 0 {} 0} {
  set actual [la_same_clock $members]
  if {$actual != $expected} {error "wrong domain guard: $members got $actual"}
}
puts PASS
'''
    run = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert run.returncode == 0 and not run.stderr and run.stdout.strip() == 'PASS', run.stderr
    # Apply the actual clock identity before choosing/reconnecting any clock net.
    assert text.index('if {![la_same_clock $mem]}') < text.index('set net [$la_blk findNet $best]')
