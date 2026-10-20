#!/usr/bin/env python3
"""Bounded role audit using existing complete-init proof binaries; no rebuild."""
from pathlib import Path
import json
import subprocess

rows = []
for seed in [0,8,16,24,32,64,128,256,512,768,992,1000,2000,4000,8000,16000]:
    role=0
    for variant, binary in [('old_replay', './obj_boot_replay_pass/Vtb'),
                            ('private_ce_trace', './obj_guard_trace3_pass/Vtb')]:
        log = Path(f'role{role}_{variant}_seed{seed}.log')
        with log.open('w') as f:
            run = subprocess.run([binary, f'+seed={seed}'], stdout=f, stderr=subprocess.STDOUT)
        text = log.read_text()
        diffs = [line for line in text.splitlines() if any(x in line for x in
                 ('GUARD_VISIBLE_DIFF', 'PROMPT_STATE FAIL', 'GUARD_VISIBLE_FAIL', 'BOOT_PIN_DIFF'))]
        row = dict(role=role, requested_seed=seed, binary=binary, exitcode=run.returncode,
                   log=str(log), first_differences=diffs[:16],
                   scope='100-cycle source-state diagnosis; old replay output compare starts after reset; private CE trace compares every edge')
        rows.append(row)
        print(json.dumps(row), flush=True)
Path('role0_probe_summary.json').write_text(json.dumps(rows, indent=2)+'\n')
