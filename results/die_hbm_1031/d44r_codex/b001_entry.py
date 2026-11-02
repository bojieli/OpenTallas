import json,sys
from pathlib import Path
import numpy as np
w=Path(__file__).resolve().parents[3];sys.path[:0]=[str(w),str(w/'tools/die_plan')]
import schema as S
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
import argparse
ap=argparse.ArgumentParser(description='Repair L730x2 input-facing banks without changing pins/depth');ap.add_argument('input');ap.add_argument('output');a=ap.parse_args();r=json.load(open(a.input));led=[]
for tn in ['q_b001','q_b001__physical_v1']:
 t=r['partition_types'][tn];s=next(s for s in t['ft_slots']if s['name']=='L730x2');assert s['stations']==3 and s['width']==1662,(tn,'source epoch changed');P=S.Plan(r);pins={(bn,i):(x,y)for bn,i,_,x,y,_ in type_pins(P,tn)};n=s['width']+1;A=np.array([pins[(s['name']+'_i',i)]for i in range(n)]);B=np.array([pins[(s['name']+'_o',i)]for i in range(n)]);W,H=t['outline_um'];cell=(1.404,.27)
 al=RowAllocator((4.32,4.32,W-4.32,H-4.32),blocked=list(S.placed_macro_boxes(t,halo=1.08).values()),cell_size=cell,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for ss in t['ft_slots']:
  if ss is s:continue
  for st in ss.get('bit_sites_um',[]):
   for x,y in st:al.reserve_rectangle((x,y,x+cell[0],y+cell[1]))
 targets=[np.column_stack((520.+.75*(A[:,0]-A[:,0].min()),np.full(n,4310.))),np.column_stack((np.full(n,730.),4140.+.4*(B[:,1]-B[:,1].min())))]
 sites=[]
 for T in targets:
  st=np.zeros((n,2))
  for i in np.argsort(T[:,0]+T[:,1],kind='stable'):
   pp,_=al.allocate(T[i],1,max_radius_um=60.);st[i]=pp[0]
  sites.append(st)
 hops=[float(np.abs(q-p).sum(axis=1).max())for p,q in zip([A]+sites,[*sites,B])];print(tn,hops,flush=True)
 assert max(hops)<=405,(tn,hops)
 s['bit_sites_um']=[(v-np.array(cell)/2).round(6).tolist()for v in sites];s['regs_um']=[A.mean(axis=0).round(4).tolist()]+[v.mean(axis=0).round(4).tolist()for v in sites];s['bit_site_cell_um']=list(cell)
 led.append(dict(type=tn,slot=s['name'],hops_um=hops,added_cycles=0,stations=3))
Path(a.output).write_text(json.dumps(r)+'\n');Path(a.output+'.ledger.json').write_text(json.dumps(led,indent=2)+'\n')
