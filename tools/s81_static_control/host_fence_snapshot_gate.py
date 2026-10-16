#!/usr/bin/env python3
"""Source-pinned exact-edge fence retiming proof plus captured-payload mutant."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv'
BASELINE = 'b2f33895e752e8181d38995af652bae212f8a2d9'
p = argparse.ArgumentParser()
p.add_argument('out', type=Path)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
old = (ROOT / 'tests/s81/ot_s81_fence_pre_capture_ref.sv').read_text()
assert hashlib.sha256(old.encode()).hexdigest() == '92ad60d5d567382285be85aff5039bc6f59a705cdf659699ddc8ce4347c2ce32', 'legacy fixture changed'
(a.out / 'old.sv').write_text(old)
candidate = (ROOT / SOURCE).read_text()
needle = 'snapshot_h <= snapshot_seam;'
assert candidate.count(needle) == 1
(a.out / 'mutant.sv').write_text(candidate.replace(needle, "snapshot_h <= snapshot_seam ^ 32'h100;"))
cases = []
for cp, hp, phase, mutant in [(6,6,0,False),(6,6,1,False),(6,8,0,False),(8,6,0,False),(6,6,0,True)]:
    name = f'c{cp}_h{hp}_p{phase}' + ('_mutant' if mutant else '')
    exe = a.out / (name + '.vvp')
    src = a.out/'mutant.sv' if mutant else ROOT/SOURCE
    cmd = ['iverilog','-g2012','-DOT_S81_HOST_PHASESAFE','-s','tb_host_fence_snapshot',
           f'-Ptb_host_fence_snapshot.CP={cp}',f'-Ptb_host_fence_snapshot.HP={hp}',
           f'-Ptb_host_fence_snapshot.PHASE={phase}','-o',str(exe),str(src),str(a.out/'old.sv'),
           str(ROOT/'rtl/lib/ot_reset_sync.sv'),str(ROOT/'tests/s81/tb_host_fence_snapshot.sv')]
    build = subprocess.run(cmd,capture_output=True,text=True)
    (a.out/(name+'.build.log')).write_text(build.stdout+build.stderr)
    if build.returncode: raise SystemExit('FENCE_SNAPSHOT BUILD_FAIL '+name)
    run = subprocess.run(['vvp','-n',str(exe)],capture_output=True,text=True)
    output = run.stdout+run.stderr
    (a.out/(name+'.log')).write_text(output)
    passed = run.returncode == 0 and 'FENCE_SNAPSHOT PASS' in output
    if passed == mutant: raise SystemExit('FENCE_SNAPSHOT UNEXPECTED '+name+' '+output)
    if mutant and 'FENCE_SNAPSHOT FAIL exact timeline' not in output: raise SystemExit('FENCE_SNAPSHOT WRONG_MUTANT_FAILURE')
    print(output.strip())
    cases.append(dict(case=name,expected='fail' if mutant else 'pass',returncode=run.returncode))
record = dict(scope='Exact component timeline only; native HOST physical and die qualification remain open.',
              baseline_commit=BASELINE,source=SOURCE,source_sha256=hashlib.sha256(candidate.encode()).hexdigest(),cases=cases)
(a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
print('HOST_FENCE_SNAPSHOT_GATE PASS four exact-edge clock configurations and captured-payload mutant')
