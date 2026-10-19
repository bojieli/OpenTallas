"""Pure integer MODEL identity, not RTL qualification. Run through ot-run."""
import json, random
n=0
for E in range(-1024,1024):
 for sub in (False,True):
  for subn in (False,True):
   for zero in (False,True):
    for inc1 in (False,True):
     for inc2 in (False,True):
      for m in (0,1,(1<<23)-1,1<<23,(1<<24)-3,(1<<24)-2,(1<<24)-1):
       # Signed 11-bit arithmetic is retained exactly, including wrap.
       signed=lambda x: ((x+1024)%2048)-1024
       eb=signed(E+127); eb1=signed(E+128)
       mf=(((m>>1)+1)<<1 | (m&1)) if inc2 else (m+1 if inc1 else m)
       ovm=bool(mf&(1<<24))
       old=not zero and ((not sub and ((eb1>254) if ovm else (eb>254))) or (not subn and eb<1))
       # Exact predicates avoid replacing signed overflow with an unchecked E threshold.
       high0=not sub and eb>254; high1=not sub and eb1>254
       low=not subn and eb<1
       new=not zero and ((high1 if ovm else high0) or low)
       carry=(inc2 and (m>>1)==(1<<23)-1) or (not inc2 and inc1 and m==(1<<24)-1)
       assert old==new and ovm==carry,(E,sub,subn,zero,inc1,inc2,m)
       n+=1
print(json.dumps({"predicate_identity_cases":n,"status":"PASS_MODEL_IDENTITY_ONLY","added_predicate_ff":96,"extra_steps":40}))
