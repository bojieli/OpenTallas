#!/usr/bin/env python3
"""Bind mapped reset plan to exact reset graph and emit per-landing release ledger.
Mapping still needs legalization/native clocks; no physical adoption implied.
"""
import argparse,json
from pathlib import Path
from qc_safe_graph import extract
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('--out',required=True);p.add_argument('--mut-offset',action='store_true');a=p.parse_args();d=json.loads(Path(a.plan).read_text());g=extract();nodes=g['reset_nodes'];edges=d['edges'];bydst={v['dst']:v for v in edges};assert set(bydst)==set(nodes);depth={k:0 for k in g['ports']if k.startswith('rst_c')}
for _ in range(len(nodes)):
 for n,e in bydst.items():
  if n not in depth and e['src']in depth:depth[n]=depth[e['src']]+2*e['hard_hops']
assert all(n in depth for n in nodes)
cons={v['inst']:v for v in d['consumers']};rows=[]
for idx,L in enumerate(g['contract']['landings']['list']):
 pair=[]
 for h in ['w','r']:
  v=cons[f'u_land_{L["name"]}_{h}'];base=depth[v['driver']];assert base==v['mapped_new_pin_depth'];padding=2*v['pad_hops'];target=base+padding
  if a.mut_offset and idx==0 and h=='r':target+=1
  pair.append(dict(half=h,driver=v['driver'],graph_pin_depth=base,padding_capture_edges=padding,release_pin_edge=target,local_face_stages=2,local_reset_state_release_edge=target+2,first_active_write_or_read_edge=target+3,split_hard_children=2,padding_counter_ff=(0 if padding==0 else 2 if padding==2 else 3+max(1,(padding-3).bit_length()))))
 G,R0=[v['local_reset_state_release_edge']for v in pair];rows.append(dict(landing=L['name'],halves=pair,G=G,R0=R0,K=2,effective_E=2+R0-G,equal_epoch=G==R0,compiler_old_face_stages=1,compiler_new_face_stages=2,normal_data_K_unchanged=True))
ok=all(v['equal_epoch']and v['effective_E']==2 for v in rows)
o=dict(schema='opentallas.cb16.safe_epoch_ledger.v1',diagnostic_only=True,source=g['source'],logical_reset_nodes=len(nodes),landing_pairs=len(rows),equal_epoch_pass=ok,rows=rows,hardware_price=dict(two_stage_forward_hops=d['mapped_forward_hops'],serial_padding_hops=d['equal_depth_padding_hops'],serial_added_reset_ff=d['added_reset_flops']),compiler_updates=dict(core_release_edge=d['A0_xstn_reset_pin_depth'],old_core_release_edge=d['old_A0_xstn_depth'],latest_landing_active_epoch=max(max(v['G'],v['R0'])for v in rows),normal_data_K=2),release_ready=False,blockers=['mapped reset route/lattice not physical legalization','native clock phase and reset transaction assertion/cancellation not proved','counter padding substitution needs full reset/epoch/MUT8 replay; this ledger uses explicit serial capture counts','all hardware relay and normal data alignment cost must enter final compiler before parent gate'])
Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print('SAFE_RESET_LEDGER',ok,len(rows),'pairs',len(nodes),'reset nodes')
if not ok:raise SystemExit(1)
