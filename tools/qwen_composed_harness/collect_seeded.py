#!/usr/bin/env python3
"""Collect the seeded per-layer whole-token runs (runseed.sh) into one receipt.

Run on each host; prints one JSON object per run: name, layer, exit, verdict
line, layer X errors (functional_cycles.json), core cycles, memo counters.
"""
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv) > 1 else '/srv/opentallas-scratch/claude/qwen-wholetoken-1014/runs')
for d in sorted(root.glob('seed_*')):
    r = {'name': d.name}
    m = re.match(r'seed_(l(\d+|head)|mut_l0r3)_v\d+', d.name)
    r['layer'] = m.group(2) if m and m.group(2) else ('mutant_l0r3' if m else None)
    st = d / 'exit_status.txt'
    r['exit'] = int(st.read_text()) if st.exists() else None
    txt = ''
    for f in ('run.log', 'run.err'):
        p = d / f
        if p.exists(): txt += p.read_text(errors='replace')
    v = [l for l in txt.splitlines() if l.startswith(('PASS', 'FAIL'))]
    r['verdict'] = v[-1][:300] if v else None
    prog = [l for l in txt.splitlines() if l.startswith('PROGRESS')]
    r['last_progress'] = prog[-1] if prog else None
    fc = list((d / 'actual').rglob('functional_cycles.json'))
    r['functional_cycles'] = [json.loads(p.read_text()) for p in fc if 'embedding' not in str(p)]
    g = d / 'actual' / 'head' / 'global_argmax.txt'
    r['head_global_argmax'] = g.read_text().strip() if g.exists() else None
    t = d / 'actual' / 'terminal.json'
    if t.exists(): r['terminal'] = json.loads(t.read_text())
    print(json.dumps(r))
