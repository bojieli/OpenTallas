#!/usr/bin/env python3
"""Private unchanged-count HH per-bit allocation diagnostic, never route authority."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
sys.path.insert(0,sys.argv[1]+'/tools/die_trial')
import schema as S
from gen_phys import type_pins
from legal_sites import RowAllocator
raw=json.loads(Path(sys.argv[2]).read_text()); P=S.Plan(raw)
report=[];cell=(1.404,.27)
for tn,t in raw['partition_types'].items():
 slots=[s for s in t.get('ft_slots',[]) if s['name'].startswith(('L700','L701'))]
 if not slots:continue
 W,H=t['outline_um']; boxes=list(S.placed_macro_boxes(t,halo=4.32).values())
 al=RowAllocator((4.32,4.32,W-4.32,H-4.32),blocked=boxes,cell_size=cell,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for old in t['ft_slots']:
  for st in old.get('bit_sites_um',[]):
   for x,y in st:al.reserve_rectangle((x,y,x+cell[0],y+cell[1]))
 pins={}
 for name,bit,layer,x,y,face in type_pins(P,tn):pins.setdefault(name,{})[bit]=(x,y,face)
 for s in slots:
  pi,po=pins[s['name']+'_i'],pins[s['name']+'_o']; bits=sorted(set(pi)|set(po)); k=s['stations']
  ac=np.mean([pi[b][:2] for b in bits],axis=0);bc=np.mean([po[b][:2] for b in bits],axis=0)
  sites=[[] for _ in range(k-1)]; bad=[]; worst=0; failures=[];disp=0
  for b in bits:
   a=np.array(pi[b][:2]);z=np.array(po[b][:2]);f=pi[b][2];a+=dict(E=(-1,0),W=(1,0),N=(0,-1),S=(0,1))[f]
   targets=[]
   for j in range(1,k):
    frac=j/(k-1);targets.append(np.array(s['regs_um'][j])+(1-frac)*(a-ac)+frac*(z-bc))
   if len(sys.argv)>5 and sys.argv[5] in ('resample','corridor'):
    path=[a]+targets+[z];lens=[float(np.abs(v-u).sum()) for u,v in zip(path,path[1:])];total=sum(lens)
    if sys.argv[5]=='corridor' and tn=='q_b112__physical_v1':
     if s['in_face']=='S':path=[a,np.array([z[0]-12.96,8.64]),np.array([z[0]-12.96,z[1]]),z]
     else:path=[a,np.array([a[0]-12.96,a[1]]),np.array([a[0]-12.96,8.64]),np.array([z[0],8.64]),z]
     lens=[float(np.abs(v-u).sum()) for u,v in zip(path,path[1:])];total=sum(lens)
    targets=[]
    for j in range(1,k):
     at=total*j/k
     for ix,L in enumerate(lens):
      if at<=L+1e-8:
       targets.append(path[ix]+(path[ix+1]-path[ix])*(at/L if L else 0));break
      at-=L
   chain=[a]
   for j in range(1,k):
    want=targets[j-1]
    try:
     target=al.project(want);q,stats=al.allocate(target,1,max_radius_um=32);q=q[0];disp=max(disp,float(np.abs(q-want).sum()))
    except ValueError as e:
     failures.append(dict(bit=b,stage=j,error=str(e)));q=want
    sites[j-1].append([round(float(q[0]-cell[0]/2),6),round(float(q[1]-cell[1]/2),6)]);chain.append(q)
   chain.append(z);hops=[float(np.abs(v-u).sum()) for u,v in zip(chain,chain[1:])];worst=max(worst,max(hops))
   if max(hops)>364.5:bad.append(dict(bit=b,max_hop_um=max(hops),stage=int(np.argmax(hops))))
  s['bit_site_cell_um']=list(cell);s['bit_sites_um']=sites
  r=dict(type=tn,slot=s['name'],payload_bits=s['width'],bits_including_epoch=len(bits),stations=k,worst_um=worst,bad_hops=len(bad),bad_sample=bad[:12],allocation_failures=len(failures),failure_sample=failures[:4],max_target_displacement_um=disp)
  report.append(r);print(json.dumps(r),flush=True)
Path(sys.argv[3]).write_text(json.dumps(raw,separators=(',',':'))+'\n')
Path(sys.argv[4]).write_text(json.dumps(dict(scope=__doc__,counts_changed=False,existing_unallocated_slots_not_qualified=True,slots=report),indent=1)+'\n')
