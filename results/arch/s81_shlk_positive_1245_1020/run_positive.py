#!/usr/bin/env python3
"""Run seqhost positives without implicitly running a legacy mutant campaign.

The closure job declares all current mutants separately with committed witnesses.
Keep the aggregate's seed, paired-row, collision and region-drop positive cases.
"""
from pathlib import Path
import subprocess
import sys

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
script = 'rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh'
subprocess.run(['bash', script, str(out), '1 2', 'base'], check=True)
exe = out / 'base/tb'
for name, args, expected in [
    ('pair1', ['+seed=1', '+pair=1'], 'SEQHOST PASS'),
    ('pair2', ['+seed=2', '+pair=1'], 'SEQHOST PASS'),
    ('collision', ['+seed=7', '+collide=1'], 'PASS (fault raised)'),
    ('region_drop', ['+seed=3', '+stdrop=1'], 'PASS (fault raised)'),
]:
    r = subprocess.run([str(exe), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '.log')).write_text(r.stdout)
    print(r.stdout, end='', flush=True)
    assert r.returncode == 0 and expected in r.stdout, (name, r.returncode)
print('SEQHOST_POSITIVE_CASES PASS 6', flush=True)
