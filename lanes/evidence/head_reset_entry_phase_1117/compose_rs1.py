"""FABLE-FIX-HEAD-RESET rs1: functional compose of the strap-selected reset/START entry phase on a gated HEAD plan.
usage: compose_rs1.py PLAN.json MODEL.json   (edits PLAN in place; the copy, never the source prep)
Rows come from the r4 model (OLD NF15c clock): they prove the form composes and gates, not the final labels."""
import json, sys, hashlib, collections
from pathlib import Path
plan, model = Path(sys.argv[1]), Path(sys.argv[2])
P = json.loads(plan.read_text()); M = json.loads(model.read_text())
h = {r['part']: r['h_half_cycles'] for r in M['rows']}
types = P['partition_types']; root = P['reset']['root_part']
parts = {p['name']: p for p in P['partitions']}
missing = sorted(set(h) - set(parts)); assert not missing, missing[:5]
opt = sorted({parts[n]['type'] for n in h} - {parts[root]['type']})
skipped = sorted({parts[n]['type'] for n in h} & {parts[root]['type']})
for tn in opt:
    t = types[tn]; assert not t.get('hard'), tn
    t.setdefault('reset', {})['pin_entry_phase'] = True
    ids = t.setdefault('id_straps', [])
    assert all(s['name'] != 'strap_rst_ph' for s in ids)
    row = dict(name='strap_rst_ph', width=1, note='reset/START entry capture phase (pin_entry_phase)')
    ids.append(row)
n = collections.Counter()
for p in P['partitions']:
    if p['type'] not in opt:
        continue
    v = h.get(p['name'], 0)
    if p['name'] not in h:
        n['unmodelled_default_0'] += 1
    p.setdefault('id_straps', {})['strap_rst_ph'] = v % 2
    if v:
        p['reset_entry_phase'] = v
    n[f'h{v}'] += 1
plan.write_text(json.dumps(P, indent=1) + '\n')
print(json.dumps(dict(opted_types=len(opt), root_type_not_opted=skipped, parts=sum(v for k, v in n.items() if k.startswith('h')),
                      hist=dict(sorted(n.items())), plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest())))
