#!/usr/bin/env python3
"""Paired L730 window move into the free south street, with unchanged eight-cycle depth."""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--lo',type=float,default=136.128);a=ap.parse_args()
r=json.loads(Path(a.input).read_text()); ledger=[]
for tn in ('q_su00','q_su00__physical_v1'):
 s=next(s for s in r['partition_types'][tn]['ft_slots'] if s['name']=='L730x1')
 assert s['width']==1662 and s['stations']==8,(tn,'source epoch changed')
 assert s['in_window_um']==[647.648,924.8147],(tn,'source window changed')
newwin=[a.lo,round(a.lo+277.1667,4)]
for tn in ('q_b113','q_b113__physical_v1'):
 b=next(b for b in r['partition_types'][tn]['buses'] if b['name']=='L730_o');old=b['window_um'];b['window_um']=newwin
 ledger.append(dict(type=tn,bus=b['name'],old=old,new=newwin))
for tn in ('q_su00','q_su00__physical_v1'):
 t=r['partition_types'][tn];slot=next(s for s in t['ft_slots'] if s['name']=='L730x1');old=slot['in_window_um'];slot['in_window_um']=newwin
 model=S.Plan(r);pins={(bn,i):(x,y)for bn,i,_,x,y,_ in type_pins(model,tn)}
 wd=int(slot['width'])+1;k=slot['stations'];A=np.array([pins[(slot['name']+'_i',i)]for i in range(wd)]);B=np.array([pins[(slot['name']+'_o',i)]for i in range(wd)])
 w,h=t['outline_um'];cell=(1.404,.27)
 alloc=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=list(S.placed_macro_boxes(t,halo=1.08).values()),cell_size=cell,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for ss in t['ft_slots']:
  if ss is slot:continue
  for st in ss.get('bit_sites_um',[]):
   for x,y in st:alloc.reserve_rectangle((x,y,x+cell[0],y+cell[1]))
 sites=[]
 for j in range(1,k):
  T=A+(B-A)*(j/k);st=np.zeros((wd,2))
  for bi in np.argsort(T[:,1],kind='stable'):
   pp,_=alloc.allocate(T[bi],1,max_radius_um=80);st[bi]=pp[0]
  sites.append(st)
 hops=[float(np.abs(q-p).sum(axis=1).max())for p,q in zip([A]+sites,[*sites,B])]
 assert max(hops)<=405,(tn,hops)
 slot['regs_um']=[A.mean(axis=0).round(4).tolist()]+[v.mean(axis=0).round(4).tolist()for v in sites]
 slot['bit_sites_um']=[(v-np.array(cell)/2).round(6).tolist()for v in sites];slot['bit_site_cell_um']=list(cell)
 slot['note']=slot.get('note','')+' | CODEX L730 paired south-street entry; bit-coherent direct interpolation; depth unchanged'
 ledger.append(dict(type=tn,slot=slot['name'],old=old,new=newwin,stations=k,width=slot['width'],added_cycles=0,hops_um=hops))
Path(a.output).write_text(json.dumps(r)+'\n');Path(a.output+'.ledger.json').write_text(json.dumps(ledger,indent=2)+'\n');print(json.dumps(ledger,indent=2))
