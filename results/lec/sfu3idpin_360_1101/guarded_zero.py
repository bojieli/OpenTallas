"""Exact one-bit LD3K reachability coupon; no assumption of zero power-up.
State: sharedp0, goldp1/goldp2, goldq01/goldq2, goldoff0/1,
       gateq01, gateoff0/1, reset-validlp/lq, sharedbankp/bankq.
All data and bank flops start arbitrary; matched initial data equal across sides.
"""
import itertools,json

def step(s, i, mutant=None):
 p0,p1,p2,q01,q2,o0,o1,gq01,go0,go1,lp,lq,bp,bq=s
 rst,ld,data,bank=i
 z=1 if mutant=='load_one' else 0
 nq01=(p0^p1) if (lp or mutant=='unguarded_q01') else q01
 ngq01=p0 if (lp or mutant=='unguarded_q01') else gq01
 no0=(q01^q2) if lq and not bq else o0
 no1=(q01^q2) if lq and bq else o1
 ngo0=gq01 if lq and not bq else go0
 ngo1=gq01 if lq and bq else go1
 return(data if ld else p0,z if ld else p1,0 if ld else p2,
        nq01,p2 if lp else q2,no0,no1,ngq01,ngo0,ngo1,
        ld if rst else 0,lp if rst else 0,bank if ld else bp,bp if lp else bq)

def initial():
 for p0,p1,p2,q01,q2,o0,o1,bp,bq in itertools.product(range(2),repeat=9):
  yield(p0,p1,p2,q01,q2,o0,o1,q01,o0,o1,0,0,bp,bq)

def run(mutant=None):
 seen=set(initial());todo=list(seen);edges=0
 for s in todo:
  for i in itertools.product(range(2),repeat=4):
   t=step(s,i,mutant);edges+=1
   # Retain each internal compare point and both off-bank outputs.
   if (t[3],t[5],t[6])!=(t[7],t[8],t[9]):
    return dict(pass_=False,mutant=mutant,states=len(seen),edges=edges,from_state=s,inputs=i,to_state=t)
   if mutant is None:
    assert not t[10] or (t[1]==0 and t[2]==0)
    assert not t[11] or t[4]==0
   if t not in seen:seen.add(t);todo.append(t)
 return dict(pass_=True,mutant=mutant,states=len(seen),edges=edges)

if __name__=='__main__':
 out=dict(base=run(),wrong_zero_mutant=run('load_one'),missing_valid_mutant=run('unguarded_q01'))
 assert out['base']['pass_'] and not out['wrong_zero_mutant']['pass_'] and not out['missing_valid_mutant']['pass_']
 # Counterexample to an unrestricted combinational induction step: the state
 # lp=1,p1=1 is unreachable after reset, but is free in the existing cut.
 out['free_cut_counterexample']=dict(lp=1,p1=1,p0=0,gold_q01_next=1,gate_q01_next=0)
 print(json.dumps(out,indent=2))
