from pathlib import Path
import sys,json,itertools,time
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/global_book_search');sys.path.insert(0,str(r/'code'))
from norm_global_publication import compose
routes=json.loads((r/'routes.json').read_text());vp=json.loads((r/'V_paths_candidate.json').read_text());pub=json.loads((r/'ffn_publication.json').read_text());slots=json.loads((r/'slots.json').read_text())
domains={};t0=time.time()
for sl,group in sorted(slots['current'].items()):
 rows=group['leaves'];base={x['leaf']:x['source_stage_offset']for x in rows};legal=[]
 for profile in itertools.product(range(5),repeat=5):
  times=[base[k]+4*profile[k]+f+z for k in range(5)for f in (0,20)for z in range(4)]
  if len(set(times))==40:legal.append(profile)
 ds=[]
 for profile in legal:
  events=[]
  for e in pub['events']:
   if e['slice']!=sl:continue
   q=dict(e);q['relative_XG_input_edge']+=4*(profile[e['leaf']]-e['candidate_k']);q['candidate_k']=profile[e['leaf']];events.append(q)
  sub=dict(pub,events=events);ffn=compose(sub,routes,vp,True)
  head=compose(dict(sub,events=[dict(e,header_index=e['global_beat']+128)for e in events if e['family']=='bf16']),routes,vp,True)
  if ffn['conflicts']or head['conflicts']:continue
  resources={('ffn',*x)for x in ffn['resource_slots']}|{('head',*x)for x in head['resource_slots']}
  ds.append(dict(profile=profile,resources=resources))
 domains[sl]=ds;print('GLOBAL_DOMAIN',sl,len(legal),len(ds),flush=True)
# Exact finite pair compatibility, followed by MRV backtracking.
compat={};direct_unsat=[];names=list(domains)
for ai,a in enumerate(names):
 for b in names[ai+1:]:
  matrix=[]
  for x in domains[a]:matrix.append({j for j,y in enumerate(domains[b])if x['resources'].isdisjoint(y['resources'])})
  compat[a,b]=matrix
  if not any(matrix):direct_unsat.append(dict(a=a,b=b,a_profiles=len(domains[a]),b_profiles=len(domains[b])))
nodes=0

def allowed(a,i,b):
 if (a,b)in compat:return compat[a,b][i]
 return {j for j,s in enumerate(compat[b,a])if i in s}

def search(left,chosen):
 global nodes
 nodes+=1
 if not left:return chosen
 a=min(left,key=lambda x:len(left[x]))
 for i in left[a]:
  other={b:(vals&allowed(a,i,b))for b,vals in left.items()if b!=a}
  if all(other.values()):
   answer=search(other,dict(chosen,**{a:i}))
   if answer is not None:return answer
 return None
answer=None if direct_unsat else search({s:set(range(len(ds)))for s,ds in domains.items()},{})
result=dict(status='UNSAT_FIXED_COMPONENT_ROOTS_K0TO4'if answer is None else'SAT_FIXED_COMPONENT_ROOTS_K0TO4',domain_sizes={s:len(ds)for s,ds in domains.items()},direct_pair_unsat=direct_unsat,search_nodes=nodes,seconds=time.time()-t0,source_top_sha256=routes['source_top_sha256'],profile={s:list(domains[s][i]['profile'])for s,i in(answer or{}).items()},scope='same fixed component RSTD dates, all K0..4 profiles preserving BOTH localfamilies, both globalFFN and HEAD books; no per-leafproducer/physical/inputauthority',canonical_adopted=False)
(r/'result.json').write_text(json.dumps(result,indent=1)+'\n');print('GLOBAL_SOLVER',result['status'],'directunsat',direct_unsat,'nodes',nodes,flush=True)
