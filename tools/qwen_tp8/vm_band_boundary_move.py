#!/usr/bin/env python3
"""Exact L1 endpoint feasible regions for regional last-tile placement proposals.
Checks outgoing fixed band endpoints only. Region worker must add predecessor,
other successors, legal placement/channel, and routed corner constraints.
"""
import collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 sf=A/'vm_band_boundary_packet_codex.json';s=json.loads(sf.read_text());pf=ROOT/s['packet']['path']
 p=json.load(gzip.open(pf,'rt'));plan=json.loads((A/'vm_leaf_plan_claude.json').read_text());bays={b['n']:b for b in plan['x_relay_bays']}
 selected={(e['launch_stage']['bay'],e['launch_stage']['slot'])for e in p['boundary_edges']if e['must_move_launch_constraint']};groups=collections.defaultdict(list)
 for e in p['boundary_edges']:
  k=(e['launch_stage']['bay'],e['launch_stage']['slot'])
  if k in selected:groups[k].append(e)
 moves=[]
 for (bay,slot),es in sorted(groups.items()):
  origin=[bays[bay]['x']+21.6*slot,bays[bay]['y']];u0=sum(origin);v0=origin[0]-origin[1];corners={}
  for corner in ('tt','ss'):
   ulo,vlo=-math.inf,-math.inf;uhi,vhi=math.inf,math.inf
   for e in es:
    r=e['corner_budgets'][corner]['deep_entry_reach_at_TT_wire_coefficient_um']-.2
    px=e['launch_xy_um'][0]-origin[0];py=e['launch_xy_um'][1]-origin[1];bx,by=e['capture_xy_um']
    u=bx+by-px-py;v=bx-by-px+py
    ulo=max(ulo,u-r);uhi=min(uhi,u+r);vlo=max(vlo,v-r);vhi=min(vhi,v+r)
   feasible=ulo<=uhi and vlo<=vhi
   rec=dict(outgoing_fixed_band_endpoints_feasible=feasible,u_origin_interval_um=[ulo,uhi],v_origin_interval_um=[vlo,vhi])
   if feasible:
    u=min(max(u0,ulo),uhi);v=min(max(v0,vlo),vhi);x=(u+v)/2;y=(u-v)/2
    # Quantize to legal 2.16um lattice and search the nearby feasible choices.
    candidates=[]
    for ix in range(math.floor(x/2.16)-2,math.ceil(x/2.16)+3):
     for iy in range(math.floor(y/2.16)-2,math.ceil(y/2.16)+3):
      xx=ix*2.16;yy=iy*2.16
      if ulo<=xx+yy<=uhi and vlo<=xx-yy<=vhi:candidates.append((abs(xx-origin[0])+abs(yy-origin[1]),xx,yy))
    rec['continuous_minimum_L1_move_um']=max(abs(u-u0),abs(v-v0))
    rec['continuous_closest_origin_um']=[x,y]
    if candidates:
     d,x,y=min(candidates);rec['near_minimum_lattice_origin_um']=[round(x,4),round(y,4)];rec['lattice_L1_move_um']=round(d,4);rec['delta_um']=[round(x-origin[0],4),round(y-origin[1],4)]
   corners[corner]=rec
  moves.append(dict(bay=bay,slot=slot,region=bays[bay]['region'],original_origin_um=origin,outgoing_boundary_bits=len(es),launch_view=es[0]['corner_budgets']['tt']['launch']['view'],corner_constraints=corners,
   outgoing_lanes=sorted({e['lane']for e in es})))
 out=dict(schema='opentallas.qwen.vm-band-regional-lasttile-move-bound.v1',qualification=False,status='OUTGOING_CONSTRAINT_ONLY_NOT_PLACEMENT',
  packet_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),moves=moves,
  caveats=['No predecessor/internal region links or whole-geometry checked; proposed origins are not assigned placements.','TT all-bit min(500,pair reach) uses conservative deep entry210ps totalreserve and .2um margin. SS same .76 wire screening is diagnostic, not authorized corner signoff.','Independent-source bit index/phase order and all existing lane stages preserved by endpoint constraint only.'])
 (A/'vm_band_boundary_move_codex.json').write_text(json.dumps(out,indent=1)+'\n')
 for m in moves:print(m['bay'],m['slot'],m['outgoing_boundary_bits'],m['corner_constraints'])
if __name__=='__main__':main()
