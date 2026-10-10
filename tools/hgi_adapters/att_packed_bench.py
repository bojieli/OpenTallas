"""Minimum H1 D64 packed consumer: real QK/PV and three-job merge.
Logical sparse packet storage is separate from ccac3e341's actual macro proof.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
from att_unit_bench import pack
from hgi_sim import lib as A

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
D, T, stride = 64, 130, 96
Q, P, SCORE, O = 1167488, 1172480, 1168000, 1174848
group = (1 << 264) | (0x36 << 136) | (0x36 << 128) | 7 | (5 << 4)
fp8group = (127 << 256) | sum(0x38 << (8*i) for i in range(32))
rows = np.zeros((T,D), np.float32); rows[0] = 1
rows[1:, [0,32]] = np.float32(5.25); rows[1:, [1,33]] = np.float32(2.625)
q = np.ones(D, np.float32); p = np.full(T, .5, np.float32)
memory = {Q+i: int(x.view(np.uint32)) for i,x in enumerate(q)}
memory.update({P+i:int(x.view(np.uint32)) for i,x in enumerate(p)})
for row in range(T):
    g = fp8group if row == 0 else group
    raw = g | (g << 265)
    base = 4194304 if row == 0 else (row-1)*stride
    for i in range(stride//4): memory[base//4+i] = (raw >> (32*i)) & 0xffffffff
def record(op, abase, an, obase, on):
    ds = [C.SV.mdesc(space=1,base=abase,n=an,m=1,stride=an),
          C.SV.mdesc(space=0,fmt=3,base=4194304,n=1,m=1,stride=stride),
          C.SV.mdesc(space=0,fmt=3,base=0,n=T-1,m=1,stride=stride),0,
          C.SV.mdesc(space=1,base=obase,n=on,m=1,stride=on),0,0]
    return pack(dict(hdr=C.SV.header(5,op,opnd=0b10111,param=1),eff=ds,n=[an,1,T-1,0,on,0,0],pos1=T))
records=[record(0,Q,D,SCORE,T),record(1,P,T,O,D)]
expected={SCORE+i:int(x.view(np.uint32)) for i,x in enumerate(A.att_qk(q,rows))}
expected.update({O+i:int(x.view(np.uint32)) for i,x in enumerate(A.att_pv(p,rows))})
for name, values, bits in [('rec',records,1216),('mem',[(a<<32)|v for a,v in sorted(memory.items())],64),('exp',[(a<<32)|v for a,v in sorted(expected.items())],64)]:
    (out/f'{name}.mem').write_text(''.join(C.hexw(v,bits)+'\n' for v in values))
(out/'sizes.svh').write_text(f'localparam NM={len(memory)}, NE={len(expected)};\n')
