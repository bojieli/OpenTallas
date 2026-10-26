#!/usr/bin/env python3
"""S81-DIE72-G2: bind the four end parents to the MU72 assembly tops (update the existing master rows in place:
module, clocks, view note; ports / straps / landing data unchanged).  Usage: apply_mu72_overlay.py BIND_TABLE [--overlay FILE]
S81-LINK5 10-21: an overlay row may carry 'clone_from' (create a missing master row as a copy of an existing one, e.g.
dsdv_slice_lepw_mab from dsdv_slice_lepw_mu), 'ports_add' (extra plan ports merged into the row's ports: the pair-B
tx2/tx3/rx2/rx3 of the copy-A/B s_0N end) and 'link_slots' (informational: which die SerDes slot each lane port uses)."""
import copy, json, sys
from pathlib import Path
# S81-XDIE 10-24: --overlay FILE (name next to this script or a path) selects another overlay of the same schema, e.g.
# mu72_overlay_xdie.json (s_0S / s_7N copy-A/B ends for a plan with the reserve SerDes pair lk_WS2/3 + lk_EN2/3)
args = sys.argv[1:]
ov = 'mu72_overlay.json'
if '--overlay' in args:
    i = args.index('--overlay'); ov = args[i + 1]; del args[i:i + 2]
p = Path(args[0]); t = json.loads(p.read_text())
ovp = Path(ov) if Path(ov).is_file() else Path(__file__).with_name(ov)
o = json.loads(ovp.read_text())
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
