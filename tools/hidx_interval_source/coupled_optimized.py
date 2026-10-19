"""Default-off SOURCE MODEL. No EDA engines; no production graph changes."""
import collections,gzip,hashlib,json,resource,time
from interval_successor import optimum_pair
from pathlib import Path
P=Path('input'); O=Path('output');O.mkdir(exist_ok=True)
def load(n):
 return json.load(gzip.open(P/n,'rt')) if n.endswith('.gz') else json.load(open(P/n))
trees=load('native_RMST_tree_ledger.json.gz');site=load('site_plan.json.gz');pg=load('pg_ledger.json');clock=load('clock_reserve.json')
assert len(trees)==11449 and len(site)==11145
reserved={tuple(x) for a in clock['reserved_H_rays'].values() for x in a}
H=sorted(set((l,y) for l in ('M2','M4') for r in ('south','band','north') for y in pg['summary'][l+':via_landing:'+r]['clear_track_nm'])-reserved)
V=sorted((l,x) for l in ('M3','M5') for x in pg['summary'][l+':via_landing:all']['clear_track_nm'])
owned=collections.defaultdict(list); C=collections.Counter(); allrows=[];start=time.time()
RC={'M2':.174942,'M3':.155554,'M4':.178475,'M5':.164264}
def free(l,axis,c,a,b,n):
 a,b=sorted((a,b))
 return not any(q!=n and a<=d+100 and b>=e-100 for e,d,q in owned[l,axis,c])
def seg(l,axis,c,a,b):return (l,axis,c,min(a,b),max(a,b))
def joglayer(p):return 'M4' if p[0]<2160 or p[0]>138240 or p[1]<2160 or p[1]>138240 else 'M2'
def branch(a,b,n):
 """Same finite SOURCE branch domain; exact interval minimum replaces pairs.
 A/B ranks preserve original native layer duplicate identity and ties.
 Endpoint pruning only removes candidates that cannot strictly improve best.
 """
 ax,ay=a;bx,by=b;best=None;bestlen=float('inf')
 av=sorted(V,key=lambda z:(abs(z[1]-ax),z));bv=sorted(V,key=lambda z:(abs(z[1]-bx),z))
 hs=sorted(H,key=lambda z:(abs(ay-z[1])+abs(by-z[1])+abs(ax-bx),z))
 for hl,hy in hs:
  vertical=abs(ay-hy)+abs(by-hy)
  if vertical+abs(ax-bx)>=bestlen:break
  aa=[];bb=[]
  for ar,(al,vx) in enumerate(av):
   ja=abs(ax-vx)
   if vertical+ja>=bestlen:break
   if not free(al,'V',vx,ay,hy,n) or not free(joglayer(a),'H',ay,ax,vx,n):continue
   aa.append((al,vx,ar))
  if not aa:continue
  for br,(bl,wx) in enumerate(bv):
   jb=abs(bx-wx)
   if vertical+jb>=bestlen:break
   if not free(bl,'V',wx,by,hy,n) or not free(joglayer(b),'H',by,bx,wx,n):continue
   bb.append((bl,wx,br))
  blocked=[(e-100,d+100) for e,d,q in owned[hl,'H',hy] if q!=n]
  choice=optimum_pair(aa,bb,blocked,ax,bx)
  if choice is None:continue
  cost,ar,br,al,vx,bl,wx=choice;length=vertical+cost
  if length>=bestlen:continue
  ss=[seg(joglayer(a),'H',ay,ax,vx),seg(al,'V',vx,ay,hy),seg(hl,'H',hy,vx,wx),seg(bl,'V',wx,by,hy),seg(joglayer(b),'H',by,bx,wx)]
  waypoints=[a,(vx,ay),(vx,hy),(wx,hy),(wx,by),b]
  best=(ss,length,waypoints);bestlen=length
 return best
def union_length(items):
 end=None;total=0
 for a,b in sorted(items):
  if end is None or a>end:total+=b-a;end=b
  elif b>end:total+=b-end;end=b
 return total/1000
