#!/usr/bin/env python3
"""HBM-ARCH: after gen_arch.py -- plan the die IO windows (die_io.py) and mark the host UCIe (host_N) as the host link."""
import json, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
plan = sys.argv[1]
subprocess.run([sys.executable, os.path.join(HERE, '..', '..', '..', 'tools', 'die_plan', 'die_io.py'), 'plan', plan, '--inplace'],
               check=True, stdout=subprocess.DEVNULL)
P = json.load(open(plan))
for w in P['die'].get('io', []):
    w.pop('host', None)
    if w.get('iface') == 'ucie':
        w['host'] = True
        w['note'] = (w.get('note', '') + ' HBM-ARCH: as-built host link = host_N UCIe x64 (ot_pdie_ucie_col)').strip()
json.dump(P, open(plan, 'w'), indent=0)
print('io windows', [(w['name'], w.get('iface'), w['sites'], w['signals'], w.get('host', False)) for w in P['die']['io']])
