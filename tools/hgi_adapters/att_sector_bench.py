"""Exhaustive BF16 grid/fault and all raw FP8, using the independent golden table."""
import argparse
import random
import struct
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hdc_golden_v41 import E4M3

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    out=Path(ap.parse_args().out);out.mkdir(parents=True,exist_ok=True)
    table={struct.unpack('<I',struct.pack('<f',v))[0]:i for i,v in enumerate(E4M3) if np.isfinite(v)}
    def expect(data,tag,es):
        codes=mask=bad=0
        for i in range(32):
            bits=(data>>(8*i))&255 if es==0 else (data>>(16*(i%16)))&65535 if es==1 else (data>>(32*(i%8)))&0xffffffff
            fp=bits<<16 if es==1 else bits
            code=bits if es==0 else table.get(fp,0)
            active=es==0 or (es==1 and (tag&1)==i//16) or (es==2 and (tag&3)==i//8)
            codes|=code<<(8*i);mask|=int(active)<<i
            bad|=int(es!=0 and fp not in table and active)<<i
        return codes|(mask<<256)|(bad<<288)|((tag>>es)<<320)
    cases=[]
    for base in range(0,256,32):
        cases.append((sum((base+i)<<(8*i) for i in range(32)),base//32,0))
    for base in range(0,65536,16):
        cases.append((sum((base+i)<<(16*i) for i in range(16)),(base//16)%32,1))
    vals=list(table)+[0x7f800000,0xff800000,0x7fc00000,0x3f800001,0x43e08000]
    rng=random.Random(72);vals += [rng.getrandbits(32) for _ in range(1024)]
    for base in range(0,len(vals),8):
        w=(vals[base:base+8]+[0]*8)[:8]
        cases.append((sum(v<<(32*i) for i,v in enumerate(w)),base%32,2))
    (out/'input.mem').write_text(''.join(f'{d|(t<<256)|(e<<264):067x}\n' for d,t,e in cases))
    (out/'expected.mem').write_text(''.join(f'{expect(d,t,e):082x}\n' for d,t,e in cases))
    (out/'sizes.svh').write_text(f'localparam N={len(cases)};\n')
    print(f'{len(cases)} sectors: all 65536 BF16 bit patterns, all256 rawFP8, FP32 grid+fault/random')

if __name__=='__main__':main()
