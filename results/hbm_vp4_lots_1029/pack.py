#!/usr/bin/env python3
"""Nearest-grid lower-left VP4 lot search against actual plan footprint/site rectangles; estimate only."""
import json,sys,math,hashlib,collections
from pathlib import Path
import numpy as np
W,H=501.12,311.04;GRID=8.64;HALO=8.64;EPS=1e-5
P=Path(sys.argv[1]);OUT=Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)
d=json.load(open(P/'die_plan.json'));results=[]
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>EPS and min(a[3],b[3])-max(a[1],b[1])>EPS
def rect(o,s):return [o[0],o[1],o[0]+s[0],o[1]+s[1]]
def expand(r,h):return[r[0]-h,r[1]-h,r[2]+h,r[3]+h]
def near(p,r,tol=2):return r[0]-tol<=p[0]<=r[2]+tol and r[1]-tol<=p[1]<=r[3]+tol
for tn in ['q_hub_nw','q_hub_ne']:
 t=d['partition_types'][tn];TW,TH=t['outline_um'];hard={c['inst']:c for c in t.get('hard_cores',[])}
 for c in [c for c in hard.values()if c['module']=='ot_hgi_dma_back_static_vp4_banks_cp']:
  obs=[];counts=collections.Counter();old=rect(c['origin_um'],c['outline_um']);off=c.get('track_offset_um',[0,0]);oldactual=[old[0]+off[0],old[1]+off[1],old[2]+off[0],old[3]+off[1]]
  def add(n,r,kind):obs.append((n,r,kind));counts[kind]+=1
  for n,hc in hard.items():
   if n==c['inst']:continue
   oo=hc.get('track_offset_um',[0,0]);o=[hc['origin_um'][0]+oo[0],hc['origin_um'][1]+oo[1]];add(n,rect(o,hc['outline_um']),'hard_core')
  for so in t.get('contents',[]):
   if so['inst']in hard or 'origin_um'not in so or 'outline_um'not in so:continue
   add(so['inst'],rect(so['origin_um'],so['outline_um']),'soft_lot')
  for fs in t.get('ft_slots',[]):
   cell=fs.get('bit_site_cell_um',[1.404,.27])
   for j,stage in enumerate(fs.get('bit_sites_um',[])):
    for b,p in enumerate(stage):add(f"ft:{fs['name']}:{j}:{b}",rect(p,cell),'actual_ft_bit_cell')
   for j,p in enumerate(fs.get('regs_um',[])):add(f"ft_reg:{fs['name']}:{j}",rect(p,cell),'ft_station')
  for si,s in enumerate(t.get('internal_stations',[])):
   for j,p in enumerate(s.get('regs_um',[])):add(f"is:{si}:{j}",rect(p,[1.404,.27]),'internal_station_site')
  for i,b in enumerate(t.get('clock',{}).get('branch_buffers',[])):
   p=b.get('xy')or b.get('xy_um')or b.get('origin_um')
   if p:add(f'clockbuf:{i}',[p[0]-4.32,p[1]-4.32,p[0]+4.32,p[1]+4.32],'clock_buffer')
  # Exact forbidden lower-left intervals. Grid-origin outward bounds conservatively include HALO.
  nx=int(math.floor((TW-W)/GRID+EPS))+1;ny=int(math.floor((TH-H)/GRID+EPS))+1;diff=np.zeros((ny+1,nx+1),np.int32);solid=np.zeros_like(diff)
  for n,r,k in obs:
   loX=r[0]-HALO-W;hiX=r[2]+HALO;loY=r[1]-HALO-H;hiY=r[3]+HALO
   x0=max(0,math.floor((loX+EPS)/GRID)+1);x1=min(nx-1,math.ceil((hiX-EPS)/GRID)-1)
   y0=max(0,math.floor((loY+EPS)/GRID)+1);y1=min(ny-1,math.ceil((hiY-EPS)/GRID)-1)
   if x0<=x1 and y0<=y1:
    diff[y0,x0]+=1;diff[y1+1,x0]-=1;diff[y0,x1+1]-=1;diff[y1+1,x1+1]+=1
    if k in ('hard_core','soft_lot','clock_buffer'):
     solid[y0,x0]+=1;solid[y1+1,x0]-=1;solid[y0,x1+1]-=1;solid[y1+1,x1+1]+=1
  occ=diff.cumsum(0).cumsum(1)[:ny,:nx];solid=solid.cumsum(0).cumsum(1)[:ny,:nx];fully_legal=int(np.count_nonzero(occ==0));yy,xx=np.where(solid==0)
  target=[(old[0]+old[2]-W)/2,(old[1]+old[3]-H)/2];dist=np.abs(xx*GRID-target[0])+np.abs(yy*GRID-target[1]);order=list(dict.fromkeys(list(np.argsort(dist,kind='stable')[:32])+list(np.lexsort((dist,occ[yy,xx]))[:32])));cands=[]
  for ix in order:
   x,y=round(float(xx[ix]*GRID),3),round(float(yy[ix]*GRID),3);nr=[x,y,x+W,y+H]
   hits=[(n,k) for n,r,k in obs if overlap(nr,expand(r,HALO))]
   assert not [n for n,k in hits if k in ('hard_core','soft_lot','clock_buffer')]
   # Re-evaluate all OLD physical endpoint legs attributed by actual endpoints near this lot.
   ends=[]
   for si,s in enumerate(t.get('internal_stations',[])):
    for side in ['from','to']:
     p=s.get(side+'_um');ns=s.get('regs_um',[])
     if not p or not ns or 'dbk'not in str(s.get('conn','')) or not near(p,oldactual,2):continue
     # Keep source pin's face and normalized within-face position. This is a geometric estimate, not regenerated pins.
     u=max(0,min(1,(p[0]-oldactual[0])/max(oldactual[2]-oldactual[0],1e-9)));v=max(0,min(1,(p[1]-oldactual[1])/max(oldactual[3]-oldactual[1],1e-9)))
     q=[x+u*W,y+v*H];adj=ns[0]if side=='from'else ns[-1];length=abs(q[0]-adj[0])+abs(q[1]-adj[1]);base=abs(p[0]-adj[0])+abs(p[1]-adj[1])
     ends.append(dict(station_index=si,conn=s.get('conn'),side=side,old_endpoint_um=p,new_endpoint_estimate_um=q,adjacent_station_um=adj,old_leg_um=base,new_manhattan_lower_bound_um=length,additional_hops_min=max(0,math.ceil((length-EPS)/405)-1)))
   cands.append(dict(origin_um=[x,y],outline_um=[W,H],centre_displacement_l1_um=round(float(dist[ix]),3),origin_displacement_um=[x-old[0],y-old[1]],physical_clear=not hits,overlap_count=len(hits),station_sites_to_resite=[n for n,k in hits],endpoint_legs=ends,new_leg_max_lower_bound_um=round(max([e['new_manhattan_lower_bound_um']for e in ends]or[0]),3),endpoint_legs_over405=sum(e['new_manhattan_lower_bound_um']>405+EPS for e in ends),additional_hops_min_total=sum(e['additional_hops_min']for e in ends)))
  gy,gx=np.indices(solid.shape);near_dist=np.abs(gx*GRID-target[0])+np.abs(gy*GRID-target[1]);mask=near_dist<=405+EPS;nyy,nxx=np.where(mask);norder=np.lexsort((near_dist[nyy,nxx],occ[nyy,nxx],solid[nyy,nxx]))[:12];nearby=[]
  for k in norder:
   x,y=round(float(nxx[k]*GRID),3),round(float(nyy[k]*GRID),3);rr=[x,y,x+W,y+H];hit=[dict(name=n,kind=kind,rect_um=r)for n,r,kind in obs if overlap(rr,expand(r,HALO)) and kind in ('hard_core','soft_lot','clock_buffer')]
   nearby.append(dict(origin_um=[x,y],centre_displacement_l1_um=round(float(near_dist[nyy[k],nxx[k]]),3),solid_colliders=hit,station_site_collisions=int(occ[nyy[k],nxx[k]]-solid[nyy[k],nxx[k]])))
  results.append(dict(type=tn,inst=c['inst'],old_origin_um=c['origin_um'],old_outline_um=c['outline_um'],orient=c.get('orient','R0'),track_offset_um=off,obstacle_counts=dict(counts),legal_grid_positions=fully_legal,solid_clear_grid_positions=len(xx),minimum_station_site_collisions=int(min(occ[yy,xx])) if len(xx) else None,nearby_partial_pack_candidates=nearby,candidates=cands))
