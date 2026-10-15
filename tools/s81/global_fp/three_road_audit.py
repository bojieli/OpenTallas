#!/usr/bin/env python3
"""Exact source logical vertical cut and optimistic3road allocation; no physical route claim."""
import argparse,gzip,hashlib,json,bisect
from pathlib import Path
CAP=5484.375/260
OLD={'S14W':[13428.72,13938.48],'VCH':[15670.8,17312.4],'S14E':[19044.72,19554.48]}
NEW={'S14W':[13428.72,13938.48],'VCH':[18457.2,19040.4],'S14E':[19044.72,19554.48]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 p=Path(a.plan);plan=json.load(gzip.open(p));segments=[]
 for ci,c in enumerate(plan['chain_paths']):
  for pi,(u,v) in enumerate(zip(c['path'],c['path'][1:])):
   if abs(u[0]-v[0])>1e-6 or u[1]==v[1]:continue
   road=next((n for n,(lo,hi) in OLD.items() if lo<=u[0]<=hi),None)
   if road is None:continue
   lo,hi=sorted([u[1],v[1]]);bits=sum(c['lanes'])+len(c['lanes'])
   segments.append(dict(id=f'{ci}_{pi}',chain=c['chain'],source_road=road,original_points=[u,v],lo=lo,hi=hi,bits=bits))
 ys=sorted({s[k] for s in segments for k in ['lo','hi']});loads={n:[0]*(len(ys)-1) for n in OLD}
 def indices(s):return range(bisect.bisect_left(ys,s['lo']),bisect.bisect_left(ys,s['hi']))
 for s in segments:
  for j in indices(s):loads[s['source_road']][j]+=s['bits']
 total=[sum(loads[n][i] for n in OLD) for i in range(len(ys)-1)];ix=max(range(len(total)),key=total.__getitem__);peak=total[ix];totalwidth=sum(hi-lo for lo,hi in NEW.values())
 allocation={n:[0]*len(total) for n in NEW};assigned=[]
 for s in sorted(segments,key=lambda s:-s['bits']*(s['hi']-s['lo'])):
  js=list(indices(s));opts=[]
  for n,(lo,hi) in NEW.items():
   # Pick the minimum new whole-road peak fraction for this indivisible segment.
   share=max((allocation[n][j]+s['bits'])/(CAP*(hi-lo)) for j in js)
   opts.append((share,n))
  _,n=min(opts);lo,hi=NEW[n]
  for j in js:allocation[n][j]+=s['bits']
  assigned.append(dict(segment=s['id'],chain=s['chain'],assigned_road=n,bits=s['bits'],vertical_points=[[(lo+hi)/2,s['lo']],[(lo+hi)/2,s['hi']]],status='VERTICAL_TRUNK_ASSIGNMENT_ONLY_ACCESS_AND_STATIONS_NOT_ROUTED'))
 x2=[0]*len(total)
 for s in segments:
  if s['chain'].startswith(('cxW','cxE')):
   for j in indices(s):x2[j]+=539
 x2total=[v+x2[i] for i,v in enumerate(total)];xix=max(range(len(total)),key=x2total.__getitem__)
 result=dict(scope='SOURCE_BOUND_CENTER_POLYLINE_CONDITIONAL_CUT_FAIL_NO_PHYSICAL_ROUTE',source=a.plan,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_commit='GEN18c exact preserved sourceplan, historical before actualcurrent GEN',capacity_per_um=CAP,old_roads=OLD,new_roads=NEW,total_new_width=totalwidth,source_vertical_segments=len(segments),joint_peak=dict(bits=peak,y_um=ys[ix],by_road={n:loads[n][ix] for n in OLD},required_width_at060=peak/CAP/.6,unavoidable_ideal_balanced_share=peak/CAP/totalwidth,extra_width_at060=peak/CAP/.6-totalwidth),individual_peaks={n:dict(bits=max(loads[n]),required_width_at060=max(loads[n])/CAP/.6) for n in OLD},BF_x2_sensitivity=dict(added_lane_bits=538,added_forward_clock=1,peak_total=x2total[xix],y_um=ys[xix],minimum_width_at060=x2total[xix]/CAP/.6),optimistic_whole_segment_allocation=dict(max_road_shares={n:max(allocation[n])/(CAP*(hi-lo)) for n,(lo,hi) in NEW.items()},assignment=assigned),source_segments=segments,gaps=['Sourcecenterpolyline backtracks nearplacedstation centers inflate some microscopic cuts; compare RP replay calibration before interpreting as physical pin-track demand.','Source is GEN18c baseline subset; future topology can localize/remove longtrunks, requiring new source-bound allincident graph.','Assignments have no source/sink access legs, no stations and no clock/PG; even granting these free, conservation lowerbound fails0.60.','S14 existingloads cannot be treated as free capacity. Mere VCH19354comparison loses S14source loads.','No actual currentVM externalpin placement or source-linked HC/SU/control homes, so no false physical route emitted.','BFx2 source successor may differ in path andstation stops;539sensitivity copies oldxsegments, not emitted successor evidence.'])
 Path(a.out).write_text(json.dumps(result,indent=1));print(json.dumps({k:result[k] for k in ['joint_peak','individual_peaks','BF_x2_sensitivity']},indent=1))
if __name__=='__main__':main()
