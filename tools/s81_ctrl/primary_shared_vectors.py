#!/usr/bin/env python3
"""Minimum native final-add gate; A arithmetic/released W2 are separately owned."""
import argparse, pathlib, sys, numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hdc_golden import to_bf16, add

def main():
    p=argparse.ArgumentParser();p.add_argument('out');args=p.parse_args()
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(41)
    # Full rank1280values;24contexts cover4TP ranks and6serial invocations.
    prefix=rng.normal(0,2,(24,1280)).astype(np.float32)
    shared=to_bf16(rng.normal(0,1,(24,1280)).astype(np.float32))
    boundary=np.array([0x3f807fff,0x3f808000,0x3f818000,0xbf808000,
                      0x00800000,0x00010000,0x3f800000,0xbf800000],dtype=np.uint32).view(np.float32)
    prefix[:,0:8]=boundary
    shared[:,0:8]=np.array([0x3b800000,0,0,0,0x00800000,0,0xbf800000,0x3f800000],dtype=np.uint32).view(np.float32)
    expected=to_bf16(add(prefix,shared))
    for name,arr in [('prefix',prefix),('shared',shared),('expected',expected)]:
        words=arr.view(np.uint32).reshape(-1,16)
        with (out/(name+'.hex')).open('w') as f:
            for row in words:f.write(''.join(f'{int(v):08x}' for v in row[::-1])+'\n')
if __name__=='__main__':main()
