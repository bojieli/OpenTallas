#!/usr/bin/env python3
"""Released HC vectors -> native resident ROM, SRAM staging and exact projection.

Input is hcx_real.py's two-record full-shape directory, already asserted against
the real 1M snapshot. No benchmark golden values are injected into the datapath.
Each ROM file is the physical via mask of one real 4096x72 macro (64 payload).
"""
import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G

@lru_cache(maxsize=1)
def load(src):
    vm={int(s[:8],16):int(s[8:],16) for s in (src/'hu_vmi.mem').read_text().splitlines()}
    rom={int(s[:10],16):int(s[10:],16) for s in (src/'hu_hbm.mem').read_text().splitlines()}
    eps=int(re.search(r"NEPS = 32'h([0-9A-Fa-f]+)",(src/'hu_sizes.svh').read_text()).group(1),16)
    return vm,rom,eps,(src/'hu_case.mem').read_text().splitlines()

def build(src,out,row):
    G.set_arith('chunk8')
    out.mkdir(parents=True,exist_ok=True)
    vm,rom,eps,cases=load(src)
    masks=[[[[0]*512 for _ in range(2)] for _ in range(4)] for _ in range(8)]
    wants=[]
    for block,line in enumerate(cases):
        d=int(line[56:],16)
        a=(d>>128)&((1<<256)-1);b=(d>>384)&((1<<256)-1)
        ab=(a>>8)&((1<<40)-1);bs=((b>>8)&((1<<40)-1))>>5
        x=np.array([vm[ab+i] for i in range(20480)],dtype=np.uint32)
        assert np.all((x&0xffff)==0)
        fn=np.empty(20480,dtype=np.uint32)
        for bank in range(8):
            for run in range(80):
                words=[]
                for lane in range(32):
                    sec=bs+4+(8*row+bank)*320+run*4+lane//8
                    w=(rom[sec]>>(32*(lane%8)))&0xffffffff
                    fn[8*(run*32+lane)+bank]=w
                    words.append(w)
                addr=block*80+run
                for m in range(4):
                    payload=sum(words[8*m+j]<<(32*j) for j in range(8))
                    for bit in range(256):
                        if payload>>bit&1:masks[bank][m][addr>>12][(addr&4095)//8]|=1<<(bit*8+addr%8)
        xf=x.view(np.float32);ff=fn.view(np.float32)
        r=G.rsqrt(G.add(G.div(G.split_sum(G.mul(xf,xf),G.HC_SS_SPLIT),np.float32(20480)),G.from_bits(eps)))
        want=np.asarray(G.mul(G.matvec_c(ff[None,:],xf,G.HC_SPLIT,cls='he'),r),np.float32).view(np.uint32)[0]
        wants.append(int(want))
        with (out/f'x{block}.mem').open('w') as f:
            for run in range(80):
                word=sum(int(x[run*256+i]>>16)<<(16*i) for i in range(256))
                f.write(f'{word:01024x}\n')
    for bank in range(8):
        for m in range(4):
            for pg in range(2):
                (out/f'hcx_r0_b{bank}_l{m}_p{pg}.viamap.hex').write_text(''.join(f'{r:0532x}\n' for r in masks[bank][m][pg]))
    (out/'expected.mem').write_text(''.join(f'{w:08x}\n' for w in wants))
    (out/'eps.mem').write_text(f'{eps:08x}\n')
    (out/'metadata.json').write_text(json.dumps(dict(source=str(src),row=row,outputs=wants,shape=[2,20480],macros=64,payload_bits_per_macro=256),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--src',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--row',type=int,required=True)
    a=p.parse_args()
    if not 0<=a.row<24:p.error('projection row must be 0..23')
    build(a.src,a.out,a.row)