# Corridor endpoint estimates for nearby joint-pack alternatives (same-face normalized pin positions).
for r in results:
 ox,oy=r['old_origin_um'];ow,oh=r['old_outline_um'];dx,dy=r['track_offset_um'];base=r['candidates'][0]['endpoint_legs'] if r['candidates'] else []
 for a in r['nearby_partial_pack_candidates']:
  x,y=a['origin_um'];legs=[]
  for e in base:
   p=e['old_endpoint_um'];q=[x+max(0,min(1,(p[0]-ox-dx)/ow))*W,y+max(0,min(1,(p[1]-oy-dy)/oh))*H];z=e['adjacent_station_um'];L=abs(q[0]-z[0])+abs(q[1]-z[1]);legs.append(dict(station_index=e['station_index'],conn=e['conn'],side=e['side'],new_endpoint_estimate_um=q,adjacent_station_um=z,new_leg_lower_bound_um=L,additional_hops_min=max(0,math.ceil((L-EPS)/405)-1)))
  a['endpoint_legs']=legs;a['endpoint_legs_over405']=sum(e['new_leg_lower_bound_um']>405+EPS for e in legs);a['new_leg_max_lower_bound_um']=max([e['new_leg_lower_bound_um']for e in legs]or[0]);a['additional_hops_min_total']=sum(e['additional_hops_min']for e in legs)
report=dict(source_plan_sha256=hashlib.sha256((P/'die_plan.json').read_bytes()).hexdigest(),source_plan=str(P/'die_plan.json'),qualification='ESTIMATE ONLY; no plan mutation/P&R',grid_um=GRID,obstacle_halo_um=HALO,station_footprint_um=[1.404,.27],station_bit_qualification='Hub types have zero ft_slots, so no explicit FT bit cells are published there. Actual internal regs_um site cells included; bus-bit spreading beyond published sites is NOT available and remains a physical-site obligation.',endpoint_qualification='Normalized same-face endpoint geometry only; exact revised pin table, clock island map, corridor path and new stations are not generated. Manhattan is a lower bound, never a routed length.',results=results)
(OUT/'vp4_lot_candidates.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(r['type'],r['inst'],'legal',r['legal_grid_positions'],'nearest',r['candidates'][0]['origin_um']if r['candidates']else'NONE','disp',r['candidates'][0]['centre_displacement_l1_um']if r['candidates']else'', 'ends>405',r['candidates'][0]['endpoint_legs_over405']if r['candidates']else'', 'minimum_site_hits',r['minimum_station_site_collisions'])
