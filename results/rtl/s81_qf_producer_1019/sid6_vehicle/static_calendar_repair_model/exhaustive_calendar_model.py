import sys,json,random,collections,time,itertools
from pathlib import Path
root=Path('/home/ubuntu/wt/codex-s81-qf-producer-source-1019');sys.path[:0]=[str(root/'tools/s81_dv'),str(root/'tools/s81')];import frame_return_plan as P
# Symbolic operands record association only; never generate arithmetic data or stimulus.
P.C.fadd=lambda a,b:((a,b),0)
b=root/'results/rtl/s81_qf_producer_1019/sid6_vehicle';c=json.load(open(b/'retained_xs_program_model/contract.json'));a=json.load(open(b/'fullsix_diagnostic_result/source_interval_audit.json'));rng=random.Random(757);res=[]
for ix,p in enumerate(c['plans'][:2]):
 m=p['master'].replace('_MX','').replace('_l4','');t=json.load(open('/home/ubuntu/wt/tok-s81-vpx/results/arch/s81_dv_1016/frame/return_plan/topology_'+m+'.json'));actual={(r['semantic_row'],r['lo'],r['k']):r for r in a['actual_return_intervals'] if r['semantic_row'] in p['rows']};offset={actual[(p['rows'][((tag>>13)&65535)&16383],(tag>>8)&31,(tag>>5)&7)]['t']-tm for tm,tag,d,e in p['return_model']}.pop();em=p['emission'];slots=[(R,s,3) for R in range(3) for s in range(3)];candidates={};counts=collections.Counter();start=time.time()
 def emit(q,s):return em['e0']+em['last_beat'][s]+em['off'][str(q)]+em['seg_extra'][s]
 vals={r:[(r,s) for s in range(3)] for r in range(6)}
 def permutations():
  for zero in itertools.combinations(range(9),3):
   rest=[i for i in range(9) if i not in zero]
   for one in itertools.permutations(rest,3):
    last=[i for i in rest if i not in one]
    for two in itertools.permutations(last):
     perm=[None]*9
     for R in range(3):perm[zero[R]]=(R,0,3);perm[one[R]]=(R,1,3);perm[two[R]]=(R,2,3)
     yield perm
 for perm in permutations():
  assign={q:[v] for q,v in zip(p['pairs'],perm)};rep,ret=P.compose(t,P.leaves_for(assign,emit,vals));faults=P.nfaults(rep);counts['samples']+=1
  if faults:continue
  counts['local_legal']+=1;counts['words'+str(len(ret))]+=1
  signature=tuple(w[0]+offset for w in ret)
  if signature not in candidates:candidates[signature]=dict(assign=perm,ret=[[w[0]+offset,w[1],w[2],w[3]] for w in ret])
 res.append(dict(frame=p['frame'],counts=dict(counts),unique_calendars=len(candidates),candidates=list(candidates.values()),seconds=time.time()-start))
 print(p['frame'],dict(counts),'unique',len(candidates),'sec',time.time()-start,flush=True)
Path('/tmp/s81_calendar_exhaustive_result.json').write_text(json.dumps(res,indent=2)+'\n')
