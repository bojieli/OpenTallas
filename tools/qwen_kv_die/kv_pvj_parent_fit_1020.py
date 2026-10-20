#!/usr/bin/env python3
"""Compare proposed PVJOIN pair envelopes with immutable actual GEN9 case.
Planning only: no source mutations, no physical/timing/age admission implied.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();b=Path(a.case);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lef=(b/'elements.lef').read_text();sizes={}
for z in re.finditer(r'(?m)^MACRO (\S+)\s*$(.*?)(?=^MACRO |\Z)',lef,re.S|re.M):
 m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',z[2]);
 if m:sizes[z[1]]=list(map(float,m.groups()))
insts={m[2]:m[1] for m in re.finditer(r'(?m)^\s*(\w+)\s+(\w+)\s*\(', (b/'die.v').read_text()) if m[1]!='module'}
placed={}
for z in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\w+)',(b/'place.tcl').read_text()):
 n,x,y,o=z.groups();master=insts.get(n);assert master in sizes,(n,master);w,h=sizes[master];placed[n]=dict(name=n,master=master,xy=[float(x),float(y)],wh=[w,h],orient=o)
assert all(n in placed for n in ['pvw_0','pvw_1','ahub','host'])
def rect(p):x,y=p['xy'];w,h=p['wh'];return x,y,x+w,y+h
def overlap(a,b):x0,y0,x1,y1=rect(a);u0,v0,u1,v1=rect(b);dx=min(x1,u1)-max(x0,u0);dy=min(y1,v1)-max(y0,v0);return round(dx,6),round(dy,6)
report={'scope':'MODEL_ONLY; actual case snapshot, no new views/pin maps; all hops/ages must be regenerated before adoption','inputs':{n:sha(b/n) for n in ['die.v','elements.lef','place.tcl','manifest.json']},'baseline':{n:placed[n] for n in ['pvw_0','pvw_1','ahub','host','seq','embgw','pvfin','kvs_ctl']},'die_um':json.load(open(b/'manifest.json'))['die_um'],'candidates':{}}
for tag,bw,bh,grow in [('fixed_faces',604.8,669.6,False),('redistribute_y_ns',604.8,604.8,False),('fixed_faces_grown',604.8,669.6,True),('redistribute_y_ns_grown',604.8,604.8,True)]:
 dw=2*(bw-561.6);dh=16*(bh-561.6);cand={n:dict(placed[n],xy=list(placed[n]['xy']),wh=list(placed[n]['wh'])) for n in ['pvw_0','pvw_1','ahub']}
 for n in ['pvw_0','pvw_1']:cand[n]['xy'][0]-=dw/2;cand[n]['wh']=[1555.2+dw,12009.6+dh]
 cand['ahub']['xy'][1]+=dh;cand['pvw_1']['xy'][1]+=dh
 context={n:dict(p,xy=list(p['xy']),wh=list(p['wh'])) for n,p in placed.items()}
 if grow:
  for n,p in context.items():
   if p['xy'][1]>=placed['embgw']['xy'][1]-1e-6:p['xy'][1]+=2*dh
  context['pvfin']['xy'][1]+=dh
  for n,p in context.items():
   if n.startswith(('pvfork_','pvtap_')):
    p['xy'][1]+=dh
    p['xy'][0]+=(-dw/2 if n.split('_')[1].startswith('W') else dw/2)
 context.update(cand)
 collisions={}
 for n,v in cand.items():
  hits=[]
  for nn,q in context.items():
   if nn==n:continue
   dx,dy=overlap(v,q)
   if dx>1e-4 and dy>1e-4:hits.append(dict(name=nn,master=q['master'],overlap_um=[dx,dy],xy=q['xy'],wh=q['wh']))
  collisions[n]=hits
 clear=context['host']['xy'][1]-(cand['pvw_1']['xy'][1]+cand['pvw_1']['wh'][1]);needed=max(0,-clear)
 functional_collisions={n:[h for h in hits if not h['master'].startswith(('qkd_rly','qkd_rst','qkd_fwd'))] for n,hits in collisions.items()}
 moved={n:q for n,q in context.items() if q!=placed[n]}
 all_new_hard=[];seen=set();outside=[]
 for n,v in moved.items():
  if v['master'].startswith(('qkd_rly','qkd_rst','qkd_fwd')):continue
  x0,y0,x1,y1=rect(v)
  if x0<0 or y0<0 or x1>report['die_um'][0]+1e-5 or y1>report['die_um'][1]+(2*dh if grow else 0)+1e-5:outside.append(n)
  for nn,q in context.items():
   if nn==n or q['master'].startswith(('qkd_rly','qkd_rst','qkd_fwd')):continue
   pair=tuple(sorted((n,nn)))
   if pair in seen:continue
   seen.add(pair);dx,dy=overlap(v,q);old_dx,old_dy=overlap(placed[n],placed[nn])
   if dx>1e-4 and dy>1e-4 and not(old_dx>1e-4 and old_dy>1e-4):all_new_hard.append(dict(pair=pair,overlap_um=[dx,dy]))
 (out/(tag+'_placement_delta.json')).write_text(json.dumps(moved,indent=1)+'\n')
 report['candidates'][tag]=dict(all_moved_new_functional_collisions=all_new_hard,outside_die_moved_functional=outside,grow_die_um=2*dh if grow else 0,die_area_delta_mm2=round(report['die_um'][0]*2*dh/1e6,6) if grow else 0,north_band_translation_um=2*dh if grow else 0,external_fork_tap_translation='candidate dy=pair dh, dx=outward dw/2; group-specific final route remains unqualified' if grow else None,functional_collisions=functional_collisions,functional_collision_count={n:len(v) for n,v in functional_collisions.items()},block_um=[bw,bh],pair_frame_um=[1555.2+dw,12009.6+dh],vertical_shift_um=round(dh,4),pair_and_ahub=cand,north_host_clearance_um=round(clear,6),minimum_die_growth_to_host_um=round(needed,6),collisions=collisions,collision_count={n:len(v) for n,v in collisions.items()},pair_area_delta_mm2=round(2*((1555.2+dw)*(12009.6+dh)-1555.2*12009.6)/1e6,6),static_age_delta='UNQUALIFIED: leaf zero-edge change does not establish parent zero-edge fit; regenerate relay routes and recompile calendars',wire_reach='UNQUALIFIED: all changed parent/pin/station paths require actual per-bit <=405um audit after replan')
(out/'parent_fit.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:{x:v[x] for x in ['pair_frame_um','vertical_shift_um','north_host_clearance_um','collision_count','pair_area_delta_mm2']} for k,v in report['candidates'].items()},indent=1))
