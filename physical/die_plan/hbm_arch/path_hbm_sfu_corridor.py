#!/usr/bin/env python3
"""Retain SFU masters and open actual M7-free S landing and EW strips."""
import argparse,json,shutil
from pathlib import Path
from path_hbm_bank_channels import update_core

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise SystemExit('output must be new')
 p=json.loads((a.src/'die_plan.json').read_text());r={'release_ready':False,'clock_pending':True,'masters_changed':False,'outline_delta_um':[0,0],'moves':{}}
 t=p['partition_types']['q_b112'];cs=t['hard_cores'];r['moves']['q_b112']=[]
 for i,c in enumerate(cs):r['moves']['q_b112'].append(update_core(t,c,[216.0+(i%2)*449.28,449.28+(i//2)*354.24]))
 t['die_ft_bands']=[{'dir':'EW','span_um':[8.64,440.64],'layers':['M4','M6'],'die_share':1.0},{'dir':'NS','span_um':[0,207.36],'layers':['M5','M7'],'die_share':1.0}]
 t=p['partition_types']['q_b113'];cs=t['hard_cores'];r['moves']['q_b113']=[]
 big=next(c for c in cs if c['inst'].endswith('opstore_b'));ctl=next(c for c in cs if c['inst'].endswith('_ctl'))
 r['moves']['q_b113'].append(update_core(t,big,[656.64,216.0]));r['moves']['q_b113'].append(update_core(t,ctl,[656.64,924.48]))
 for i,c in enumerate(c for c in cs if c is not big and c is not ctl):r['moves']['q_b113'].append(update_core(t,c,[1434.24,216.0+i*362.88]))
 t['die_ft_bands']=[{'dir':'EW','span_um':[8.64,207.36],'layers':['M4','M6'],'die_share':1.0},{'dir':'NS','span_um':[310.0,656.0],'layers':['M5','M7'],'die_share':1.0}]
 for tn in r['moves']:
  t=p['partition_types'][tn];w,h=t['outline_um']
  for c in t['hard_cores']:
   x,y=c['origin_um'];cw,ch=c['outline_um']
   if min(x,y)<8.64 or x+cw>w-8.64+1e-6 or y+ch>h-8.64+1e-6:raise ValueError(f'{tn}.{c["inst"]}: overflow')
  # The old stations are invalid after the move; selected repair must rebuild.
  t.pop('internal_stations',None)
 shutil.copytree(a.src,a.out);(a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'sfu_corridor_report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
