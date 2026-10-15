#!/usr/bin/env python3
"""Exact exported-pin and actual chain-guide cut audit, no native waiver."""
import argparse,collections,gc,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import group_placement_opt as G

def guide_cuts(plan):
 # Count actual exported directed chain polylines once each. Capacity is only
 # over-tile M6/M8 usable tracks, not clock/PG/remaining buses. This is an
 # explicit route-guide screen, not exact final detailed-routing demand.
 bins=collections.Counter();cell=260.;seen=set();nonrect=[]
 for c in plan.get('chain_paths',[]):
  if c['chain'] in seen:raise ValueError('duplicate chain')
  seen.add(c['chain']);bits=sum(c['lanes'])
  for a,b in zip(c['path'],c['path'][1:]):
   x,y=a;X,Y=b
   if abs(x-X)<1e-6:
    for k in range(math.floor(min(y,Y)/cell)+1,math.ceil(max(y,Y)/cell)):
     bins[('Y',k,math.floor(x/cell))]+=bits
   elif abs(y-Y)<1e-6:
    for k in range(math.floor(min(x,X)/cell)+1,math.ceil(max(x,X)/cell)):
     bins[('X',k,math.floor(y/cell))]+=bits
   else:nonrect.append([c['chain'],a,b])
 capacity=cell*G.PA.OVER_TILE_PER_UM
 top=[dict(axis=ax,cut_coordinate_um=k*cell,window_span_um=[window*cell,(window+1)*cell],bits=n,usable_tracks=capacity,share=n/capacity) for (ax,k,window),n in bins.most_common(30)]
 return dict(scope='ACTUAL_CHAIN_POLYLINE_GUIDE_SCREEN_NOT_FINAL_PINROUTE',window_um=cell,capacity_rule='M8(.080)75% +M6(.064)75%; M5cappedtile excluded',top30=top,over060_windows=sum(n/capacity>.6 for n in bins.values()),windows=len(bins),nonrectilinear_segments=nonrect,exclusions=['Clock/PG/reset and nonchain direct buses','Actualstation pin jogs and path repairs','All physical changes for final328+150VM and cap/CDC children','Nativeobstructions/halos and detailedroute/resource sharing'])
def analyze(planpath,lefpath):
 p=json.loads(G.read(planpath));print('MODEL_START',planpath.name,len(p['insts']),len(p['buses']),flush=True);m=G.Model(p,[G.read(lefpath)],p['die']);print('MODEL_READY',len(m.edges),len(m.missing),flush=True)
 total=dict(sum_bit_um=0,max_um=0,over500_bits=0,alignment_failures=0,endpoint_bits=0);classes={};top=[];long=[];fails=[];abuts=0
 for i,e in enumerate(m.edges):
  aa,bb=e['points'];ll=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(aa,bb)];q=G.PA.bundle(aa,bb);ss=sum(ll);mx=max(ll);over=sum(x>500+1e-6 for x in ll);failed=q['verdict']=='FAIL';row=dict(bus=e['bus'],class_=e['cls'],ends=e['ends'],bits=e['bits'],sum_bit_um=ss,max_um=mx,over500_bits=over,alignment=q)
  if len(top)<30 or ss>min(v['sum_bit_um'] for v in top):top=sorted(top+[row],key=lambda r:r['sum_bit_um'],reverse=True)[:30]
  if over and (len(long)<30 or mx>min(v['max_um'] for v in long)):long=sorted(long+[row],key=lambda r:r['max_um'],reverse=True)[:30]
  if failed:fails.append(row)
  total['sum_bit_um']+=ss;total['max_um']=max(total['max_um'],mx);total['over500_bits']+=over;total['alignment_failures']+=failed;total['endpoint_bits']+=e['bits']
  c=classes.setdefault(e['cls'],dict(edges=0,endpoint_bits=0,sum_bit_um=0,max_um=0,over500_bits=0,alignment_failures=0));c['edges']+=1;c['endpoint_bits']+=e['bits'];c['sum_bit_um']+=ss;c['max_um']=max(c['max_um'],mx);c['over500_bits']+=over;c['alignment_failures']+=failed
  if i%30000==0:print('EDGES',i,flush=True)
 exempt=collections.Counter(c for _,c,_,_ in p['buses'] if c in G.PA.EXEMPT_CLS)
 hubs={r[0]:sum(any(n==r[0] for n,_ in e['ends']) for e in m.edges) for r in p['insts'] if len(r)>7 and r[7]=='hub'}
 out=dict(scope=p['scope'],source_sha256={str(v):hashlib.sha256(v.read_bytes()).hexdigest() for v in [planpath,lefpath]},instances=len(p['insts']),buses=len(p['buses']),resolved_point_to_point_edges=len(m.edges),missing_edges=m.missing,exempt_classes=dict(exempt),total=total,by_class=classes,top30_widthweighted_routes=top,top30_long_hops=long,alignment_failure_routes=fails,hub_incident_edges=hubs,calendar=p.get('calendar'),guide_cuts=guide_cuts(p),coverage_gaps=['Constructioncomplete is current generator topology, not finalproductionmaster closure','Current VM singleparent is superseded by actual328core+150writeedge and cap/CDC rootinventory','No activity/serialization/scheduleweighting; no nativeTT/FFclock/PGphysical qualification','500um is geometry bound only; measured native sourcearcs can require shorter hops','Clock/reset/topinput classes excluded from data pin audit explicitlylisted'])
 del m;gc.collect();return out

def main():
 ap=argparse.ArgumentParser()
 for n in ['plan','lef','baseline_plan','baseline_lef','out']:ap.add_argument('--'+n.replace('_','-'),type=Path,required=True)
 a=ap.parse_args();new=analyze(a.plan,a.lef);old=analyze(a.baseline_plan,a.baseline_lef);cal0={r['root']:r for r in old['calendar']};cal1={r['root']:r for r in new['calendar']};deltas=[]
 for r in sorted(cal0.keys()&cal1.keys()):
  x,y=cal0[r],cal1[r];deltas.append(dict(root=r,half=y['physical_half'],x_stations_before=x['x_stations'],x_stations_after=y['x_stations'],x_station_delta=y['x_stations']-x['x_stations'],x_path_before_um=x['x_path_um'],x_path_after_um=y['x_path_um'],return_stations_before=x['return_stations'],return_stations_after=y['return_stations']))
 report=dict(schema='opentallas.s81.complete_construction_geometry.v1',candidate=new,baseline_partial=old,calendar_deltas=deltas,comparison_scope='Calendarall128roots comparable; totalwire and guidecuts have differentcontrolgraphcoverage, not wholeproductionobjective comparison',audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());a.out.write_text(json.dumps(report,indent=1)+'\n');print('FINAL',json.dumps(dict(new=new['total'],missing=len(new['missing_edges']),old=old['total'],cal=len(deltas))),flush=True)
if __name__=='__main__':main()
