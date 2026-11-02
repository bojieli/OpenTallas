#!/usr/bin/env python3
"""QC MU pair sequencer and driven forwarded-control pads: deterministic one-block plan delta."""
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
x = json.loads(p.read_text())
t = x['partition_types']['glue']
old = {"u_sys_face.u_ot_pr_core.u_cseq.u_tx_rom", "u_sys_face.u_ot_pr_core.u_cseq.u_rx_rom"}
t['hard_cores'] = [h for h in t['hard_cores'] if h['inst'].removeprefix('u_bound.') not in old]
found = []
for c in t['contents']:
    if c['inst'] in ('u_bump_fwd_epoch', 'u_bump_fwd_lrst'):
        c['module'] = 'qfd_sigbump_input'
        c['bump_ports'] = [dict(pin='pad_i', dir='input', width=1,
            note='Forwarded QC/KV control signal from the package; driven die input, zero added cycles')]
        found.append(c['inst'])
assert len(found) == 2, found
for inst, px, py in (('bump_fwd_epoch', 250.56, 207.36), ('bump_fwd_lrst', 302.4, 207.36)):
    name = f'bump_{inst}_pad_i'
    t['pads'] = [q for q in t.get('pads', []) if q['name'] != name]
    t['pads'].append(dict(name=name, dir='in', width=1, layer='M7', sites_um=[[px, py]],
        note='Digital package control pad; direct wire into existing receiver capture logic, no analog receiver claim'))
p.write_text(json.dumps(x) + '\n')
