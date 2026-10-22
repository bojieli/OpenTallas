"""Abstract one-S5-transition coupon; NOT production RTL equivalence or schedule proof."""
import hashlib,json

def check(mode=0):
    cases=errors=0
    for b0 in range(8):
      for f in range(8):
       for n in range(65):
        old=[10000+i for i in range(64)]
        carry=old[b0*8:b0*8+7]
        rot=[-1]*64
        for j in range(n):rot[(b0*8+f+j)%64]=20000+j
        nf,fn=divmod(f+n,8)
        for b in range(8):
          if (b-b0)%8>=nf:continue
          expected=[old[b*8+q] if b==b0 and q<f else rot[b*8+q] for q in range(8)]
          got=[carry[q] if b==b0 and q<(f+(mode==2)) and q<7 else rot[b*8+q] for q in range(8)]
          errors+=got!=expected
        updated=old[:]
        for j in range(n):updated[(b0*8+f+j)%64]=rot[(b0*8+f+j)%64]
        bn=(b0+nf+(mode==3))%8
        for q in range(fn):
          retain=(nf==0 and q<f) or (mode==1 and nf==8 and q<f)
          got=carry[q] if retain else rot[bn*8+q]
          errors+=got!=updated[((b0+nf)%8)*8+q]
        cases+=1
    return dict(cases=cases,mismatches=errors)

if __name__=='__main__':
    base=check()
    assert base['mismatches']==0,base
    mutants={str(m):check(m) for m in (1,2,3)}
    assert all(r['mismatches']>0 for r in mutants.values()),mutants
    print(json.dumps(dict(scope='abstract_one_S5_transition_NOT_RTL_equivalence',positive=base,
                         causal_mutants=mutants,source_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest()),sort_keys=True))
