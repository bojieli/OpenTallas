"""Independent golden codes/scales, exact BF16 values and chunk8 sums."""
import argparse
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as G
from hgi_sim import lib as A

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--fp8',action='store_true')
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261010)
    blocks=[]
    x=np.zeros(32,dtype=np.float32);x[:2]=[5.25,2.625];blocks.append(x)
    for scale in G.E4M3[1:127]:
        code=np.array([6,3,2,1.5,1,.5,0,-6,-3,-2,-1.5,-1,-.5,0,4,-4],dtype=np.float32)
        blocks.append(np.tile(code*scale,2).astype(np.float32))
    for exp in range(-10,13):
        for _ in range(8):blocks.append((rng.standard_normal(32)*2.**exp).astype(np.float32))
    ins=[];ex=[];sums=[]
    scale_codes={float(v):i for i,v in enumerate(G.E4M3[:127])}
    for x in blocks:
        y=(G.qdq_fp8(x) if args.fp8 else G.qdq_fp4_e4m3(x)).astype(np.float32)
        if args.fp8:
            q,e=G.quant_fp8(x);packed=(int(e[0])+127)<<256
            for i,z in enumerate(q):
                c=next(j for j,t in enumerate(G.E4M3) if t==z and bool(np.signbit(t))==bool(np.signbit(z)))
                packed|=c<<(8*i)
        else:
            packed=1<<264
            for b in range(2):
                t=x[16*b:16*b+16];amax=max(float(np.max(np.abs(t))),float(G.FP4_AMAX_FLOOR_E4M3))
                s=float(min(G._e4m3_round(amax/6),448))
                packed|=scale_codes[s]<<(128+8*b)
                for j,z in enumerate(t):
                    c=0
                    for i,m in enumerate(G.E2M1_MIDPOINTS):
                        if abs(float(z))>m*s or (abs(float(z))==m*s and (i+1)%2==0):c=i+1
                    sign=int(np.signbit(z) and z!=0)
                    packed|=(c|(sign<<3))<<(4*(16*b+j))
        xin=sum(int(v)<<(32*i) for i,v in enumerate(x.view(np.uint32)))
        yout=sum((int(v)>>16)<<(16*i) for i,v in enumerate(y.view(np.uint32)))
        ins.append(f'{xin:0256x}\n');ex.append(f'{packed|(yout<<265):0195x}\n')
        sums.append(f'{int(A.csum(y[:8]).view(np.uint32)):08x}\n')
    (out/'input.mem').write_text(''.join(ins));(out/'expected.mem').write_text(''.join(ex))
    (out/'sum.mem').write_text(''.join(sums));(out/'sizes.svh').write_text(f'localparam N={len(blocks)};\n')
    print(f'{len(blocks)} blocks; counterexample5.25/2.625, all126 positiveE4M3scales, seededmagnitude sweep; golden chunk8')

if __name__=='__main__':main()
