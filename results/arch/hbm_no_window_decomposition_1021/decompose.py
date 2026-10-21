#!/usr/bin/env python3
"""Read emitted N/O data only; no planner/probe execution."""
import json,math,collections,hashlib
from pathlib import Path
import numpy as np
BASE=Path('/home/ubuntu/artifacts/hdie-d4');G=10.; X,Y=10450.,30800.;SIZE=550.
xx,yy=np.meshgrid(np.arange(X,X+SIZE,G),np.arange(Y,Y+SIZE,G),indexing='ij')
paths={'N':BASE/'codex_hbm_r16n_sidexq_1021/plannM','O':BASE/'codex_hbm_r16o_corridor_1021/planoM'}
def boxes(m):
 for n,v in m['placement'].items():
  if v.get('m','').startswith('hbfd_rly') or n.startswith('rly'):continue
  w,h=v['w'],v['h']
  if v.get('o','R0') in ('R90','R270','MXR90','MYR90'):w,h=h,w
  yield n,v,(v['x'],v['y'],v['x']+w,v['y']+h)
def mask(b,carve=False):
 x0,y0,x1,y1=b
 if carve:return (xx>=math.ceil(x0/G)*G)&(xx<math.floor(x1/G)*G)&(yy>=math.ceil(y0/G)*G)&(yy<math.floor(y1/G)*G)
 return (xx>=math.floor(x0/G)*G)&(xx<math.ceil(x1/G)*G)&(yy>=math.floor(y0/G)*G)&(yy<math.ceil(y1/G)*G)
def geom(m,roots):
 occ=np.zeros(xx.shape,bool);owners={};car=np.zeros(xx.shape,bool);near=[]
 for n,v,b in boxes(m):
  q=mask(b);occ|=q
  if q.any():owners[n]=q;near.append(dict(instance=n,placement=v,grid_blocked_cells=int(q.sum())))
  for c in m.get('carved_feedthrough',{}).get(v['m'],[]):
   a,z=c['x_um'];b0,z0=c['y_um'];o=v.get('o','R0')
   if o in ('MY','R180'):a,z=v['w']-z,v['w']-a
   if o in ('MX','R180'):b0,z0=v['h']-z0,v['h']-b0
   car|=mask((v['x']+a,v['y']+b0,v['x']+z,v['y']+z0),True)
 free=(~occ)|car
 for s in roots['sites']:free&=~mask(s['keepout'])
 return free,owners,near

def fp(bits,tiles):
 w=48 if bits<=48 else 624;side=min(max(10.8,(2*w+8)/24),max(21.6,(2*w+8)*.048*1.5/.9/4));return (tiles or math.ceil(bits/w))*side**2*1.2
out={'scope':'existing emitted N/O only, window [10450,30800] 550x550; G10/util0.5','runs':{}}
F={};OWN={};ST={}
for k,p in paths.items():
 m=json.load(open(p/'case_a_manifest.json'));r=json.load(open(p/'lanes_report.json'));st=json.load(open(p/'stations_lanes.json'));roots=json.load(open(p/'root_sites.json'));F[k],OWN[k],near=geom(m,roots)
 row=next(t for t in r['capacity']['windows']['worst'] if t[1]==[10450,30800]);cap=int(F[k].sum()*G*G*.5);assert cap==row[3],(k,cap,row)
 totals=collections.defaultdict(float);member={}
 for a in st['rows']:
  val=0;ns=0
  for s in a['stations']:
   if X<=s['x']<X+SIZE and Y<=s['y']<Y+SIZE:val+=fp(a['bits'],s.get('tiles'));ns+=1
  pads=[]
  for q in a.get('pads',[]):
   if X<=q['x']<X+SIZE and Y<=q['y']<Y+SIZE:val+=fp(a['bits'],a['stations'][0].get('tiles') if a['stations'] else None)*q['stages'];pads.append(q)
  if val:totals[a['driver']]+=val;member[a['driver']]=dict(driver=a['driver'],sinks=a['sinks'],bits=a['bits'],pins=a.get('pins'),stations_in_window=ns,pads_in_window=pads,nominal_site_footprint=round(val,3))
 ST[k]=totals
 out['runs'][k]=dict(report_window=row,exact_free_grid_cells=int(F[k].sum()),exact_capacity=cap,intersecting_actual_bodies=near,nominal_site_footprint_total=round(sum(totals.values()),3),nominal_site_contributors=sorted(member.values(),key=lambda x:-x['nominal_site_footprint'])[:20],input_sha256={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['case_a_manifest.json','lanes_report.json','stations_lanes.json','root_sites.json']})
lost=F['N']&~F['O'];gained=F['O']&~F['N'];out['grid_delta']=dict(lost_free_cells=int(lost.sum()),gained_free_cells=int(gained.sum()),lost_capacity=int(lost.sum()*50),gained_capacity=int(gained.sum()*50),O_blocker_attribution=[dict(instance=n,lost_cells=int((lost&q).sum())) for n,q in OWN['O'].items() if (lost&q).any()],N_removed_blocker_attribution=[dict(instance=n,gained_cells=int((gained&q).sum())) for n,q in OWN['N'].items() if (gained&q).any()])
out['nominal_site_footprint_deltas']=sorted([dict(driver=n,N=round(ST['N'][n],3),O=round(ST['O'][n],3),delta=round(ST['O'][n]-ST['N'][n],3)) for n in ST['N'].keys()|ST['O'].keys()],key=lambda x:-abs(x['delta']))[:25]
fix=['refcfg_SW','refcfg_NW','cij_SW','cij_SE','cij_NW','cij_NE'];mo=json.load(open(paths['O']/'case_a_manifest.json'));model=json.load(open(Path(__file__).parents[1]/'hbm_release_r16_1021/plano2M/corridor_model.json'));expected={x['instance']:x['after'] for x in model['placement_checks']};out['six_missed_homes']=[dict(instance=n,actual=mo['placement'][n],expected=expected[n],actual_intersects_window=bool(mask(next(b for nn,v,b in boxes(mo) if nn==n)).any()),expected_intersects_window=bool(mask((expected[n]['x'],expected[n]['y'],expected[n]['x']+expected[n]['w'],expected[n]['y']+expected[n]['h'])).any())) for n in fix]
out['demand_attribution_limit']='Report demand is cap.used booked across neighbouring bins (consume radius2 or4); emitted stations contain sites but not per-station forced/spread or per-bin booking ledger. Nominal site-footprint membership is exact for emitted coordinates but cannot be equated to booked-window demand. No reroute/replan performed.'
Path(__file__).with_name('decomposition.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'grid':out['grid_delta'],'deltas':out['nominal_site_footprint_deltas'][:8],'six_intersections':[(x['instance'],x['actual_intersects_window'],x['expected_intersects_window']) for x in out['six_missed_homes']]},indent=2))
