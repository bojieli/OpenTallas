#!/usr/bin/env python3
"""G24 independent list-based golden: slot-major OWNED R, D[0:2]."""
import sys
from pathlib import Path
import numpy as np


def golden(ids, B, G, die, batch=0):
    # Build each rank's list explicitly; derive the inverse permutation by list lookup.
    buckets = [[] for _ in range(G)]
    locations = [[] for _ in range(G)]
    for i, row in enumerate(ids):
        block, offset = divmod(int(row), B)
        local_block, owner = divmod(block, G)
        buckets[owner].append(i)
        locations[owner].append(local_block * B + offset)
    M = max(map(len, buckets))
    R = [0] * len(ids)
    for owner, entries in enumerate(buckets):
        for slot, index in enumerate(entries):
            R[index] = slot * G + owner
    O = locations[die % G] + [0] * (M - len(locations[die % G]))
    return np.array(O, dtype=np.uint32), np.array(R, dtype=np.uint32), M, (M + max(batch, 1)-1)//max(batch,1)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    specs = [(8,96,0,512,c) for c in (0,1,2,3,17,255)] + [
        (8,96,150,2048,2),(8,8,13,512,2),(16,4,2,300,3),(8,1,5,7,2),
        (1,2,1,64,2),(128,96,95,512,7),(8,96,3,2048,2),(8,96,95,2048,255),
        (8,1,0,2048,2),(8,96,3,512,2)]
    lines=[]
    for c,(B,G,die,K,batch) in enumerate(specs):
        ids=rng.choice(1<<20,size=K,replace=False).astype(np.uint32)
        if c==1: ids=np.sort(ids)
        if c==12: ids=np.array([(i//B)*(B*G)+3*B+i%B for i in range(K)], dtype=np.uint32)
        if c==13: ids=np.array([(i//B)*(B*G)+3*B+i%B for i in range(K)], dtype=np.uint32)
        fault=int(c==len(specs)-1)
        if fault:
            ids[100]=1<<20; O,R,M,ND=np.zeros(1,np.uint32),np.zeros(1,np.uint32),0,0
        else: O,R,M,ND=golden(ids,B,G,die,batch)
        for key,values in (('a',ids),('o',O),('r',R)):
            np.savetxt(out/f'case_{c}.{key}.mem',values,fmt='%08x')
        lines.append(f'{B} {G} {die} {K} {fault} {M} {len(O)} {batch} {ND}')
    (out/'cases.txt').write_text(f'{len(lines)}\n'+'\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__': main()
