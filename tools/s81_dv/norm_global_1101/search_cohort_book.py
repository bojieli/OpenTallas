from pathlib import Path
import sys,json,random,time
old=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/global_book_search')
exec((old/'solve_global_profiles.py').read_text().split('# Exact finite pair compatibility')[0])
out=old.parent/'global_cohort_search_v1';out.mkdir(exist_ok=False);(out/'.keep').write_text('critical source-relative publicationcohort search\n');t0=time.time()
sys.path.insert(0,str(old.parent/'code'));from layer_prog import norm_q as N
book=json.loads((old/'ffn_norm_candidate.json').read_text());net=json.loads((old/'NX_component.json').read_text());names=list(domains);sid=lambda s:2*int(s[4])+(s[-1]=='N');ids={s:sid(s)for s in names}
# Per-profile exact forbidden pair phase differences for every shared resource.
indexed={s:[]for s in names}
for s in names:
 for p in domains[s]:
  by={}
  for slot in p['resources']:by.setdefault(slot[:-1],[]).append(slot[-1])
  indexed[s].append(by)
forbid={};OFF=2048
for ai,a in enumerate(names):
 for b in names[ai+1:]:
  matrix=[]
  for x in indexed[a]:
   row=[]
   for y in indexed[b]:
    diff={ta-tb for key in x.keys()&y.keys()for ta in x[key]for tb in y[key]};bits=0
    for d in diff:bits|=1<<(d+OFF)
    row.append(bits)
   matrix.append(row)
  forbid[a,b]=matrix
adds=[n for n in range(1,N.NVP)if N.isadd(n)]
def child(n):
 while n<N.NVP and not N.isadd(n):n*=2
 return n
children={n:(child(2*n),child(2*n+1))for n in adds};INF=10**12

def root(dl):
 vd=[INF]*(2*N.NVP);issued=[INF]*N.NVP
 for b,edge in dl.items():
  for k in range(5):vd[N.NVP+b+k]=edge+2
 prev=None;c=min(dl.values())
 for _ in range(4096):
  ready=None
  for n in adds:
   a,b=children[n]
   if vd[a]<=c and vd[b]<=c and issued[n]>c:ready=n;break
  if prev is not None and issued[prev]>c:
   issued[prev]=c+1;wb=c+1+N.LAV;vd[prev]=wb+1
   if prev==1:return wb
  prev=ready;c+=1
 raise ValueError('native controller model did not finish')
anchors={s:next(c['partial_cohort_offset_excluding_common_local_age']for c in book['commands']if c['slice']==s and c['kind']=='NORMR')for s in names}
baseDl={ids[s]:{}for s in names}
for s in names:baseDl[ids[s]][5*ids[s]]=anchors[s]+7
for e in book['nx_events']:baseDl[ids[e['destination']]][5*ids[e['origin']]]=e['relative_landing_edge']+13
measured={int(s):v for s,v in net['root_writeback_edges'].items()};assert {s:root(d)for s,d in baseDl.items()}==measured
print('FAST_PRIORITY_MODEL_MATCHES_ACTUAL16_ROOT_DATES',flush=True)
rowby={x['tix']:x for x in book['rows']};cmd={s:[(rowby[c['template']]['eng'],c['issue'])for c in book['commands']if c['slice']==s and c['kind']=='NORMR']for s in names};go={(rowby[c['template']]['eng'],c['issue'])for c in book['commands']if c['kind']=='XFIN_GO'};nx={s:[(e['slice'],e['port'],e['relative_output_edge'])for e in book['nx_events']if e['origin']==s]for s in names};sidnames=sorted(names,key=ids.get)

def legalize(suggest):
 used=set(go);nxused=set();shifts={}
 for s in sidnames:
  for d in range(suggest.get(s,0),suggest.get(s,0)+129):
   a={(eng,e+d)for eng,e in cmd[s]};b={(sl,p,e+d)for sl,p,e in nx[s]}
   if not a&used and not b&nxused:break
  else:return None
  shifts[s]=d;used|=a;nxused|=b
 return shifts
