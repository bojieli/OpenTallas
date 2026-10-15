#!/usr/bin/env python3
"""Candidate parent pins preserve global W/E coordinates under north-anchored growth.
Scalar inherited clock ports are NOT an implemented native child-clock ABI.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
for cell,delta in [('dsfd_sp_hc_c',388.8),('dsfd_sp_hc_t',466.56)]:
 path=f'physical/s81_die_pins/v19_merged/generated/{cell}.json'
 raw=subprocess.check_output(['git','show','HEAD:'+path]);x=json.loads(raw)
 x['outline_um'][1]=round(x['outline_um'][1]+delta,3);x['case']='norm_capture_margin_UNADOPTED';x['qualification']='UNADOPTED geometry only; station topology, internal native-clock ABI, source/pin/PG/cut/hop and TTFFDRC remain open';x['source']='tools/s81_norm_physical/margin_parent_pins.py';x['candidate_growth_down_um']=delta;x['base_pin_sha256']=hashlib.sha256(raw).hexdigest()
 for port,plan in x['ports'].items():
  if plan.get('uniform') and plan['face'] in ('W','E'):plan['at'][0]=round(plan['at'][0]+delta,3)
  for bit in plan.get('per_bit',[]):
   if bit[0] in ('W','E'):bit[2]=round(bit[2]+delta,3)
  if 'meets' in plan:plan['prior_meets_UNVERIFIED']=plan.pop('meets')
 (a.out/(cell+'.json')).write_text(json.dumps(x,indent=1)+'\n')
 print(cell,x['outline_um'],delta)
