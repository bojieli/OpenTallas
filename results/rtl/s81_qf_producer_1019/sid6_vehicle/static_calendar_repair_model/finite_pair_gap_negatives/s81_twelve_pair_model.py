import sys,json,random,collections,time,math
from pathlib import Path
root=Path('/home/ubuntu/wt/codex-s81-qf-producer-source-1019');sys.path[:0]=[str(root/'tools/s81_dv'),str(root/'tools/s81')];import frame_return_plan as P
P.C.fadd=lambda a,b:((a,b),0)
b=root/'results/rtl/s81_qf_producer_1019/sid6_vehicle';c=json.load(open(b/'retained_xs_program_model/contract.json'));rng=random.Random(855618);res=[]
for ix,p in enumerate(c['plans'][:2]):
 m=p['master'].replace('_MX','').replace('_l4','');t=json.load(open('/home/ubuntu/wt/tok-s81-vpx/results/arch/s81_dv_1016/frame/return_plan/topology_'+m+'.json'));em=p['emission'];qs=[int(k) for k in em['off']];offset=[1434,1430][ix];vals={r:[(r,s) for s in range(3)] for r in range(6)};pool={};counts=collections.Counter();start=time.time();best=99
 def emit(q,s):return em['e0']+em['last_beat'][s]+em['off'][str(q)]+em['seg_extra'][s]
 def evaluate(assign):
  aa={q:[v] for q,v in zip(qs,assign) if v is not None};rep,ret=P.compose(t,P.leaves_for(aa,emit,vals));nf=P.nfaults(rep);score=nf*100+len(ret)
  if not nf:
   sig=tuple(w[0]+offset for w in ret)
   if sig not in pool:pool[sig]=dict(assign=[list(v) if v else None for v in assign],ret=[[w[0]+offset,w[1],w[2],w[3]] for w in ret])
   counts['legal_evaluations']+=1;counts['words'+str(len(ret))]+=1
  counts['evaluations']+=1
  return score
 original={x['pair']:(x['super_row'],x['seg'],3) for x in p['placement']};initial=[original.get(q) for q in qs]
 for restart in range(64):
  cur=initial[:] if restart<32 else [(r,s,3) for r in range(3) for s in range(3)]+[None]*3
  if restart>=32:rng.shuffle(cur)
  score=evaluate(cur)
  for step in range(512):
   trial=cur[:];i,j=rng.sample(range(12),2);trial[i],trial[j]=trial[j],trial[i];new=evaluate(trial);temp=8*(1-step/512)+.2
   if new<=score or rng.random()<math.exp(-(new-score)/temp):cur,score=trial,new
  best=min(best,score)
 print(p['frame'],'best',best,'pool',len(pool),'counts',dict(counts),'sec',time.time()-start,flush=True)
 res.append(dict(frame=p['frame'],pairs=qs,offset=offset,counts=dict(counts),best_score=best,unique_calendars=len(pool),candidates=list(pool.values()),seconds=time.time()-start))
Path('/tmp/s81_twelve_pair_result.json').write_text(json.dumps(res,indent=2)+'\n')
