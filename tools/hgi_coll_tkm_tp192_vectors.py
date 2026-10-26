#!/usr/bin/env python3
"""Independent NumPy lexsort oracle, full192-source SELECT/CANDIDATE and signed-zero/rank alias edge."""
import argparse,json
from pathlib import Path
import numpy as np
from hgi_coll_tkm_vectors import write_case,bf16,owned_ids

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 rng=np.random.default_rng(1921016);g=192;cases=[]
 ids=[owned_ids(q,1<<20,g,512,rng) for q in range(g)]
 vals=[bf16(rng.normal(0,1,512)) for _ in range(g)]
 cases.append(write_case(a.out,'syn_sel',g,512,512,191,vals,ids,True))
 ci=[np.arange(q,131072,g,dtype=np.uint32) for q in range(g)]
 cv=[bf16(rng.normal(0,1,len(x))) for x in ci]
 cases.append(write_case(a.out,'syn_cand',g,683,2048,191,cv,ci,True))
 vals=[np.full(8,-np.inf,np.float32) for _ in range(g)];ids=[np.arange(q*8,q*8+8,dtype=np.uint32)+1000 for q in range(g)]
 vals[0][0]=np.float32(-0.0);vals[128][0]=np.float32(0.0);ids[0][0]=ids[128][0]=5
 cases.append(write_case(a.out,'rank128_zeros',g,8,1,191,vals,ids,True))
 assert (a.out/'rank128_zeros/r.hex').read_text().splitlines()[0]=='80000000'
 (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');print('TKM_TP192_VECTORS',[(x['name'],x['nout']) for x in cases])
if __name__=='__main__':main()
