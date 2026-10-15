#!/usr/bin/env python3
"""Bounded complete-collective road localization screen, never physical admission.
Preserves source endpoints, all 128 returns, BF pair/shared graph, all other chains.
For moved collective+8 HL adapters, reroutes every incident constructed chain.
Native pin polygons, CTS/PG and stations remain explicit unresolved obligations.
"""
import argparse,collections,copy,gzip,hashlib,json,math
from pathlib import Path
CAP=21.09375
WIDTHS={'S14W':509.76,'VCH':583.2,'S14E':509.76}
ROADS={'S14W':(13428.72,13938.48),'VCH':(15670.8,17312.4),'S14E':(19044.72,19554.48)}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def road(x):
 for n,(l,h) in ROADS.items():
  if l<=x<=h:return n
 if 18457.2<=x<=19040.4:return 'VCH'
def segs(chains):
 for c in chains:
  for u,v in zip(c['path'],c['path'][1:]):
   if abs(u[0]-v[0])<1e-6 and abs(u[1]-v[1])>1e-6 and road(u[0]):
    yield (min(u[1],v[1]),max(u[1],v[1]),sum(c['lanes'])+len(c['lanes']),c['chain'],road(u[0]))
def stat(cs):
 ss=list(segs(cs));events=collections.defaultdict(int)
 for l,h,b,_,_ in ss:events[l]+=b;events[h]-=b
 load=0;peak=(-1,None)
 for y,d in sorted(events.items()):
  load+=d
  if load>peak[0]:peak=(load,y)
 active=[s for s in ss if s[0]<=peak[1]<s[1]]
 return dict(peak_tracks=peak[0],y_um=peak[1],saved_tracks=23572-peak[0],budget_at060=sum(WIDTHS.values())*CAP*.6,ideal_share=peak[0]/sum(WIDTHS.values())/CAP,by_road={n:sum(s[2] for s in active if s[4]==n) for n in WIDTHS},active=[dict(chain=s[3],road=s[4],tracks=s[2],lo=s[0],hi=s[1]) for s in active])
