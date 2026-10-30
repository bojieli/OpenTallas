#!/usr/bin/env python3
"""Private new LOAD lot estimate; existing hardware/RTL/plan are never modified."""
import sys,json,math
from pathlib import Path
import numpy as np
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S
raw=json.load(open(sys.argv[2]));facts=json.load(open(sys.argv[3]));G=8.64;W,H=302.4,151.2;HALO=5.4;MAX_D=float(sys.argv[5]) if len(sys.argv)>5 else 1600
out=[]
for part in ['NW_hub','NE_hub']:
 rows=[x for x in facts if x['partition']['name']==part];tn=rows[0]['partition']['type'];t=raw['partition_types'][tn];TW,TH=t['outline_um']
 nx,ny=int(math.ceil(TW/G)),int(math.ceil(TH/G));blocked=np.zeros((nx,ny),dtype=bool)
 def mark(a,b,c,d):
  i,j=max(0,int(math.floor(a/G))),max(0,int(math.floor(b/G)));ii,jj=min(nx,int(math.ceil(c/G))),min(ny,int(math.ceil(d/G)))
  blocked[i:ii,j:jj]=True
 for a,b,c,d in S.placed_macro_boxes(t,halo=HALO).values():mark(a,b,c,d)
 for s in t.get('internal_stations',[]):
  R=4.32+math.sqrt(max(1,s.get('bits',1))*.5832/2)
  for x,y in s.get('regs_um',[]):mark(x-R,y-R,x+R,y+R)
 for s in t.get('ft_slots',[]):
  if s.get('bit_sites_um'):
   for stage in s['bit_sites_um']:
    for x,y in stage:mark(x-2.16,y-2.16,x+1.404+2.16,y+.27+2.16)
  else:
   R=4.32+math.sqrt((s['width']+1)*.5832/2)
   for x,y in s.get('regs_um',[]):mark(x-R,y-R,x+R,y+R)
 for tap in t.get('clock',{}).get('taps',[]):
  xy=tap.get('xy') or tap.get('xy_um')
  if xy:mark(xy[0]-HALO,xy[1]-HALO,xy[0]+HALO,xy[1]+HALO)
 for r in rows:
  oc=r['hard_core'];rx,ry=oc['origin_um'];rw,rh=oc['outline_um'];target=(rx+rw/2,ry)
  sat=np.pad(blocked.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
  # Candidate origins are 8.64-um lattice points; padded rectangle includes all new halo.
  cw,ch=math.ceil((W+2*HALO)/G),math.ceil((H+2*HALO)/G)
  ix,iy=np.meshgrid(np.arange(1,nx-cw-1),np.arange(1,ny-ch-1),indexing='ij');ix,iy=ix.ravel(),iy.ravel()
  cost=np.abs(ix*G+HALO+W/2-target[0])+np.abs(iy*G+HALO-target[1]);near=cost<MAX_D
  ix,iy,cost=ix[near],iy[near],cost[near]
  hit=sat[ix+cw,iy+ch]-sat[ix,iy+ch]-sat[ix+cw,iy]+sat[ix,iy];valid=np.flatnonzero(hit==0)
  if not len(valid):
   out.append(dict(part=part,raw=r['native']['path'],verdict='NO_PRIVATE_LOT_IN_BOUNDED_SEARCH',max_search_um=MAX_D,outline_um=[W,H]));continue
  q=valid[np.argmin(cost[valid])];x,y=round(ix[q]*G+HALO,6),round(iy[q]*G+HALO,6)
  # Shift to the 2.16-um origin lattice without escaping the reserved padded cells.
  x=math.ceil(x/2.16)*2.16;y=math.ceil(y/2.16)*2.16
  d=abs(x+W/2-target[0])+abs(y-target[1]);pin_spread=abs(W-rw)/2
  o=dict(part=part,parent_type=tn,raw=r['native']['path'],new_inst='u_load_'+r['native']['path'],origin_um=[round(x,6),round(y,6)],outline_um=[W,H],raw_origin_um=[rx,ry],fill_face_midpoint_extension_um=d,fill_bus_extension_upper_um=d+pin_spread,min_added_405_segments=math.ceil((d+pin_spread)/405),verdict='ESTIMATE_SPACE_ONLY')
  out.append(o);mark(x-HALO,y-HALO,x+W+HALO,y+H+HALO);print(json.dumps(o),flush=True)
result=dict(scope=__doc__,base='d32q-derived hh_seams2, unadopted',stdcell_area_each_um2=11967.08904,SRAM_count_each=2,halo_um=HALO,grid_um=G,proposals=out,not_qualified=['actual parent clock/reset/START/PG','native actual alias and full pins','PHY service and branch dates','regional merge and all quadrant delivery/return routes','actual placement/G1/STA/GRT/route'])
Path(sys.argv[4]).write_text(json.dumps(result,indent=1)+'\n')