current={s:next(i for i,p in enumerate(domains[s])if tuple(p['profile'])==tuple(slots['both_families_per_slice_k0to4'][s]['profile']))for s in names}
nodes=0

def solve(delta):
 compatible={}
 for (a,b),m in forbid.items():
  bit=1<<(delta[b]-delta[a]+OFF);mat=[{j for j,v in enumerate(row)if not(v&bit)}for row in m]
  if not any(mat):return None,False
  compatible[a,b]=mat
 fixed=all(current[b]in m[current[a]]for(a,b),m in compatible.items())
 if fixed:return dict(current),True
 def allowed(a,i,b):
  if(a,b)in compatible:return compatible[a,b][i]
  return {j for j,v in enumerate(compatible[b,a])if i in v}
 def visit(left,chosen):
  nonlocal_search_counter[0]+=1
  if nonlocal_search_counter[0]>50000:return None
  if not left:return chosen
  a=min(left,key=lambda s:len(left[s]));order=sorted(left[a],key=lambda i:i!=current[a])
  for i in order:
   rem={b:values&allowed(a,i,b)for b,values in left.items()if b!=a}
   if all(rem.values()):
    x=visit(rem,dict(chosen,**{a:i}))
    if x is not None:return x
  return None
 nonlocal_search_counter=[0];answer=visit({s:set(range(len(ds)))for s,ds in domains.items()},{})
 return answer,False
rng=random.Random(1101);suggestions=[{}]
for step in [8,16,24,32,48,64]:
 for reverse in [False,True]:suggestions.append({s:step*(15-ids[s]if reverse else ids[s])for s in names})
for delay in [16,32,48,64,96,128,192,256,384,512]:
 for s in sidnames:suggestions.append({s:delay})
for _ in range(1000):suggestions.append({s:rng.randrange(0,513,8)for s in names})
trials=[];seen_configs=set();winner=None
for q,suggest in enumerate(suggestions):
 shift=legalize(suggest)
 if shift is None:continue
 signature=tuple(shift[s]for s in names)
 if signature in seen_configs:continue
 seen_configs.add(signature);roots={dest:root({b:e+shift[next(s for s in names if ids[s]==b//5)]for b,e in dl.items()})for dest,dl in baseDl.items()};delta={s:roots[ids[s]]-measured[ids[s]]for s in names};answer,same=solve(delta)
 trial=dict(trial=q,max_cohort_shift=max(shift.values()),root_spread=max(roots.values())-min(roots.values()),same_K=same,SAT=answer is not None);trials.append(trial)
 if q%25==0:print('COHORT_SEARCH',q,len(trials),trial,'seconds',round(time.time()-t0,1),flush=True)
 if answer is not None:
  winner=dict(**trial,cohort_shifts=shift,root_writeback=roots,RSTD_after_root=82,K_profiles={s:list(domains[s][i]['profile'])for s,i in answer.items()},native_last_issue_delta=max(e+d for s,d in shift.items()for eng,e in cmd[s])-book['last_issue'],NX_latest_landing_delta=max(e['relative_landing_edge']+shift[e['origin']]for e in book['nx_events'])-book['relative_NX_last_landing'],latest_RSTD_delta=max(roots.values())-max(measured.values()));break
result=dict(status='FOUND_SOURCE_RELATIVE_COHORT_CANDIDATE'if winner else'NO_CANDIDATE_IN_BOUNDED_SEARCH',winner=winner,trials=trials,seconds=time.time()-t0,controller_checked_against_actual16_component_roots=True,source_top_sha256=routes['source_top_sha256'],unknown_per_leaf_producer_epochs=True,actual104_56_source_values_qualified=False,physical_phase_qualified=False,HOST_START_authority=False,canonical_adopted=False)
(out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print('COHORT_SEARCH_RESULT',result['status'],winner,'seconds',result['seconds'],flush=True)
