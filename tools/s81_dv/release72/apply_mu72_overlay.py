#!/usr/bin/env python3
"""S81-DIE72-G2: bind the four end parents to the MU72 assembly tops (update the existing master rows in place:
module, clocks, view note; ports / straps / landing data unchanged).  Usage: apply_mu72_overlay.py BIND_TABLE
S81-LINK5 10-21: an overlay row may carry 'clone_from' (create a missing master row as a copy of an existing one, e.g.
dsdv_slice_lepw_mab from dsdv_slice_lepw_mu), 'ports_add' (extra plan ports merged into the row's ports: the pair-B
tx2/tx3/rx2/rx3 of the copy-A/B s_0N end) and 'link_slots' (informational: which die SerDes slot each lane port uses)."""
import copy, json, sys
from pathlib import Path
p = Path(sys.argv[1]); t = json.loads(p.read_text())
o = json.loads(Path(__file__).with_name('mu72_overlay.json').read_text())
for m, e in o['masters'].items():
    e = dict(e); add = e.pop('mode_unused_add', []); src = e.pop('clone_from', None); padd = e.pop('ports_add', {})
    if m not in t['masters'] and src:
        t['masters'][m] = copy.deepcopy(t['masters'][src])
    row = t['masters'][m]
    row.update(e)
    if padd:
        row['ports'] = {**row['ports'], **padd}
    mu = row.setdefault('mode_unused', [])
    for a in add:
        if not any(x.get('port') == a['port'] and x.get('when') == a['when'] for x in mu):
            mu.append(a)
t.setdefault('rtl_widths', {}).update(o['rtl_widths'])
p.write_text(json.dumps(t, indent=1) + '\n')
print('MU72_OVERLAY', ' '.join(f"{m}->{e['module']}" for m, e in o['masters'].items()))
