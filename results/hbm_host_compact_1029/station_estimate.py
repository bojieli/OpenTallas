import json,sys,math
from pathlib import Path
P=Path(__file__).parent;D=json.load(open(sys.argv[1]));T=D['partition_types']['root'];pins=json.load(open(P/'pins_candidate.json'));core=next(c for c in T['hard_cores']if c['inst']=='u_host_cp_rxs');results=[]
for origin in [core['origin_um'],[43.2,622.08]]:
 rows=[];unknown=[]
 for si,s in enumerate(T.get('internal_stations',[])):
  for role,side,adj in [('launch','from',0),('capture','to',-1)]:
   ref=s.get(role,'')
   if not ref.startswith('u_host_cp_rxs.'):continue
   port=ref.split('.',1)[1];ps=[p for p in pins if p['name']==port or p['name'].startswith(port+'[')]
   if not ps or not s.get('regs_um'):unknown.append(dict(index=si,ref=ref));continue
   z=s['regs_um'][adj];legs=[]
   for p in ps:
    xy=[p['x']+origin[0],p['y']+origin[1]];L=abs(xy[0]-z[0])+abs(xy[1]-z[1]);legs.append((L,p['name'],xy))
   mx,n,xy=max(legs);rows.append(dict(index=si,ref=ref,conn=s.get('conn'),bits=len(ps),existing_adjacent_station_um=z,new_worst_pin=n,new_endpoint_um=xy,max_manhattan_lower_bound_um=round(mx,3),bits_gt405=sum(l[0]>405+1e-6 for l in legs),additional_hops_min=max(0,math.ceil(mx/405)-1)))
 results.append(dict(origin_um=origin,rows=rows,unmatched=unknown,max_leg_lower_bound_um=max([r['max_manhattan_lower_bound_um']for r in rows]or[0]),rows_gt405=sum(r['bits_gt405']>0 for r in rows),matched_station_rows=len(rows)))
report=dict(status='ESTIMATE ONLY; exact candidatepin coordinates vs published parent station sites. Manhattan lowerbound, not route length; all bit endpoints checked, root ft-slot bus spreading and clock paths remain owner obligation.',source_plan=sys.argv[1],candidates=results)
(P/'station_estimate.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(r['origin_um'],'rows',len(r['rows']),'max',r['max_leg_lower_bound_um'],'rows>405',r['rows_gt405'],'unknown',r['unmatched'])
