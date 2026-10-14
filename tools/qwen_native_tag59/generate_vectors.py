#!/usr/bin/env python3
"""Repeat the pinned independent actual pair-fold fixture for mixed traffic."""
import argparse, hashlib, json, subprocess
from pathlib import Path
SOURCE='414c13ff1'
BASE='tools/qwen_native_collective/fixture/'
def read(name):
    return subprocess.check_output(['git','show',f'{SOURCE}:{BASE}{name}'],text=True)
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
ranks=[read(f'rank{i}.hex').strip().splitlines() for i in range(8)];expected=read('expected.hex').strip().splitlines()
assert all(len(r)==512 for r in ranks) and len(expected)==512
parts=[];sums=[]
for msg in range(16):
    for bench_die in range(8):parts.extend(ranks[4*(bench_die%2)+bench_die//2])
    sums.extend(expected)
for name,rows in [('part.hex',parts),('sum.hex',sums),('mode.hex',[str(int(msg%3==1)) for msg in range(16)])]:
    (a.output/name).write_text('\n'.join(rows)+'\n')
receipt={'fixture_commit':SOURCE,'messages':16,'words':512,'arithmetic':'((P0+P1)+P2)+P3; Pp=rank[p]+rank[p+4], actual binary32 golden','sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.glob('*.hex')}}
(a.output/'fixture_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
