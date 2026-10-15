#!/usr/bin/env python3
"""Check the proposed VM hard-child packing with the production cluster rules."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tools/ref_tile'))
spec = importlib.util.spec_from_file_location('native_ref_tile', R / 'tools/ref_tile/ref_tile.py')
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
p = R / 'physical/s81_die_pins/v20_vm_static_standard/layout_candidate.json'
raw = p.read_bytes()
candidate = json.loads(raw)
nodes = [dict(name=n['name'], master=n['master'], idx=i, kind='child',
              x=n['xy_um'][0], y=n['xy_um'][1],
              w=n['outline_um'][0], h=n['outline_um'][1], offtrack=None)
         for i, n in enumerate(candidate['nodes'])]
checks = rt.floorplan_checks(dict(kind='cluster', pins={f: ['pending'] for f in 'NSEW'}),
                            *candidate['parent_outline_um'], nodes, None)
counts = collections.Counter(f'{severity}:{kind}' for severity, kind, *_ in checks)
report = dict(scope='Production hard-child geometry audit only; pins/real views/clock/cuts unproven',
              input_path=str(p.relative_to(R)), input_sha256=hashlib.sha256(raw).hexdigest(),
              tool_sha256=hashlib.sha256((R / 'tools/ref_tile/ref_tile.py').read_bytes()).hexdigest(),
              status='FAIL' if any(c[0] == 'FAIL' for c in checks) else 'PASS',
              parent_outline_um=candidate['parent_outline_um'], hard_children=len(nodes),
              rules=dict(channel_um=rt.CHANNEL_UM, child_lattice_um=rt.CHILD_LATTICE_UM,
                         diagnostic_abut_plan=False), counts=dict(counts), checks=checks,
              remedy='Repack real hard children with production20um channels and audit all actual pins/cuts; preserve current bank leaf geometry')
out = R / 'results/physical/die_iter_1012/s81/vm_native_parent_audit_1015'
out.mkdir(parents=True, exist_ok=True)
(out / 'audit.json').write_text(json.dumps(report, indent=1) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'hard_children', 'counts']}))
