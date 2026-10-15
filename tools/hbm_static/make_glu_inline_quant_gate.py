#!/usr/bin/env python3
"""Quant oracle derives from canonical expected GLU; DUT is fed ONLY G/U/route."""
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import hdc_golden_v41 as V
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
for name in ['gate','up','route','gold']:(out/(name+'.hex')).write_bytes((source/(name+'.hex')).read_bytes())
gold=np.array([int(x,16) for x in (source/'gold.hex').read_text().splitlines()],dtype=np.uint32)
x=G.from_bits(gold);q,exps=V.quant_fp8(x);dq=G.bits(V.qdq_fp8(x))>>16
lookup={float(V.E4M3[c]):c for c in range(127)}
codes=[lookup[float(abs(v))]|(int(np.signbit(v))<<7) for v in q]
packets=[sum(codes[b*32+i]<<(i*8) for i in range(32))|((int(exps[b])&1023)<<256) for b in range(96)]
(out/'quant.hex').write_text(''.join(f'{p:067x}\n' for p in packets))
(out/'dequant.hex').write_text(''.join(f'{sum(int(dq[b*32+i])<<(i*16) for i in range(32)):0128x}\n' for b in range(96)))
beats=[]
for a in range(24):
 g,t=divmod(a,8);fragment=sum(packets[(4*g+j)*8+t]<<(266*j) for j in range(4))
 for group in range(13):beats.append(fragment if group==0 else 0)
(out/'xwrite.hex').write_text(''.join(f'{b:0512x}\n' for b in beats))
(out/'manifest.json').write_text(json.dumps(dict(actual_GLU_inputs='canonicalG/U/route only; actualRTL computesall3072BF16outputs',expected_only='canonicalGLUgold→V.quant_fp8/V.qdq_fp8; never fed toDUT',quant_packets=96,code_bytes=3072,exponents=96,dequant_BF16_words=3072,SM_pins='NC8SUB4 fmt1,K3072,G3,address0..23,13groups;col0real;7contextsOPEN',fragment_mapping='b=(4*g+j)*8+t;packet={signedexp10,codes256littleendian};col0bitsj*266',SM_beats=312,full_P8_qualified=False),indent=2)+'\n')
