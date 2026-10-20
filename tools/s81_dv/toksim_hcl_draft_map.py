#!/usr/bin/env python3
"""TOKSIM-S81B/HCL (10-19): can the MTP DSpark draft blocks (D0/D1/D2) be composed from the release per-op records?

The draft nodes of ds_rom_mtp.json carry the same (cls, op) names as the main-layer nodes but OLD cycles from a different
decomposition (results/rtl/dsrom_recovery_20261004/draft: DP1-EP5 placement, stated, not bound on any S81 die).  No draft
node's old cycles equal a main-layer node's old cycles (toksim_s81_compose.node_cycles therefore leaves every draft node at
its committed number).  This tool lists, per draft node, the layer-equivalent (cls, op) whose release record would apply IF the
draft blocks were placed on p4l layer-class dies (same D 5120 / MoE / attention shapes as a main layer), and fills the cycles
of the ops HCL measured.  It is a placement mapping, not a measurement: nothing here is folded by the compose tool.

  python3 tools/s81_dv/toksim_hcl_draft_map.py <ds_rom.json> <ds_rom_mtp.json> <HCL.json> <out.json>
"""
import collections
import json
import re
import sys

ar, mtp, hcl, out = sys.argv[1:5]
A, M, H = json.load(open(ar)), json.load(open(mtp)), json.load(open(hcl))
gk = {g['id']: g['kind'] for g in M['groups']}
layer = collections.defaultdict(list)
for n in A['nodes']:
    layer[(n.get('cls'), n.get('op'))].append(float(n['cycles']))
rec = {(o.get('dag_cls'), o['op']): o for o in H['ops'] if o.get('cycles') is not None
       and o.get('grade', '').startswith('measured-release') and o.get('bit_exact')}
rows, tot = [], collections.Counter()
for n in M['nodes']:
    if gk.get(n.get('group')) != 'draft' or not n['id'].startswith('mtp.'):
        continue
    k = (n.get('cls'), n.get('op'))
    kl = (k[0], re.sub(r'\.r\d+$', '', k[1] or ''))
    lk = k if k in layer else (kl if kl in layer else None)
    old = float(n['cycles'])
    r = rec.get(k) or rec.get(kl)
    row = dict(node=n['id'], cls=k[0], op=k[1], critical=bool(n.get('critical')), old_draft_cycles=old,
               layer_equivalent=('%s/%s' % lk) if lk else None,
               layer_old_cycles=sorted(set(round(x, 1) for x in layer[lk]))[:6] if lk else [],
               old_matches_layer=any(abs(x - old) <= 0.6 for x in layer[lk]) if lk else False,
               release_cycles_if_layer_placed=(r['cycles'] if r else None),
               release_record=('HCL ' + r['op']) if r else ('other class' if lk else 'no layer node'))
    rows.append(row)
    if row['critical']:
        tot['critical_old'] += old
        tot['critical_with_layer_equivalent'] += old if lk else 0
        tot['critical_hcl_old'] += old if r else 0
        tot['critical_hcl_release'] += float(r['cycles']) if r else 0
json.dump(dict(schema='opentallas.toksim_s81b.hcl_draft_map.v1', dag=mtp,
               verdict='composable only as a placement mapping (draft blocks on p4l layer-class dies); no draft node old '
                       'cycles match a layer node, so compose keeps them; a run would execute the same release RTL at the '
                       'same layer shape (cycles static) and add only mtp.* weight bit-exactness: not launched',
               totals={k: round(v, 1) for k, v in tot.items()}, nodes=rows), open(out, 'w'), indent=1)
print(json.dumps({k: round(v, 1) for k, v in tot.items()}), len(rows), 'draft nodes')
