#!/usr/bin/env python3
"""Small deterministic four-quarter component proof, no admitted heavy build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[5]
base = Path(__file__).resolve().parent
sources = [base/'ot_hgi_coll_quarter_bridge.sv', base/'tb_hgi_coll_quarter_bridge.sv']
a.out.mkdir(parents=True, exist_ok=True)
records = []
with tempfile.TemporaryDirectory(prefix='hcoll-quarter-') as td:
    for name, param, expected in [('positive', None, 0), ('mut_select', 'MUT_SELECT', 1), ('mut_fault', 'MUT_FAULT', 1)]:
        binary = str(Path(td)/name)
        cmd = ['iverilog', '-g2012', '-s', 'tb_hgi_coll_quarter_bridge', '-o', binary]
        if param:
            cmd.append('-Ptb_hgi_coll_quarter_bridge.'+param+'=1')
        subprocess.run(cmd+[str(x) for x in sources], check=True)
        r = subprocess.run(['vvp', binary], capture_output=True, text=True)
        (a.out/(name+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode != expected:
            raise SystemExit(f'{name}: expected {expected}, got {r.returncode}')
        records.append(dict(case=name, exit=r.returncode, expected=expected))
manifest = dict(scope='component functional only; four real-quarter router instances, RX mux, two wire relays; no parent or physical qualification',
    source_sha256={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},
    cases=records)
(a.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('PASS quarter bridge baseline and two intended-failure controls')
