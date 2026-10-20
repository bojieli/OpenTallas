#!/usr/bin/env python3
"""CP-SAT feasibility probe for hard children and complete CB16 connectivity.
No route/gate output. A feasible result still requires actual corridor routing,
clock references, reset hardening, and schedule replay. No solver time limit.
"""
import argparse,json,math,time
from pathlib import Path
from ortools.sat.python import cp_model
from qc_safe_graph import ROOT,extract
S=1000;GRID=43200;GAP=20000

def main():
 p=argparse.ArgumentParser();p.add_argument('--step',type=float,required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--core',action='store_true');p.add_argument('--relax-unknown',action='store_true');p.add_argument('--grid-domains',action='store_true');p.add_argument('--anchor-bounds',action='store_true');p.add_argument('--placement-hint');p.add_argument('--hint-only',action='store_true');p.add_argument('--shelf-hint',action='store_true');p.add_argument('--greedy-hint',action='store_true');p.add_argument('--soft-reach',action='store_true',help='diagnostic legal packing minimizing sum of405um reach overruns');p.add_argument('--full-land',action='store_true');p.add_argument('--paired-land',action='store_true');p.add_argument('--zones',action='store_true');p.add_argument('--native-pins',help='compiled safe endpoint plan; exact local child pin offsets');p.add_argument('--forward-bank',action='store_true');p.add_argument('--forward-read-reach',type=float,default=250);a=p.parse_args();g=extract();assert not g['unresolved'];c=g['contract'];cols=[172.8+i*a.step for i in range(4)];W=math.ceil((cols[-1]+457.92+172.8)/43.2-1e-8)*43.2;H=c['outline_um']['h'];oldx=sorted(set(t['at'][0]for t in c['tiles']))
 knots=sorted([(0,0),(c['outline_um']['w'],W)]+[(x+d,y+d)for x,y in zip(oldx,cols)for d in [0,457.92]])
 def mx(x):
  for(oa,na),(ob,nb)in zip(knots,knots[1:]):
   if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
  raise ValueError(x)
 seed_placement={v['inst']:v['at']for v in json.loads(Path(a.placement_hint).read_text())['placement']}if a.placement_hint else {}
 m=cp_model.CpModel();xs=[];ys=[];jobs={};groups={};fixed={n:(round(mx(v['at'][0])*S),round(v['at'][1]*S))for n,v in g['ports'].items()}
 extras={};forward_groups={}
 if a.forward_bank:
  assert not a.full_land
  for e in g['edges']:
   if e['kind']!='bank':continue
   source=g['nodes'][e['src']];half=int(source['ports']['W'])//2;keys=[]
   for part in [0,1]:
    key=e['src']+f'_forward_p{part}';keys.append(key)
    extras[key]=dict(kind='qfd_c_bank_forward_safe',bits=4*half+47,region=source['region'],at=[(u+v)/2 for u,v in zip(e['src_at'],e['dst_at'])])
   forward_groups[e['src'],e['dst']]=keys
 for n,v in list(g['nodes'].items())+list(extras.items()):
  if v['bits']<=1:continue
  if v['kind'].startswith('qfd_c_land_'):
   keys=[n] if a.full_land else [n+'_p0',n+'_p1'];shape=(103.68,181.44) if a.full_land else (64.8,129.6)
  else:keys=[n];shape=(103.68,129.6)if'bank_forward'in v['kind']else(90.72,129.6)if'xstn'in v['kind']else(90.72,64.8)
  groups[n]=keys
  for k in keys:
   w,h=[round(t*S)for t in shape];ix=m.new_int_var(1,math.floor((W*S-GAP-w)/GRID),k+'_ix');iy=m.new_int_var(1,math.floor((H*S-GAP-h)/GRID),k+'_iy')
   x=m.new_int_var(GRID,round(W*S),k+'_x');y=m.new_int_var(GRID,round(H*S),k+'_y');m.add(x==ix*GRID);m.add(y==iy*GRID)
   xs.append(m.new_fixed_size_interval_var(x,w+GAP,k+'_xr'));ys.append(m.new_fixed_size_interval_var(y,h+GAP,k+'_yr'))
   jobs[k]=dict(logical=n,kind=v['kind'],region=v['region'],w=shape[0],h=shape[1],ix=ix,iy=iy,x=x,y=y,center=(x+w//2,y+h//2),target=[mx(v['at'][0]),v['at'][1]])
   if a.zones:
    # Redundant but stronger propagation: all empty tile-array space is the
    # union of five vertical corridors and five horizontal row gaps. This
    # preserves the unrestricted feasible set (unlike sibling pairing).
    rows=sorted(set(t['at'][1]for t in c['tiles']))
    strips=[('x',0,cols[0]-20)]+[('x',cols[i]+457.92+20,cols[i+1]-20)for i in range(3)]+[('x',cols[-1]+457.92+20,W)]
    strips += [('y',0,rows[0]-20)]+[('y',rows[i]+1166.4+20,rows[i+1]-20)for i in range(3)]+[('y',rows[-1]+1166.4+20,H)]
    choices=[]
    for zi,(axis,lo,hi)in enumerate(strips):
     size=shape[0]if axis=='x'else shape[1];lower=max(1,math.ceil((lo-1e-8)/43.2));upper=math.floor((hi-size+1e-8)/43.2)
     if lower>upper:continue
     on=m.new_bool_var(k+f'_zone{zi}');var=ix if axis=='x'else iy
     m.add(var>=lower).only_enforce_if(on);m.add(var<=upper).only_enforce_if(on);choices.append(on)
    m.add_bool_or(choices)
   if not(a.greedy_hint or a.shelf_hint):m.add_hint(ix,min(math.floor((W*S-GAP-w)/GRID),max(1,round(seed_placement[k][0]/43.2)if k in seed_placement else round((mx(v['at'][0])-shape[0]/2)/43.2))))
   if not(a.greedy_hint or a.shelf_hint):m.add_hint(iy,min(math.floor((H*S-GAP-h)/GRID),max(1,round(seed_placement[k][1]/43.2)if k in seed_placement else round((v['at'][1]-shape[1]/2)/43.2))))
 # Optional sibling pairing removes duplicate-split symmetry, while preserving
 # both horizontal and vertical legal channels. This is a restricted feasibility
 # search, never an impossibility claim for the unrestricted parent.
 if a.paired_land:
  assert not a.full_land
  for n,keys in groups.items():
   if len(keys)!=2:continue
   j0,j1=[jobs[k]for k in keys];horizontal=m.new_bool_var(n+'_horizontal')
   m.add(j1['ix']==j0['ix']+2).only_enforce_if(horizontal)
   m.add(j1['iy']==j0['iy']).only_enforce_if(horizontal)
   m.add(j1['ix']==j0['ix']).only_enforce_if(horizontal.Not())
   m.add(j1['iy']==j0['iy']+4).only_enforce_if(horizontal.Not())
 for t in c['tiles']:
  col=int(t['inst'][4]);tx=round(cols[col]*S);ty=round(t['at'][1]*S)
  xs.append(m.new_fixed_size_interval_var(tx,round(457.92*S)+GAP,t['inst']+'_xr'));ys.append(m.new_fixed_size_interval_var(ty,round(1166.4*S)+GAP,t['inst']+'_yr'))
 m.add_no_overlap_2d(xs,ys)
 if a.shelf_hint:
  assert abs(a.step-777.6)<1e-6 and not(a.full_land or a.forward_bank)
  inner=[math.ceil((cols[i]+457.92+20)/43.2-1e-8)for i in range(3)];outer=[1,math.ceil((cols[-1]+457.92+20)/43.2-1e-8)]
  catalog={(64.8,129.6):[(x+d,1+4*r)for x in inner for d in [0,2,4]for r in range(24)],(90.72,129.6):[(x,1+4*r)for x in outer for r in range(8)]}
  catalog[90.72,64.8]=[(x+d,97+2*r)for x in inner for d in [0,3]for r in range(12)]+[(x,33+2*r)for x in outer for r in range(44)]+[(round(x/43.2)+d,y)for x in cols for d in [0,3,6]for y in [math.ceil((row+1166.4+20)/43.2-1e-8)for row in sorted(set(t['at'][1]for t in c['tiles']))[:-1]]]
  placements=[]
  for k,j in sorted(jobs.items(),key=lambda item:(item[1]['region'],item[0])):
   shape=j['w'],j['h'];slots=catalog[shape];assert slots,(shape,k)
   ix,iy=min(slots,key=lambda pos:abs(pos[0]*43.2+shape[0]/2-j['target'][0])+abs(pos[1]*43.2+shape[1]/2-j['target'][1]));slots.remove((ix,iy))
   m.add_hint(j['ix'],ix);m.add_hint(j['iy'],iy);placements.append(dict(inst=k,at=[ix*43.2,iy*43.2],w=shape[0],h=shape[1]))
  hint=Path(a.out+'.hint.json');hint.parent.mkdir(parents=True,exist_ok=True);hint.write_text(json.dumps(dict(diagnostic_only=True,release_ready=False,scope='constructive shelf legal packing hint only; no reach/clock/reset qualification',outline_um=dict(w=W,h=H),placement=placements,jobs=len(jobs)),indent=1)+'\n')
  print('CP_SHELF_HINT',len(placements),'of',len(jobs),'placed',flush=True)
 if a.greedy_hint:
  occupied=set();placements=[];legal={}
  obstacles=[(cols[int(t['inst'][4])],t['at'][1],457.92,1166.4)for t in c['tiles']]
  def clash(rect,other):
   x,y,w,h=rect;u,v,bw,bh=other
   return not(x+w+20<=u+1e-7 or u+bw+20<=x+1e-7 or y+h+20<=v+1e-7 or v+bh+20<=y+1e-7)
  for k,j in sorted(jobs.items(),key=lambda item:(-item[1]['w']*item[1]['h'],item[1]['region'],item[0])):
   shape=j['w'],j['h'];w,h=shape;nw=math.ceil((w+20)/43.2-1e-8);nh=math.ceil((h+20)/43.2-1e-8)
   if shape not in legal:
    legal[shape]=[(ix,iy)for ix in range(1,math.floor((W-20-w)/43.2)+1)for iy in range(1,math.floor((H-20-h)/43.2)+1)if not any(clash((ix*43.2,iy*43.2,w,h),o)for o in obstacles)]
   candidates=sorted(legal[shape],key=lambda pos:abs(pos[0]*43.2+w/2-j['target'][0])+abs(pos[1]*43.2+h/2-j['target'][1]))
   for ix,iy in candidates:
    cells={(x,y)for x in range(ix,ix+nw)for y in range(iy,iy+nh)}
    if occupied&cells:continue
    occupied.update(cells);m.add_hint(j['ix'],ix);m.add_hint(j['iy'],iy);placements.append(dict(inst=k,at=[ix*43.2,iy*43.2],w=w,h=h));break
   else:print('CP_HINT_UNPLACED',k,flush=True)
  hint=Path(a.out+'.hint.json');hint.parent.mkdir(parents=True,exist_ok=True);hint.write_text(json.dumps(dict(diagnostic_only=True,release_ready=False,scope='legal packing hint only; no reach/clock/reset qualification',outline_um=dict(w=W,h=H),placement=placements,jobs=len(jobs)),indent=1)+'\n')
  print('CP_GREEDY_HINT',len(placements),'of',len(jobs),'placed',flush=True)
 if a.hint_only:
  assert a.greedy_hint or a.shelf_hint
  return
 def center(k):return jobs[k]['center']if k in jobs else fixed[k]
 ee=[];assume={};native_bounds={};native_bits=0;overruns=[];relaxed_contacts={};signs8=[(x,y)for x in[-1,0,1]for y in[-1,0,1]if x or y]
 if a.relax_unknown:assert a.native_pins,'relaxed endpoints require exact known-child pins'
 if a.native_pins:
  assert not a.full_land and not a.forward_bank,'native plan is narrow, unforwarded only'
  plan=json.loads(Path(a.native_pins).read_text());assets={}
  for master,asset in plan['native_pin_assets'].items():
   import hashlib
   raw=(ROOT/asset['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==asset['sha256']
   assets[master]=json.loads(raw)['pins']
  for bus in plan['bindings']:
   src,dst=bus['src'],bus['dst']
   if src.get('master')not in assets or dst.get('master')not in assets:
    if not a.relax_unknown:continue
    def endpoint_id(ep):return ep['inst']if ep.get('master')in assets else ep['port']+('_'+ep['inst'][4:]if ep['inst']!='BOUNDARY'else'')
    known=[ep for ep in[src,dst]if ep.get('master')in assets]
    if len(known)!=1:continue
    ep=known[0];unknown=dst if ep is src else src;uid=endpoint_id(unknown);pv=g['ports'][uid]
    if pv['kind']=='tile_port':
     tile=next(v for v in c['tiles']if v['inst']==pv['tile']);tx=cols[int(tile['inst'][4])];ty=tile['at'][1];bbox=[tx,ty,tx+457.92,ty+1166.4]
    else:bbox=[0,0,W,H]
    key=endpoint_id(src),endpoint_id(dst);contact=relaxed_contacts.setdefault(key,dict(known=ep['inst'],unknown=uid,bbox=[round(v*S)for v in bbox],bounds=[-10**12]*8))
    lo=ep.get('range',[0,bus['bits']-1])[0]
    for i in range(bus['bits']):
     pin=assets[ep['master']][ep['port']+f'[{lo+i}]'];assert len(pin['centers_um'])==1;x,y=[round(v*S)for v in pin['centers_um'][0]]
     for si,(sx,sy)in enumerate(signs8):contact['bounds'][si]=max(contact['bounds'][si],sx*x+sy*y)
    continue
   key=(src['inst'],dst['inst']);bounds=native_bounds.setdefault(key,[-10**12]*4)
   starts=[ep.get('range',[0,bus['bits']-1])[0]for ep in [src,dst]]
   for i in range(bus['bits']):
    pts=[]
    for ep,lo in zip([src,dst],starts):
     pin=assets[ep['master']][ep['port']+f'[{lo+i}]'];assert len(pin['centers_um'])==1
     pts.append(pin['centers_um'][0])
    ox,oy=[round((a-b)*S)for a,b in zip(*pts)]
    for si,(sx,sy)in enumerate([(1,1),(1,-1),(-1,1),(-1,-1)]):bounds[si]=max(bounds[si],sx*ox+sy*oy)
    native_bits+=1

 expanded=[]
 for e in g['edges']:
  ss=groups.get(e['src'],[e['src']]);dd=groups.get(e['dst'],[e['dst']]);pairs=zip(ss,dd)if len(ss)==len(dd)==2 else((s,d)for s in ss for d in dd)
  for part,(src,dst)in enumerate(pairs):
   if a.forward_bank and e['kind']=='bank':
    relay=forward_groups[e['src'],e['dst']][part]
    expanded.extend([(dict(e,kind='bank_forward_capture',base_capture_edges=1),src,relay,405),(dict(e,kind='bank_forward_read',base_capture_edges=1),relay,dst,a.forward_read_reach)])
   else:expanded.append((e,src,dst,405))
 for e,src,dst,reach in expanded:
   x0,y0=center(src);x1,y1=center(dst);i=len(ee);dx=m.new_int_var(0,round(W*S),f'ex{i}');dy=m.new_int_var(0,round(H*S),f'ey{i}');m.add_abs_equality(dx,x0-x1);m.add_abs_equality(dy,y0-y1)
   # Necessary geometric reach condition, including each bank. Corridor path is
   # checked after packing. No multicycle relaxation is used by this solver.
   bounds=native_bounds.get((src,dst));constraints=[]
   over=m.new_int_var(0,round((W+H)*S),f'over{i}')if a.soft_reach else 0
   if a.soft_reach:overruns.append(over)
   if bounds is not None:
    ox0,oy0=jobs[src]['x'],jobs[src]['y'];ox1,oy1=jobs[dst]['x'],jobs[dst]['y']
    for bound,(sx,sy)in zip(bounds,[(1,1),(1,-1),(-1,1),(-1,-1)]):constraints.append(m.add(sx*(ox0-ox1)+sy*(oy0-oy1)+bound<=round(reach*S)+over))
   elif a.relax_unknown:
    contact=relaxed_contacts.get((src,dst));assert contact,(src,dst,'missing relaxed native contact')
    j=jobs[contact['known']];lx,ly,rx,ry=contact['bbox']
    for bound,(sx,sy)in zip(contact['bounds'],signs8):
     support=sx*(rx if sx>=0 else lx)+sy*(ry if sy>=0 else ly)
     constraints.append(m.add(sx*j['x']+sy*j['y']+bound<=round(reach*S)+over+support))
   else:constraints.append(m.add(dx+dy<=round(reach*S)+over))
   if a.core:
    active=m.new_bool_var(f'edge{i}_reach')
    for constraint in constraints:constraint.only_enforce_if(active)
    m.add_assumption(active);assume[active.index]=i
   ee.append(dict(e,src=src,dst=dst,reach_target_um=reach,reach_basis='exact native child bit-pin Manhattan'if bounds is not None else'relaxed independent unknown endpoint anywhere in contract rectangle'if a.relax_unknown else'center diagnostic (A0/boundary pins unqualified)'))
 anchor_limits={};grid_domain_sizes={}
 anchor_receipt=dict(enabled=a.anchor_bounds,projection_bounds=0,contradictions=[],basis='unknown-rectangle support bounds, propagated only through exact native child edges'if a.relax_unknown else'fixed-center surrogate anchor bounds')
 if a.anchor_bounds:
  import heapq
  assert not(a.soft_reach or a.core),'anchor implications require all reach edges hard'
  signs=[(1,1),(1,-1),(-1,1),(-1,-1)];opposite=[3,2,1,0];arcs=[{}for _ in signs]
  def half(k):return (round(jobs[k]['w']*S/2),round(jobs[k]['h']*S/2))if k in jobs else(0,0)
  for e in ee:
   src,dst=e['src'],e['dst'];bs=native_bounds.get((src,dst))
   if bs is None:
    if a.relax_unknown:continue
    (u,v),(x,y)=half(src),half(dst);bs=[sx*(u-x)+sy*(v-y)for sx,sy in signs]
   for si in range(4):
    graph=arcs[si]
    for u,v,cost in [(dst,src,round(e['reach_target_um']*S)-bs[si]),(src,dst,round(e['reach_target_um']*S)-bs[opposite[si]])]:
     assert cost>=0,(u,v,cost)
     graph.setdefault(u,{})[v]=min(graph.get(u,{}).get(v,10**15),cost)
  for si,(sx,sy)in enumerate(signs):
   dist={k:sx*x+sy*y for k,(x,y)in fixed.items()}if not a.relax_unknown else {}
   if a.relax_unknown:
    for e in ee:
     contact=relaxed_contacts.get((e['src'],e['dst']))
     if contact is None:continue
     lx,ly,rx,ry=contact['bbox'];support=sx*(rx if sx>=0 else lx)+sy*(ry if sy>=0 else ly);bound=round(e['reach_target_um']*S)+support-contact['bounds'][signs8.index((sx,sy))]
     k=contact['known'];dist[k]=min(dist.get(k,10**18),bound)
   owner={k:k for k in dist};heap=[(value,k)for k,value in dist.items()];heapq.heapify(heap)
   while heap:
    value,u=heapq.heappop(heap)
    if value!=dist[u]:continue
    for v,cost in arcs[si].get(u,{}).items():
     if value+cost<dist.get(v,10**18):dist[v]=value+cost;owner[v]=owner[u];heapq.heappush(heap,(value+cost,v))
   anchor_limits[si]=dist
   for k,j in jobs.items():
    if k in dist:m.add(sx*j['x']+sy*j['y']<=dist[k]);anchor_receipt['projection_bounds']+=1
   for k,(x,y)in ([]if a.relax_unknown else fixed.items()):
    if dist[k]<sx*x+sy*y:anchor_receipt['contradictions'].append(dict(projection=[sx,sy],anchor=owner[k],endpoint=k,shortfall_um=(sx*x+sy*y-dist[k])/S))
  print('CP_ANCHOR_BOUNDS',anchor_receipt,flush=True)
 if a.grid_domains:
  assert a.anchor_bounds and not(a.soft_reach or a.core)
  obstacles=[(round(cols[int(t['inst'][4])]*S),round(t['at'][1]*S),round(457.92*S),round(1166.4*S))for t in c['tiles']]
  for k,j in jobs.items():
   w,h=round(j['w']*S),round(j['h']*S);allowed=[]
   for ix in range(1,math.floor((W*S-GAP-w)/GRID)+1):
    x=ix*GRID
    for iy in range(1,math.floor((H*S-GAP-h)/GRID)+1):
     y=iy*GRID
     if any(sx*x+sy*y>anchor_limits[si].get(k,10**18)for si,(sx,sy)in enumerate(signs)):continue
     if any(not(x+w+GAP<=u or u+bw+GAP<=x or y+h+GAP<=v or v+bh+GAP<=y)for u,v,bw,bh in obstacles):continue
     allowed.append((ix,iy))
   m.add_allowed_assignments([j['ix'],j['iy']],allowed);grid_domain_sizes[k]=len(allowed)
  sizes=sorted(grid_domain_sizes.values());print('CP_GRID_DOMAINS','min',min(sizes),'median',sizes[len(sizes)//2],'max',max(sizes),'empty',[k for k,v in grid_domain_sizes.items()if not v],flush=True)
 if a.soft_reach:
  assert not a.core,'soft-reach cannot produce a hard infeasibility core'
  m.minimize(sum(overruns))
 solver=cp_model.CpSolver();solver.parameters.num_search_workers=1 if a.core else a.workers;solver.parameters.log_search_progress=True
 print('CP_PLACE_START',a.step,'outline',W,H,'jobs',len(jobs),'edges',len(ee),'native_pairs',len(native_bounds),'native_bits',native_bits,flush=True)
 started=time.time()
 class PlacementWitness(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   if not a.soft_reach:return
   placed=[dict(inst=k,**{v:j[v]for v in ['logical','kind','region','w','h']},at=[self.value(j['x'])/S,self.value(j['y'])/S])for k,j in jobs.items()]
   violations=[dict(edge=e,overrun_um=self.value(overruns[i])/S)for i,e in enumerate(ee)if self.value(overruns[i])]
   receipt=dict(schema='opentallas.cb16.softreach_candidate.v1',diagnostic_only=True,release_ready=False,outline_um=dict(w=W,h=H),source=g['source'],native_pin_plan=a.native_pins,placement=placed,edges=ee,reach_violations=violations,total_overrun_um=self.objective_value/S,solver_wall_s=self.wall_time,scope='hard legal packing; reach is SOFT diagnostic, any positive overrun blocks parent adoption; missing A0/boundary pins and clocks/reset/routing remain unqualified')
   out=Path(a.out+'.best.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=1)+'\n')
   print('CP_SOFT_WITNESS','overrun_um',receipt['total_overrun_um'],'violations',len(violations),'wall',self.wall_time,flush=True)
 status=solver.solve(m,PlacementWitness());name=solver.status_name(status);print('CP_PLACE_STATUS',name,'wall',time.time()-started,flush=True)
 result=dict(schema='opentallas.cb16.cp_place.v1',diagnostic_only=True,source=g['source'],outline_um=dict(w=W,h=H),step_um=a.step,area_mm2=W*H/1e6,area_ratio=W/c['outline_um']['w'],status=name,solver_wall_s=time.time()-started,shape_policy='stations90.72x64.8; xstn90.72x129.6; '+('full103.68x181.44' if a.full_land else 'split64.8x129.6')+'; all pins<=6/um',clock_domain_rule='logical domain unchanged; physical regions may overlap; clock closure unqualified',reset_hardening_remaining=len(g['reset_nodes']),storage_waiver_required=a.full_land,paired_land_restriction=a.paired_land,empty_space_zones=a.zones,forward_bank_stage=a.forward_bank,extra_forward_children=len(extras),extra_forward_state_bits=sum(v["bits"]for v in extras.values()),extra_forward_outline_area_mm2=len(extras)*103.68*129.6/1e6,forward_read_reach_um=a.forward_read_reach,landing_child_profile='full103.68x181.44'if a.full_land else'split64.8x129.6',unknown_endpoint_rectangle_relaxation=a.relax_unknown,unknown_endpoint_scope='Each connection and bit may independently choose any point inside its unqualified A0 contract rectangle or die boundary rectangle; no shared pin/face/density proof'if a.relax_unknown else'Unknown A0/boundary endpoints use unqualified center surrogate',relaxed_contacts=len(relaxed_contacts),grid_domain_sizes=grid_domain_sizes,anchor_bounds=anchor_receipt,soft_reach=a.soft_reach,total_overrun_um=(solver.objective_value/S if a.soft_reach and status in [cp_model.OPTIMAL,cp_model.FEASIBLE] else None),placement_hint=a.placement_hint,native_pin_plan=a.native_pins,native_pin_bits_checked=native_bits,native_pin_pairs=len(native_bounds),release_ready=False)
 if status==cp_model.INFEASIBLE:
  result['infeasible_edge_core']=[ee[assume[i]] for i in solver.sufficient_assumptions_for_infeasibility() if i in assume]
  print('CP_PLACE_CORE',[(e['src'],e['dst'],e['net'])for e in result['infeasible_edge_core']],flush=True)
 if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
  placed=[]
  for k,j in jobs.items():placed.append(dict(inst=k,**{v:j[v]for v in ['logical','kind','region','w','h']},at=[solver.value(j['x'])/S,solver.value(j['y'])/S]))
  result.update(placement=placed,edges=ee)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
if __name__=='__main__':main()
