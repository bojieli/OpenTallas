#!/usr/bin/env python3
"""Actual parent calendar coupons; one full64-seat element,192-rank key width.
Not a full2048-seat chain throughput or die qualification.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_coll_tkm_vectors import write_case, bf16
p=argparse.ArgumentParser(__doc__)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();rng=np.random.default_rng(1020);cases=[]
for name,g,n in [('full192_random',192,8),('group4_long',4,128)]:
    vals=[bf16(rng.normal(size=n)) for _ in range(g)]
    ids=[np.arange(q*n,(q+1)*n,dtype=np.uint32)+1000 for q in range(g)]
    cases.append(write_case(a.out,name,g,n,64,191,vals,ids,True))
g,n=192,8
vals=[np.full(n,-np.inf,np.float32) for _ in range(g)]
ids=[np.arange(q*n,(q+1)*n,dtype=np.uint32)+1000 for q in range(g)]
vals[0][0]=np.float32(-0.0);vals[128][0]=np.float32(0.0)
ids[0][0]=ids[128][0]=5
cases.append(write_case(a.out,'rank128_zero64',g,n,64,191,vals,ids,True))
(a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
print('E86_PARENT_PROTOCOL_VECTORS',[(c['name'],c['nout']) for c in cases])
