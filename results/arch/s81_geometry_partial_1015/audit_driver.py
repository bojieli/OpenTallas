import collections,gzip,hashlib,json,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tools/s81'))
import group_placement_opt as G
p=json.loads(G.read(R/'canonical_partial_finalized.json.gz'))
p['port_aliases']=json.loads((R/'port_aliases_screen7.json').read_text())
cap=json.loads((R/'capacity.json').read_text())
for h in cap['hcp_homes']:
 p['insts'].append([h['name'],h['master'],*h['at_um'],h['outline']['w'],h['outline']['h'],'R0','unbound_supplemental_reservation','hcp_keepout'])
print('MODEL_START',len(p['insts']),len(p['buses']),flush=True)
m=G.Model(p,[G.read(R/'partial_exact_pins.lef.gz')],p['die'])
print('MODEL_READY',len(m.edges),len(m.missing),flush=True)
baseline=m.metrics(m.edges)
classes={};long=[];badalign=[]
for e in m.edges:
 cls=e['cls'];rec=classes.setdefault(cls,dict(bundles=0,bits=0,sum_bit_um=0,max_um=0))
 mm=m.metrics([e]);route=mm['top20_routes'][0]
 if mm['max_um']>500:long.append(route)
 if mm['alignment_failures']:badalign.append(route)
 rec['bundles']+=1;rec['bits']+=e['bits'];rec['sum_bit_um']+=mm['sum_bit_um'];rec['max_um']=max(rec['max_um'],mm['max_um'])
groups={r[0]:[r[0]] for r in p['insts'] if r[7]=='hub'}
print('SEARCH_START',list(groups),flush=True)
candidates,blocked,tradeoffs=G.search(m,groups,172.8,86.4)
missing_masters=collections.Counter()
for e in m.missing:
 for n,_ in e['ends']:missing_masters[m.insts[n].master]+=1
crossings=[dict(root=k,logical_half=f['logical_half'],physical_half=f['half'],x=f['x'],y=f['y']) for k,f in p['frames'].items() if f['half']!=f['logical_half']]
report=dict(scope=p['scope'],source_pins={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in R.iterdir() if q.name in ['canonical_partial_finalized.json.gz','partial_exact_pins.lef.gz','capacity.json','port_aliases_screen7.json','port_aliases_screen7.sources.json','audit.py']},
 actual_instances=len(p['insts'])-6,supplemental_hcp_obstacles=cap['hcp_homes'],resolved_edges=len(m.edges),missing_edges=m.missing,missing_master_incidence=dict(missing_masters),baseline=baseline,
 by_class=classes,top20_long_hops=sorted(long,key=lambda e:e['max_um'],reverse=True)[:20],alignment_failure_routes=badalign,groups=groups,groups_without_data_incidence=[n for n in groups if not any(any(nn==n for nn,_ in e['ends']) for e in m.edges)],candidates=candidates,groups_blocked=blocked,geometric_tradeoffs=tradeoffs,cross_half_frames=crossings,
 limitations=['Partial canonical generated graph; missing return routes and hubs prevent release conclusions','Missing incident pins block affected group optimization','No traffic/critical-path weighting or routed congestion/timing proof','HCP keepouts supplied explicitly from canonical capacity; no HCP native edge claims'])
(R/'report.json').write_text(json.dumps(report,indent=1)+'\n')
print('REPORT',json.dumps(dict(edges=len(m.edges),missing=len(m.missing),candidates=len(candidates),blocked=blocked,total_bit_um=baseline['sum_bit_um'],crossings=len(crossings))),flush=True)
