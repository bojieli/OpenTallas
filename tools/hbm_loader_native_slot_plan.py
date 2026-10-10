#!/usr/bin/env python3
"""Price proposed lease stations at actual recorded service PC pin coordinates.
No existing-unit occupancy or loaded clock budget is inferred from this plan.
"""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
gp=R/'physical/hbm_accel_die_views/svc/svc_geometry.json';sp=R/'physical/hbm_accel_die_views/svc/seg_stages.json'
g=json.loads(gp.read_text());sg=json.loads(sp.read_text());families={}
for family in ('SW','SE'):
 rec=g['hfd_svc_'+family];x=rec['pc_x'];slots=[]
 for pc,center in enumerate(x):
  seg=next(s for s in sg['families'][family]['segments'] if 'pc'+str(pc) in s['units'])
  # Keep the100um station inside its assigned real segment. This is a proposal,
  # not permission to overwrite existing cells, tracks or row reservations.
  left=min(max(center-50,seg['x0']),seg['x1']-100)
  box=[left,0,left+100,100]
  slots.append(dict(PC=pc,segment=seg['name'],box_um=box,actual_pin_center_um=[center,5],max_pin_to_station_center_um=((left+50-center)**2+45**2)**0.5,
   existing_occupancy_checked=False,loaded_clock_budget=None))
 overlaps=[]
 for i,s in enumerate(slots):
  for other in slots[i+1:]:
   if s['box_um'][0]<other['box_um'][2] and other['box_um'][0]<s['box_um'][2]:overlaps.append([s['PC'],other['PC']])
 families[family]=dict(proposed_slots=slots,proposed_lease_slot_overlap=overlaps,station_area_um2=32*10000,
   station_FF=32*316,station_DFF_area_proxy_um2=32*316*.2916,region_fit_proven=False)
receipt=dict(scope='actual PC-coordinate reservation proposal; occupancy and IO/clock closure still required',
 source_sha256={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [gp,sp,Path(__file__)]},
 replicas=dict(per_stack=32,stacks=4,total=128),families=families,
 native_req_reply_routing='Each PC station needs actual native request/return relay chains from the loader landing face, including finite ownership transport; the raw32way mux wrapper is functional evidence only',
 final_physical_qualified=False,adopted=False)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(receipt,indent=2)+'\n')
