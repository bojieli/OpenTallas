#!/usr/bin/env python3
"""Source-canonical 128-lane return replay comparing old membership and adopted RP.
Preserves actual baseline sink homes and all non-return source chains. No station or physicalroute claim.
"""
import argparse,ast,gzip,hashlib,heapq,json,subprocess,types
from pathlib import Path
from three_road_audit import OLD,CAP

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--trees',required=True);ap.add_argument('--out',required=True);ap.add_argument('--hub-layout');a=ap.parse_args()
 src=Path(a.plan);plan=json.load(gzip.open(src));trees=json.loads(Path(a.trees).read_text())['trees'];frames={int(k):v for k,v in plan['frames'].items()};insts={i[0]:i for i in plan['insts']}
 cp='results/physical/die_iter_1012/s81/canonical_gen_1015/capacity_service_gap_broad_reroot_E.json';cb=subprocess.check_output(['git','show','eb9cfa044:'+cp]);canonical=json.loads(cb);assert hashlib.sha256(cb).hexdigest()==plan['variant']['canonical_layout']['sha256']
 code=subprocess.check_output(['git','show','eb9cfa044:tools/s81/canonical_layout.py']).decode();tree=ast.parse(code);node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Roadmap');ns={'heapq':heapq};exec(compile(ast.Module(body=[node],type_ignores=[]),'<source-canonical-Roadmap>','exec'),ns)
 G=types.SimpleNamespace(COL_W8=1182.816,RSC_W=47.52,s14_x=lambda m,side,tag:13500.55 if side=='W' else 19116.55,stn_dims=lambda lanes,horiz:(54.84,17.256))
 m={'frames':frames,'canonical_layout':canonical};road=ns['Roadmap'](G,m,{},return_lanes=True)
 for side in 'WE':
  es=sorted(road.entry[side],key=lambda n:n[1])
  for u,v in zip(es,es[1:]):road.add(u,v)
 rsc=set(road.sx.values())
 for u,edges in road.graph.items():
  for v,w in list(edges.items()):
   if u[0]==v[0] and u[0] in rsc:edges[v]=2*w
 ret=[c for c in plan['chain_paths'] if c['chain'].startswith('cr')];widths={w for c in ret for w in c['lanes']};assert widths=={70},widths
 busindex={}
 for b in plan['buses']:
  for inst,port in b[3]:busindex.setdefault(inst,[]).append(b)
 source_endpoints={}
 for c in plan['chain_paths']:
  st={d['inst'] for d in c.get('stations',[])};boundary={}
  for inst in st:
   for b in busindex.get(inst,[]):
    ext=[e for e in b[3] if e[0] not in st]
    if ext:boundary[b[0]]=dict(bus=b[0],bits=b[2],external_endpoints=ext)
  source_endpoints[c['chain']]=list(boundary.values())
 other=[c for c in plan['chain_paths'] if not c['chain'].startswith('cr')]
 anchors={};allcross=[]
 def inroad(x,n):return OLD[n][0]<=x<=OLD[n][1]
 for t in trees:
  key=f"{t['half']}{t['tier']}";hr=insts['hr_'+key];dst=[hr[2]+hr[4]/2,hr[3]+hr[5]/2];anch={'destination':dst,'destination_outline':hr[2:6]}
  for c in ret:
   if not c['chain'].startswith('cr'+key+'_') or not c['chain'].endswith('_hub'):continue
   for u,v in zip(c['path'],c['path'][1:]):
    if abs(u[1]-v[1])>1e-6:continue
    if inroad(u[0],'S14E') and inroad(v[0],'VCH'):anch.update(cy=u[1],vx=v[0])
    if (inroad(u[0],'S14W') and inroad(v[0],'VCH')) or (inroad(v[0],'S14W') and inroad(u[0],'VCH')):anch['yy']=u[1];allcross.append(u[1])
  if 'cy' not in anch:anch.update(cy=13199.76,vx=16491.6,unused_source_E_anchor_fallback=True)
  anchors[key]=anch
 for key,anch in anchors.items():
  if 'yy' not in anch:anch['yy']=min(allcross,key=lambda y:abs(y-anch['destination'][1]));anch['yy_fallback_from_other_source_group']=True
 requested_hub=None
 if a.hub_layout:
  requested_hub=json.loads(Path(a.hub_layout).read_text());ga=requested_hub['blocks']['sp_gather'];corr=requested_hub['corridor']
  for side in 'WE':
   hrs=[insts[f'hr_{side}{t}'] for t in range(6)];extent=sum(hr[5] for hr in hrs)+5*21.6;yy=ga[1]+(ga[3]-extent)/2
   for t,hr in enumerate(hrs):
    key=f'{side}{t}';cy=corr[1]+60+(corr[3]-120)*(.15+.7*t/5)
    anchors[key]=dict(destination=[13683.6 if side=='W' else 18748.8,yy+hr[5]/2],destination_outline=[(13683.6 if side=='W' else 18748.8)-hr[4]/2,yy,hr[4],hr[5]],cy=cy,yy=cy,vx=18748.8,status='REQUESTED_SOURCE_OUTLINE_LOWERBOUND_HOME_NOT_EMITTED',old_source_hr_outline=hr[4:6]);yy+=hr[5]+21.6
 def replay(use_rp):
  chains=[];members=[]
  for t in trees:
   key=f"{t['half']}{t['tier']}";roots=t['roots'] if use_rp else t['was'];anc=anchors[key];gx,gy=anc['destination'];cy=anc['cy'];vx=anc['vx'];yy=anc['yy']
   for side in 'WE':
    entry=min(road.entry[side],key=lambda n:abs(n[1]-gy));dist={entry:0};parent={entry:None};q=[(0,entry)]
    while q:
     cost,u=heapq.heappop(q)
     if cost!=dist[u]:continue
     for v,w in road.graph[u].items():
      if cost+w<dist.get(v,float('inf')):dist[v]=cost+w;parent[v]=u;heapq.heappush(q,(cost+w,v))
    for root in roots:
     f=frames[root]
     if f['half']!=side:continue
     source=road.rootnode[(root,'r')];path=[source];u=source
     while u!=entry:u=parent[u];path.append(u)
     wx=entry[0] if side=='W' else road.entry['W'][0][0]
     if side=='E':path +=[(entry[0],cy),(vx,cy)]
     if side!=t['half']:path +=[(path[-1][0],yy),(wx if t['half']=='W' else vx,yy)]
     path +=[(path[-1][0],gy),(gx,gy)]
     cf=insts['cf'+str(root)];cp=[cf[2]+cf[4]/2,cf[3]+cf[5]/2];path=[cp,(cp[0],source[1])]+path
     clean=[]
     for p in path:
      if not clean or p!=clean[-1]:clean.append(p)
     chains.append(dict(chain=f"RP_{key}_cf{root}",lanes=[70],path=clean,source_endpoint=dict(data=[f'cf{root}','rd'],clock=[f'cf{root}','rf']),sink_endpoint=dict(data=[f'hr_{key}',f'di{len(roots)-1-roots.index(root)}'],clock=[f'hr_{key}',f'fi{len(roots)-1-roots.index(root)}']),lane_provenance='Generator logical_col=listindex; canonicaltrunks sortslogical_colreverse before enumeratinglane' ,source_frame_half=side,logical_tree=t['half'],logical_tier=t['tier']))
     members.append(root)
  assert sorted(members)==list(range(128))
  return chains
 def broadcast(pair=False):
  br=ns['Roadmap'](G,m,{},return_lanes=False);chains=[]
  for side in 'WE':
   es=sorted(br.entry[side],key=lambda n:n[1])
   for u,v in zip(es,es[1:]):br.add(u,v)
   if requested_hub:
    pq=requested_hub['blocks']['sp_pq'];source=[13683.6 if side=='W' else 18748.8,pq[1]+pq[3]/2];corr=requested_hub['corridor'];cy=corr[1]+60+(corr[3]-120)*.5
   else:
    hx=insts['hx_'+side];source=[hx[2]+hx[4]/2,hx[3]+hx[5]/2];prefix=plan['broadcast_trees'][side]['prefix'];cy=next((u[1] for u,v in zip(prefix,prefix[1:]) if abs(u[1]-v[1])<1e-6 and abs(u[0]-v[0])>100),13199.76)
   targets=[br.rootnode[(root,'x')] for root,f in frames.items() if f['column_index']==(10 if side=='W' else 11)];root=min(targets,key=lambda n:abs(n[1]-source[1]));entry=next(n for n in es if n[1]==root[1]);override=canonical.get('broadcast_entry_overrides',{}).get(side)
   if override is not None:entry=min(es,key=lambda n:abs(n[0]-override[0])+abs(n[1]-override[1]));assert abs(entry[1]-override[1])<.001
   prefix=[source,[source[0],cy],[entry[0],cy],entry] if side=='E' else[source,[entry[0],source[1]],entry]
   dist={entry:0};parent={entry:None};q=[(0,entry)]
   while q:
    cost,u=heapq.heappop(q)
    if cost!=dist[u]:continue
    for v,w in br.graph[u].items():
     if (v[0]<13942.8 and side=='E') or (v[0]>19040.4 and side=='W'):continue
     if cost+w<dist.get(v,float('inf')):dist[v]=cost+w;parent[v]=u;heapq.heappush(q,(cost+w,v))
   required=set()
   for root,f in frames.items():
    if f['half']!=side:continue
    u=br.rootnode[(root,'x')]
    while u is not None:required.add(u);u=parent[u]
   lanes=[566,538] if pair else[566];chains.append(dict(chain=f'BC_{side}_spine',lanes=lanes,path=prefix,source_endpoint=[f'hx_{side}','fo/oa andfo2/ob'],sink_endpoint='sharedsourcecanonical broadcasttree'))
   for k,u in enumerate(sorted(required-{entry},key=lambda n:dist[n])):chains.append(dict(chain=f'BC_{side}_edge{k}',lanes=lanes,path=[parent[u],u],source_endpoint='sourcecanonical parentnode',sink_endpoint='sourcecanonical childnode'))
  return chains
 def segments(chains,bfx2=False):
  ss=[]
  for c in chains:
   bits=sum(c['lanes'])+len(c['lanes'])
   if bfx2 and c['chain'].startswith(('cxW','cxE')):bits+=539
   for i,(u,v) in enumerate(zip(c['path'],c['path'][1:])):
    if abs(u[0]-v[0])>1e-6 or u[1]==v[1]:continue
    n=next((n for n in OLD if inroad(u[0],n)),None)
    if n is None and requested_hub and 18457.2<=u[0]<=19040.4:n='VCH'
    if n:
     lo,hi=sorted([u[1],v[1]]);ss.append(dict(chain=c['chain'],road=n,bits=bits,lo=lo,hi=hi,path_edge=i,source_endpoint=c.get('source_endpoint'),sink_endpoint=c.get('sink_endpoint'),source_bus_boundary_key=c['chain'] if c['chain'] in source_endpoints else None))
  return ss
 def stats(chains,bfx2=False):
  ss=segments(chains,bfx2);ys=sorted({s[k] for s in ss for k in ['lo','hi']});worst=(0,None);first=None;widths={'S14W':509.76,'VCH':583.2,'S14E':509.76}
  for y in ys:
   active=[s for s in ss if s['lo']<=y<s['hi']];total=sum(s['bits'] for s in active)
   if total>worst[0]:worst=(total,y)
   if first is None and total>sum(widths.values())*CAP*.6:first=dict(y_um=y,bits=total,active=active)
  y=worst[1];active=[s for s in ss if s['lo']<=y<s['hi']]
  return dict(peak_bits=worst[0],y_um=y,by_road={n:sum(s['bits'] for s in active if s['road']==n) for n in OLD},minimum_width_at060=worst[0]/CAP/.6,best_ideal_share=worst[0]/CAP/sum(widths.values()),peak_active=active,first_failing_cut=first)
 old=replay(False);rp=replay(True);actual=stats(plan['chain_paths']);cal=stats(other+old);new=stats(other+rp);x2=stats(other+rp,True)
 bc=broadcast(False);bc2=broadcast(True);service=[c for c in other if not c['chain'].startswith('cx')];rpb=stats(service+rp+bc);rpb2=stats(service+rp+bc2)
 at=actual['y_um'];calibration_at_actual_peak={}
 for key,cs in [('actual',plan['chain_paths']),('old_model',other+old),('RP_model',other+rp)]:
  active=[s for s in segments(cs) if s['lo']<=at<s['hi']];calibration_at_actual_peak[key]=dict(bits=sum(s['bits'] for s in active),by_road={n:sum(s['bits'] for s in active if s['road']==n) for n in OLD},return_bits_by_road={n:sum(s['bits'] for s in active if s['road']==n and s['chain'].startswith(('cr','RP_'))) for n in OLD},active=active)
 out=dict(source_bus_boundaries=source_endpoints,source_sink_outline_map={name:dict(master=i[1],xywh=i[2:6],orientation=i[6],kind=i[7]) for name,i in insts.items() if name in busindex},requested_hub_layout=a.hub_layout,requested_hub_status='SourceHRoutline placeholders, explicitcrossingcorridor, retained oldnonreturn sourcepaths NOTactualnewhubrouting' if requested_hub else 'ActualbaselineHRhomes',calibration_at_actual_peak=calibration_at_actual_peak,scope='SOURCE_WIDTH_CANONICAL_GRAPH_RP_REPLAY_NOT_EMITTED_STATION_LAYOUT',source_plan_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),source_trees_sha256=hashlib.sha256(Path(a.trees).read_bytes()).hexdigest(),canonical_source_sha256=hashlib.sha256(cb).hexdigest(),roadmap_source_sha256=hashlib.sha256(code.encode()).hexdigest(),transport=dict(frame_count=128,data_bits_per_return_frame=70,forward_clock_bits_per_frame=1,root_output_source_chains='Actual hr_*_o chains retained byte-identical with other service/hub chains'),anchors=anchors,actual_baseline=actual,calibrated_old_membership=cal,RP_same_actual_sink_homes=new,RP_plus_BFx2_sourcepath_sensitivity=x2,delta=dict(RP_vs_same_model_old=cal['peak_bits']-new['peak_bits'],RP_vs_actual_source=actual['peak_bits']-new['peak_bits'],source_calibration_model_minus_actual=cal['peak_bits']-actual['peak_bits']),RP_replanned_broadcast=rpb,RP_replanned_BFx2_broadcast=rpb2,replanned_BFx2_broadcast_chains=bc2,replanned_return_chains=rp,native_gaps=['Actual GEN20sa failed before returns; this is explicit sourcecanonical graph replay, not emitted GEN output or station placement.','Same actual baseline hr sinkhomes isolate RP membership; adopted SA hubhomes/currentVM640homes are not legal allincident placements.','Source-canonical endpoint CF/endb centers are CH emitter anchors, not measured pin rectangles.','Actual station centering/first-fit nudges and gap occupancy not reemitted; source-template crossing gap reused.','All source nonreturn paths and hr outputs retained; moving realhub endpoints requires their new actual pinjoin and complete reroute.','Replannedbroadcast exactsourceRoadmapsharedtree andcanonicalentryoverrides,566+538plus2clocks; newhx footprint/pins andallstations stillunplaced.','BFx2 sensitivity adds538data+1clock to every actual cx physicalsegment, not only one imagined trunk.'])
 target=Path(a.out);raw=json.dumps(out,indent=1).encode();target.write_bytes(gzip.compress(raw,mtime=0) if target.suffix=='.gz' else raw);print(json.dumps({k:{q:v[q] for q in ['peak_bits','y_um','minimum_width_at060']} for k,v in out.items() if k in ['actual_baseline','calibrated_old_membership','RP_same_actual_sink_homes','RP_plus_BFx2_sourcepath_sensitivity','RP_replanned_broadcast','RP_replanned_BFx2_broadcast']},indent=1));print(out['delta'])
if __name__=='__main__':main()