# Fewest-contact local branches first prevents long unqualified weak-driver detours.
# Exactly one deterministic construction; no parameter sweep or retries.
order=sorted(range(len(trees)),key=lambda n:(len(trees[n]['access_points_um']),trees[n]['total_tree_length_um'] if 'total_tree_length_um' in trees[n] else trees[n]['max_tree_root_path_um'],n))
for ordinal,n in enumerate(order):
 t=trees[n];pts=[tuple(round(v*1000) for v in p) for p in t['access_points_um']];connected={0};pending=set(range(1,len(pts)));edges=[];failed=[];metals=collections.defaultdict(list);dist={0:0};anchors=[]
 while pending:
  # Finite nearest-connected-contact / existing-segment projection topology.
  # Each projection is an actual shared branch join, with native stack HOLD.
  # A failed pair is retained, with
  # no alternative topology retry, so this does not claim global infeasibility.
  options=[]
  for j in pending:
   px,py=pts[j]
   for i in connected:options.append((abs(pts[i][0]-px)+abs(pts[i][1]-py),j,pts[i],dist[i],('contact',i)))
   for ai,(l,axis,c,a,b,origin,origin_distance) in enumerate(anchors):
    q=(max(a,min(b,px)),c) if axis=='H' else (c,max(a,min(b,py)))
    rd=origin_distance+abs(q[0]-origin[0])+abs(q[1]-origin[1])
    options.append((abs(q[0]-px)+abs(q[1]-py),j,q,rd,('shared_segment',ai,l)))
  _,j,parentpoint,parentdistance,parentref=min(options)
  candidate=branch(parentpoint,pts[j],n);pending.remove(j)
  if candidate is None:failed.append({'point_index':j,'attempted_parent':parentref,'reason':'FINITE_COUPLED_BRANCH_DOMAIN_EXHAUSTED'});continue
  ss,length,waypoints=candidate
  for l,ax,c,a,b in ss:owned[l,ax,c].append((a,b,n));metals[l,ax,c].append((a,b))
  walked=0
  for k,(l,ax,c,a,b) in enumerate(ss):
   anchors.append((l,ax,c,a,b,waypoints[k],parentdistance+walked))
   walked+=abs(waypoints[k][0]-waypoints[k+1][0])+abs(waypoints[k][1]-waypoints[k+1][1])
  connected.add(j);dist[j]=parentdistance+length;edges.append({'parent':parentref,'parent_point_nm':parentpoint,'child_contact':j,'length_um':length/1000,'segments_nm':ss})
 lengths=collections.Counter()
 for (l,ax,c),ints in metals.items():lengths[l]+=union_length(ints)
 cap=sum(RC[l]*v for l,v in lengths.items());complete=len(connected)==len(pts);caps={}
 for co,c in t['corner_cap'].items():
  total=c['native_plus_external_fF']+cap;limit=t['native_max_cap_fF'].get(co);bad=limit is not None and total>limit
  caps[co]={'native_plus_external_fF':c['native_plus_external_fF'],'union_wire_fF':cap,'total_excluding_UNKNOWN_via_fringe_fF':total,'native_max_fF':limit,'excess':bad}
  C['cap_excess_'+co]+=int(bad);C['complete_cap_excess_'+co]+=int(bad and complete)
 C['native_contacts']+=len(pts);C['connected_contacts']+=len(connected);C['nets_complete' if complete else 'nets_incomplete']+=1
 row={'net_index':n,'driver':t['driver'],'points_nm':pts,'connected_contact_indices':sorted(connected),'failures':failed,'edges':edges,'union_wire_length_um':dict(lengths),'corner_cap':caps,'complete_modeled_branch_graph':complete,'root_paths_um':{str(k):v/1000 for k,v in dist.items()} if complete else None,'local_native_access':'HOLD','unique_via_cut_union':'HOLD'}
 allrows.append(row)
 if ordinal%100==0:print(json.dumps({'processed':ordinal,'elapsed_seconds':round(time.time()-start,2),'counts':dict(C)}),flush=True)
assert C['native_contacts']==31384
summary={'status':'FAIL' if C['nets_incomplete'] or C['cap_excess_TT'] or C['cap_excess_FF'] else 'MODELED_BRANCH_GRAPH_ONLY_ACCESS_DRC_HOLD','counts':dict(C),'source_cells':len(site),'new_buffers':0,'new_FF':0,'new_source_cycles':0,'horizontal_candidate_rays':len(H),'vertical_candidate_columns':len(V),'clock_reserved_rays':len(reserved),'original_actual_checkpoint':'70042afe82ff76fc2657f45fb6c2a89f91eed2993add8e9dc89f2fc612fc88a6','runtime_seconds':time.time()-start,'maxrss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir()},'open':['native M1 local access and local-jog PG clear','exact shared default via CUT union and enclosures','all native signal DRC and crossing stacks','native PG contact/conductor/short for proposed positions','all via fringe cap','waveform setup hold real clock and upstream fixed point'],'max_complete_root_path_um':max((max(r['root_paths_um'].values(),default=0) for r in allrows if r['root_paths_um'] is not None),default=None)}
with gzip.open(O/'branches.json.gz','wt') as f:json.dump(sorted(allrows,key=lambda r:r['net_index']),f)
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
