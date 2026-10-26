import json,re,sys,copy,argparse
from pathlib import Path
from collections import defaultdict,Counter
ap=argparse.ArgumentParser()
ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
ap.add_argument('--requirements',type=Path)
ap.add_argument('--out',type=Path)
a=ap.parse_args()
R=a.root.resolve(); out=a.out.resolve() if a.out else R/'out'
if a.out and out.exists() and any(out.iterdir()):raise ValueError('refuse to overwrite an existing price case '+str(out))
out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R));import cb16_dag as D
req=json.load(open(a.requirements or R/'qc_r3_requirements.json')); add=req['lane_added_cycles']
bg=json.load(open(R/'bind_v7/bus_groups.json')); empty=out/'empty_r8.json';empty.write_text('{"members":[]}')
cache=R/'bind_v7/cb16_inputs.json'
if cache.exists():
 saved=json.load(open(cache)); inp=saved['inputs']; gid=defaultdict(set,{(r['leaf'],r['port']):set(r['members'])for r in saved['crossing_groups']})
else:
 inp,gid,r8,groups=D.load(R/'bind_v7',empty)
 cache.write_text(json.dumps(dict(source='canonical v7 final, strict377parts79types; input offsets from bind_sinks minus source stages',inputs=inp,crossing_groups=[dict(leaf=l,port=p,members=sorted(v))for(l,p),v in gid.items()]),indent=1)+'\n')
old=D.baseline(inp)
port_add=defaultdict(set);port_members=defaultdict(list); endpoints={}
for g in bg['landing']:
 for m in g['members']:
  endpoints.setdefault(m['lane'],(g['src_part'],g['sink_part']))
  if g['sink'].startswith('c16_'):
   k=g['sink'],m['sink_port'];port_add[k].add(add.get(m['lane'],0));port_members[k].append(m)
unknown=set(add)-set(endpoints)
if unknown:raise ValueError('landing lanes absent from bind: '+str(sorted(unknown)))
new=copy.deepcopy(inp);word_pads=[]
for leaf,ports in new.items():
 for p,(sl,sp,off) in ports.items():
  values=port_add.get((leaf,p),{0}); extra=max(values)
  ports[p]=(sl,sp,off+extra)
  if len(values)>1:
   word_pads.append(dict(leaf=leaf,port=p,nominal_additions=sorted(values),required_whole_port_add=extra))
nodes,relations,roots=D.build(new,gid); phase,iterations=D.solve(nodes,relations)
clusters={};before_max=-10**9;after_max=-10**9
rs=defaultdict(list)
for g in bg['landing']:
 if g['sink'].startswith('c16_'):continue
 for m in g['members']:
  if re.match(r'^c16_\w+\.u_t_0_0\.n_y$',m['source']):
   cluster=m['source'].split('.')[0];rs[cluster].append(dict(lane=m['lane'],sink=g['sink'],before=m['landed_stages']-m['asbuilt_stages'],added=add.get(m['lane'],0)))
for cluster,node in roots.items():
 before=old(cluster+'.u_t_0_0','n_y');after=phase[node]
 paths=rs[cluster]
 if not paths:raise ValueError('no root return path '+cluster)
 b=before+max(x['before']for x in paths);a=after+max(x['before']+x['added']for x in paths)
 clusters[cluster]=dict(root_before=before,root_after=after,rs=paths,total_before=b,total_after=a)
 before_max=max(before_max,b);after_max=max(after_max,a)
reference=json.load(open(R/'inputs/cb16_path.json'))['binds']['v7']['max_root_plus_rs']
if before_max!=reference:raise ValueError(f'wrong CB baseline: {before_max} != {reference}')
rephase=[]
for e in relations:
 extra=phase[e['dst']]-phase[e['src']]-e['off']
 if extra:
  if extra<0 or not e['ids']:raise ValueError('illegal phase fix')
  rephase.append(dict(e,extra=extra))
def member_id(g,m):
 bits=','.join('{}:{}'.format(a,b)for a,b in m['sink_bits'])
 return '{}.{}[{}]<-{}@{}'.format(g['sink'],m['sink_port'],bits,m['source'],m['asbuilt_stages'])
member_rows={member_id(g,m):m for g in bg['landing']for m in g['members']}
phase_requests={}
for e in rephase:
 for mid in e['ids']:
  if mid in phase_requests and phase_requests[mid]!=e['extra']:raise ValueError('conflicting phase request')
  phase_requests[mid]=e['extra']
rephase_ff=sum(n*sum(b-a+1 for a,b in member_rows[mid]['sink_bits'])for mid,n in phase_requests.items())

def col(p):
 m=re.match(r'^(?:sl|c)_([EW])(\d)_',p)
 return (5-int(m[2]) if m[1]=='W' else 6+int(m[2]))if m else None
hop_lanes={lane for lane,(s,t)in endpoints.items()if s.startswith('sl_')and t.startswith('sl_')and col(s)!=col(t)}
hops=defaultdict(list)
for lane in hop_lanes:
 if add.get(lane):
  s,t=endpoints[lane];hops[tuple(sorted((col(s),col(t))))].append((lane,add[lane]))
hop_add=sum(max(v for _,v in rows)for rows in hops.values())
l9_add=max([add[lane]for lane in hop_lanes if '__l9_'in lane and lane in add]or[0])
plain={lane:n for lane,n in add.items()if lane not in hop_lanes}
fe=json.load(open(R/'inputs/price_fereach_clkland_1026/add_fe.json'))
combined=dict(fe)
for lane,n in plain.items():combined[lane]=combined.get(lane,0)+n
# out is an immutable per-case directory when --out is provided
(out/'add_actual_land.json').write_text(json.dumps(plain,indent=1)+'\n')
(out/'add_actual_fe_land.json').write_text(json.dumps(combined,indent=1)+'\n')
report=dict(schema='opentallas.qc_actual_clock_landing_price_inputs.v1',source_table_sha256=req['source_table_sha256'],ports=req['crossings'],lanes=len(add),known_lanes=len(set(add)&set(endpoints)),nominal_additions=dict(Counter(add.values())),cb_before=before_max,cb_after=after_max,cb_add=after_max-before_max,cb_clusters=clusters,cb_rephase_relations=rephase,cb_whole_port_pads=word_pads,cb_solver_iterations=iterations,additional_cb_rephase_logical_ff=rephase_ff,additional_cb_rephase_members=len(phase_requests),hop_add=hop_add,hops={str(k):v for k,v in hops.items()},l9_add=l9_add,scope='Conditional price on exact nominal regional crossing table applied to v7 source. CB whole-port/phase fixes are required beyond nominal table; calendar phase offsets remain unqualified.')
(out/'actual_landing_paths.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:report[k]for k in('ports','lanes','cb_before','cb_after','cb_add','hop_add','l9_add')},sort_keys=True))
print('rephase relations',len(rephase),'whole-port pads',len(word_pads))
