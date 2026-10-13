#!/usr/bin/env python3
"""Build RAW dependency vectors from the immutable production record0 golden.

Bench DEPENDENCY=1 omits preload of record1, whose A is record0's O. The second
expected result is independently quantized from that golden O, so prematurely
reading A is observable as a numerical mismatch.
"""
import argparse
import shutil
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as G

p=argparse.ArgumentParser()
p.add_argument('production',type=Path)
p.add_argument('out',type=Path)
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
row=a.production.joinpath('recs.txt').read_text().splitlines()[1].split()
op,n,ab,ob,cost,block=map(int,row)
assert op==4 and n==512
for kind in ('in','out'):
 shutil.copyfile(a.production/f'{kind}_0.hex',a.out/f'{kind}_0.hex')
lines=a.production.joinpath('out_0.hex').read_text().splitlines()[:16]
x=np.array([int(line[i:i+8],16) for line in lines for i in range(56,-1,-8)],dtype=np.uint32)
y=G.bits(G.qdq_fp4_e8m0(x.view(np.float32).copy(),block=32)).astype(np.uint32)
a.out.joinpath('in_1.hex').write_text(''.join(line+'\n' for line in lines))
a.out.joinpath('out_1.hex').write_text(''.join(''.join(f'{int(w):08x}' for w in reversed(y[s:s+8]))+'\n' for s in range(0,128,8)))
a.out.joinpath('recs.txt').write_text(f'2\n{op} {n} {ab} {ob} {cost} {block}\n5 128 {ob} 150000 12 32\n')
print('PASS dependency vectors: rec1 A=rec0 O, rec1 preload omitted by DEPENDENCY=1')
