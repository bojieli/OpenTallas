#!/usr/bin/env python3
"""Add the NLDM upstream cell-load consequence of PD13 proportional mesh drivers.
Keeps original wire RC and tree geometry. Delta is evaluated at a declared40ps input slew,
not timing sign-off; the all-corner wire/routed-slew follow-up is still required.
"""
import argparse,collections,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--rec',required=True);p.add_argument('--sites',required=True);p.add_argument('--corner',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools)
import die_clock_128 as C
L=C.lib_cells(a.corner,Path('~/.cache/opentallas/asap7_nldm').expanduser(),('BUFx24_ASAP7_75t_R',))['BUFx24_ASAP7_75t_R']
R=json.load(open(a.rec));S=json.load(open(a.sites));sites={r['site']:r for r in S['sites']};by={n['tag']:n for n in R['nodes']};added=collections.Counter();baseline=collections.Counter()
for n in R['nodes']:
 if n['driver']:
  r=sites[n['cell']];added[n['parent']]+=(r['new_cells']-r['base_cells'])*L['cap'];baseline[n['parent']]+=r['base_cells']*L['cap']
extra={k:C._bilin(L['delay'],40.0,baseline[k]+v)-C._bilin(L['delay'],40.0,baseline[k]) for k,v in added.items()}
shift={}
for n in sorted(R['nodes'],key=lambda n:len(n['tag'])):
 shift[n['tag']]=(shift.get(n['parent'],0) if n['parent'] else 0)+extra.get(n['tag'],0)
 n['arr'][a.corner]+=shift[n['tag']]
for b in R['band']:b['arr'][a.corner]+=shift.get(b['parent'],0)
R['note']=R.get('note','')+'; CODEX load-aware prediction: baseline-mult input load included on final tree parent, fixed40ps input slew, NOT routed evidence.'
Path(a.out).write_text(json.dumps(R)+'\n')
print(json.dumps(dict(corner=a.corner,changed_parent_nodes=sum(v>0 for v in extra.values()),max_added_load_fF=max(added.values()),max_added_parent_cell_delay_ps=max(extra.values()),max_driver_shift_ps=max(shift[n['tag']] for n in R['nodes'] if n['driver']),basis='NLDM40ps input slew; original wire RC not recomputed')))