def length(path):return sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(path,path[1:]))
def collision(a,b):return a[0]<b[0]+b[2]-1e-6 and b[0]<a[0]+a[2]-1e-6 and a[1]<b[1]+b[3]-1e-6 and b[1]<a[1]+a[3]-1e-6

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--replay',required=True);ap.add_argument('--out',required=True);ap.add_argument('--hub-routing',default='admitted_road',choices=['admitted_road','retained_local_x']);ap.add_argument('--root',default='sp_collective',choices=['sp_collective','sp_hc_s','sp_hc_t']);a=ap.parse_args()
 p=json.load(gzip.open(a.plan));r=json.load(gzip.open(a.replay));inst={i[0]:i for i in p['insts']};base=[c for c in p['chain_paths'] if not c['chain'].startswith(('cr','cx'))]+r['replanned_return_chains']+r['replanned_BFx2_broadcast_chains'];assert stat(base)['peak_tracks']==23572
 root=a.root;group={root}|({f'hl_{s}{i}' for s in 'WE' for i in range(4)} if root=='sp_collective' else set())
 global_clock_reset={b[0] for b in p['buses'] if b[1] in ('clock','reset')}
 incident={}
 for c in p['chain_paths']:
  eps={tuple(e) for b in r['source_bus_boundaries'].get(c['chain'],[]) if b['bus'] not in global_clock_reset for e in b['external_endpoints'] if e[0] in group}
  if eps:incident[c['chain']]=sorted(eps)
 def endgroup(c,idx):
  # Chain boundary data/control buses name true native endpoint; select its box
  # nearest the source emitter anchor. No invented center pin coordinates.
  xy=c['path'][idx];options=[]
  for name,port in incident.get(c['chain'],[]):
   i=inst[name];x,y,w,h=i[2:6];dist=max(x-xy[0],0,xy[0]-x-w)+max(y-xy[1],0,xy[1]-y-h)
   options.append((dist,name,port))
  return min(options) if options else None
 def candidate(y,local_k=True):
  dy=y-inst[root][3];cs=[];ledger=[]
  for c0 in base:
   c=copy.deepcopy(c0)
   if c['chain'] not in incident:cs.append(c);continue
   path=c['path'];start=list(path[0]);end=list(path[-1]);changed=[]
   for idx,xy in [(0,start),(-1,end)]:
    z=endgroup(c,idx)
    if z and z[0]<2:xy[1]+=dy;changed.append(dict(end=idx,instance=z[1],port=z[2],anchor_distance_to_outline=z[0]))
   if c['chain'].startswith(('KW','KE')) and local_k:
    # Retain every field street segment. Replace only the hub-side road access,
    # using its actual departure y, eliminating source road backtracking.
    out=[i for i,xy in enumerate(path) if xy[0]<13428.72 or xy[0]>19554.48]
    if not out:raise ValueError(c['chain'])
    if changed and changed[0]['end']==0:
     j=out[0];q=path[j];rx=13683.6 if q[0]<13428.72 else 19299.6
     new=[start,[rx,start[1]],[rx,q[1]]]+path[j:]
    else:
     j=out[-1];q=path[j];rx=13683.6 if q[0]<13428.72 else 19299.6
     new=path[:j+1]+[[rx,q[1]],[rx,end[1]],end]
   else:
    # Every hub incident chain retained with exact translated source anchors;
    # road access legs require a later native-obstruction/station proof.
    vs=[(abs(u[1]-v[1]),u[0]) for u,v in zip(path,path[1:]) if abs(u[0]-v[0])<1e-6 and u[1]!=v[1]];rx=max(vs)[1] if a.hub_routing=='retained_local_x' and vs else 18748.8;new=path if abs(dy)<1e-6 else [start,[rx,start[1]],[rx,end[1]],end]
   assert changed, (c['chain'],'No source native data/forward-clock anchor matched')
   oldlen=length(path);newlen=length(new);c['path']=new;cs.append(c)
   oldst=len(c0.get('stations',[]));minst=max(0,math.ceil(newlen/500)-1)
   ledger.append(dict(chain=c['chain'],lanes=c['lanes'],endpoints=incident[c['chain']],translated_anchors=changed,source_path_length_um=oldlen,candidate_path_length_um=newlen,source_stations=oldst,minimum_stages_at500um=minst,retained_stages=max(oldst,minst),added_stages=max(0,minst-oldst),retiming_credit=0,path=new))
  home=[inst[root][2],y,*inst[root][4:6]]
  overlaps=[i[0] for i in p['insts'] if i[0].startswith('sp_') and i[0]!=root and collision(home,i[2:6])]
  local_events=collections.defaultdict(int)
  for item in ledger:
   for u,v in zip(item['path'],item['path'][1:]):
    if abs(u[0]-v[0])<1e-6 and u[1]!=v[1] and road(u[0]) is None:
     lo,hi=sorted([u[1],v[1]]);bits=sum(item['lanes'])+len(item['lanes']);local_events[lo]+=bits;local_events[hi]-=bits
  load=0;local_peak=0
  for yy,delta in sorted(local_events.items()):load+=delta;local_peak=max(local_peak,load)
  return dict(local_vertical_outside_admitted_roads_peak_tracks=local_peak,route_topology=a.hub_routing,group_y_um=y,home=home,statistics=stat(cs),incident_chain_count=len(ledger),stage_ledger=ledger,geometry=dict(die_inside=home[1]>=0 and home[1]+home[3]<=26000,overlapping_historical_whole_hubs=overlaps,adapters=[dict(instance=n,xywh=[inst[n][2],inst[n][3]+dy,*inst[n][4:6]]) for n in sorted(group-{root})],allincident_native_stations_placed=False,source_pins='Generator source anchor offsets translated exactly; native LEF pin access not measured'),status='BOUNDED_ROAD_SCREEN_NOT_BUILDABLE')
 ys=sorted(set([float(y) for y in range(0,int(26000-inst[root][5])+1,250)]+[inst[root][3],10005.211]+([12465.336] if root=='sp_hc_s' else [])))
 trials=[candidate(y) for y in ys];best=min(trials,key=lambda x:x['statistics']['peak_tracks']);old=candidate(inst[root][3]);sa=candidate(10005.211 if root=='sp_collective' else 12465.336)
 direct_buses=[dict(bus=b[0],kind=b[1],bits=b[2],endpoints=b[3]) for b in p['buses'] if b[1] not in ('clock','reset') and b[0]!='clk_stream' and any(e[0] in group for e in b[3]) and not any(e[0].startswith('f_') for e in b[3])]
 clock_buses=[dict(bus=b[0],kind=b[1],bits=b[2],endpoint_count=len(b[3])) for b in p['buses'] if b[1] in ('clock','reset') and any(e[0] in group for e in b[3])]
 out=dict(scope='COMPLETE_GROUP_ENDPOINT_BOUNDED_ROAD_LOCALIZATION',root=root,route_topology=a.hub_routing,source_canonical_sha256=r['canonical_source_sha256'],source_roadmap_sha256=r['roadmap_source_sha256'],source_trees_sha256=r['source_trees_sha256'],field_return_endpoints=[dict(chain=c['chain'],source=c['source_endpoint'],sink=c['sink_endpoint'],lanes=c['lanes']) for c in r['replanned_return_chains']],broadcast_source_endpoints=[dict(chain=c['chain'],source=c['source_endpoint'],sink=c['sink_endpoint'],lanes=c['lanes']) for c in r['replanned_BFx2_broadcast_chains'] if c['chain'].endswith('_spine')],source_plan_sha256=digest(a.plan),replay_sha256=digest(a.replay),script_sha256=digest(__file__),baseline=stat(base),group=sorted(group),group_direct_buses=direct_buses,clock_reset_obligations=clock_buses,ranked_alternatives=[dict(rank=1,name='best_scanned_whole_group_local_entry',**best),dict(rank=2,name='requested_collective_y_only_or_closed_HC_gap_local_entry',**sa),dict(rank=3,name='same_home_local_entry_only',**old)],scan=[dict(y=t['group_y_um'],peak=t['statistics']['peak_tracks']) for t in trials],gaps=['All 128x70-data+1clock returns and source shared 566+538+2clock broadcast preserved unchanged.','Complete incident constructed chains and direct native buses retained, with no workload changes.','Source old noncollective homes retained for bounded experiment; root free to repack all groups.','Collective requested SA y tested at historical source x; this is not the complete SA layout. Clock/reset endpoint obligations enumerated but CTS/PG and concrete station homes not emitted.','Kept source stage counts even when route shorter; extra minimum stages charged; static compiler clock age/turn retiming still unqualified.','Road access horizontals may cross bodies; no screen is a geometric routing or timing PASS.','Historical collective contract is not a source complete native footprint and adapter geometry could improve through legal constituent repacking.'])
 Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps([(t['name'],t['group_y_um'],t['statistics']['peak_tracks'],t['statistics']['saved_tracks'],t['geometry']['overlapping_historical_whole_hubs']) for t in out['ranked_alternatives']]))
if __name__=='__main__':main()
