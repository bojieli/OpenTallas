#!/usr/bin/env python3
"""Constructive placement of real SU arithmetic leaves; capacity/ABI not qualified.
Preserves individual master dimensions and R0 pins. No fake area-scaled parent.
"""
import argparse, json, math
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);a=p.parse_args();ip=Path(a.inventory);d=json.loads(ip.read_text());vs=d['historical_real_views']
 choices={v['cell'].removeprefix('dsfd_su_t_'):v for v in vs if v['cell'].startswith('dsfd_su_t_')}
 # Explicit variant choices are geometric samples, not qualification/adoption.
 chosen={'pin':'s81su_pinns_ref','swe':'s81su_swe_sp8_ref','qbe':'s81su_qbe_sp8_ref','qnq':'s81su_qnq_sp8_ref','sml':'s81su_sml_u65_ref','smd':'s81su_smd_u65_ref','smt':'s81su_smt_hb2_ref'}
 for short,kit in chosen.items():choices[short]=next(v for v in vs if '/'+kit+'/' in v['view'])
 leaves=[]
 for g,counts in d['hierarchical_arithmetic_counts'].items():
  for short,n in counts.items():
   for i in range(n):
    v=choices[short];leaves.append(dict(name=f'{g}/{short}{i}',group=g,master=v['cell'],view=v['view'],outline_um=v['outline_um'],clock=v['boundary_clocks'],insertion=v['insertion'],pin_manifest=v['view'].split('/')[2]+'__'+v['cell']+'_pins.json'))
 options=[]
 for width in [4104.0,5184.0,6048.0]:
  gap=43.2;x=gap;y=gap;rh=0;placed=[]
  # IO last = top nearest VM; stable functional groups preserve arithmetic adjacency.
  order=sorted(leaves,key=lambda n:({'sm':0,'sw':1,'kv':2,'qn':3,'qb':4,'io':5}[n['group']],-n['outline_um'][1],n['name']))
  for n in order:
   w,h=n['outline_um']
   if x+w+gap>width:x=gap;y+=rh+gap;rh=0
   placed.append(dict(n,origin_um=[round(x,3),round(y,3)],orientation='R0'));x+=w+gap;rh=max(rh,h)
  height=math.ceil((y+rh+gap)/2.16)*2.16
  assert len(placed)==711 and all(n['origin_um'][0]+n['outline_um'][0]<=width for n in placed)
  # Pairwise geometric proof, independent of shelf construction.
  collisions=[]
  for i,a in enumerate(placed):
   ax,ay=a['origin_um'];aw,ah=a['outline_um']
   for b in placed[:i]:
    bx,by=b['origin_um'];bw,bh=b['outline_um']
    if ax<bx+bw and ax+aw>bx and ay<by+bh and ay+ah>by:collisions.append([a['name'],b['name']])
  assert not collisions
  options.append(dict(name=f'SU real leaves W{width:g}',outline_um=[width,round(height,3)],leaf_count=len(placed),real_leaf_area_mm2=sum(n['outline_um'][0]*n['outline_um'][1] for n in placed)/1e6,parent_area_mm2=width*height/1e6,channel_um=gap,overlap_count=len(collisions),leaves=placed,qualification='GEOMETRY ONLY. RX, control/spine glue/relays and routed incident graph still missing; not a die shape grant.'))
 out=dict(source_commit=d['source_commit'],views=chosen,options=options,preferred_for_next_actual_graph='5184-wide balanced SU: compactness and VM-facing IO adjacency to screen, not adoption',constraints=['VM17137b seam must land on N-facing real pin-bank; current pin children span only1814.4um, complete request/mask controls need exact pin join.','43.2um streets are geometric spacing only; each exact per-bit cut must prove <=0.60 before realviews/fulltrial.','R0 child faces preserved. Moving leaf positions does not establish controller/relay-clock ABI or existing static schedule validity.','Arithmetic grouping retains native order logically; relay depths ERL3/ERS5/SRL2/SRD2/NRL4/NRC5 must be allocated from actual pins and recompiled if altered.','HC cannot inherit contract CTH790.56 against newer literal835.92; preserve measured source-specific child set before folding64 CTH groups.'])
 (ip.parent/'compact_su_leaf_options.json').write_text(json.dumps(out,indent=1)+'\n')
 print(json.dumps([{k:v for k,v in o.items() if k!='leaves'} for o in options]))
if __name__=='__main__':main()
