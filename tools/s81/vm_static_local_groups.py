#!/usr/bin/env python3
"""Generous static VM physical option: local 8-bank quarters, two fixed relay levels.
An explicit slot-change candidate, not a die-qualified plan. Existing cycles
remain unproved until real per-bit pins/phi-R views and uniform stage paths pass.
"""
import json,sys,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/ref_tile'))
spec=importlib.util.spec_from_file_location('rt',R/'tools/ref_tile/ref_tile.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
def rectgap(a,b):
 x,y=a['xy_um'];w,h=a['outline_um'];xx,yy=b['xy_um'];ww,hh=b['outline_um'];return max(0,x-xx-ww,xx-x-w)+max(0,y-yy-hh,yy-y-h)
def main():
 old=json.loads((R/'physical/s81_die_pins/v20_vm_static_standard/layout_candidate.json').read_text());by={n['name']:n for n in old['nodes']};nodes=[]
 for s in range(4):
  def add(name,x,y):
   n=dict(by[f'vm_s{s}_{name}']);
   if name.startswith('quarter'):n['outline_um']=[172.8,172.8]
   if name.startswith('bridge'):n['outline_um']=[345.6,345.6]
   n['xy_um']=[round(x,3),round(y+1555.2*s,3)];nodes.append(n)
  for b in range(32):
   q=b//8;k=b%8;add(f'bank{b}',(43.2 if q%2==0 else 1512)+259.2*(k//4),(43.2 if q<2 else 561.6)+129.6*(k%4))
  for q in range(4):add(f'quarter{q}',561.6 if q%2==0 else 1296,216 if q<2 else 777.6)
  add('bridge0',907.2,172.8);add('bridge1',907.2,1166.4)
  add('wscatter',864,691.2);add('read_frontend',864,820.8);add('return32',864,907.2)
 outline=[2073.6,6825.6]
 bl=[dict(name=n['name'],master=n['master'],idx=i,kind='child',x=n['xy_um'][0],y=n['xy_um'][1],w=n['outline_um'][0],h=n['outline_um'][1],offtrack=None) for i,n in enumerate(nodes)]
 checks=rt.floorplan_checks(dict(kind='cluster',pins={f:['pending'] for f in 'NSEW'}),*outline,bl,None);assert not checks,checks
 by={n['name']:n for n in nodes};edges=[]
 def edge(a,b):edges.append(dict(source=a,target=b,rect_lower_bound_um=round(rectgap(by[a],by[b]),3)))
 for s in range(4):
  for b in range(32):edge(f'vm_s{s}_bank{b}',f'vm_s{s}_quarter{b//8}')
  for q in range(4):edge(f'vm_s{s}_quarter{q}',f'vm_s{s}_bridge{q//2}')
  for h in range(2):
   for end in ['wscatter','read_frontend','return32']:edge(f'vm_s{s}_bridge{h}',f'vm_s{s}_{end}')
 assert not any(e['rect_lower_bound_um']>500 for e in edges)
 d=dict(schema='opentallas.s81.vm-local-native-groups.v1',status='SLOT_CHANGE_OPTION_NOT_ADOPTED',parent_outline_um=outline,old_outline_um=old['parent_outline_um'],core_slice_outline_um=[2073.6,1555.2],nodes=nodes,checks=checks,necessary_reach_edges=edges,necessary_reach_max_um=max(e['rect_lower_bound_um'] for e in edges),necessary_reach_over500=0,old_parent_mm2=old['parent_outline_um'][0]*old['parent_outline_um'][1]/1e6,new_parent_mm2=outline[0]*outline[1]/1e6,edge_service_reserved_band_xywh_um=[43.2,6220.8,1987.2,561.6],adoption_gates=['S-DIE slot-change placement with canonical2417/BF519/PHW10 full die','actual cap16/CDC/53write staging measured packing inside reserved band; no promise from area alone','all endpoint/per-bit pin assignment and worst-bit Manhattan<=500 or explicit fixed stage/calendar change','real phi-R TT/FF DRC0 views and native pin setup/launch hop budget','exact actual SRAM and full producer calendar after any added stages, immutable model pricing retained'],cost='larger local VM reservation only; no repricing or claimed cycles/gain; expose actual die area and any cycle cost after native stage assignment')
 out=R/'physical/s81_die_pins/v20_vm_static_local_groups';out.mkdir(exist_ok=True);(out/'layout_option.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps({k:d[k] for k in ['status','old_parent_mm2','new_parent_mm2','necessary_reach_max_um','necessary_reach_over500','checks']}))
if __name__=='__main__':main()
