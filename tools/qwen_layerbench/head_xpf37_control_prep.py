#!/usr/bin/env python3
"""Emit actual native HEAD XPF fields with explicit TEST_ONLY component dates."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--gme',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--rank',type=int,choices=range(8),default=0);a=p.parse_args()
r=json.loads(a.gme.read_text())['ranks'][a.rank]
if r['xpf']['producer_pidx']!=17 or r['xpf']['stage']!=37:raise ValueError('actual native HEAD dedicated producer source required')
v=int(r['xpf']['fixed_low92_hex'],16)|(100<<92)|(129<<124)|(300<<156);pw=[0]*1024;pw[993]=(0x43414c42<<32)|(5<<24)|28
for n in range(3):pw[994+n]=(v>>(64*n))&((1<<64)-1)
pw[1003]=(0x58505447<<32)|400
(a.out/'input').mkdir(parents=True,exist_ok=True)
(a.out/'input/program.memh').write_text(''.join(f'{w:016x}\n'for w in pw));(a.out/'input/xpf72.memh').write_text(r['xpf']['xpf72_hex']+'\n')
(a.out/'fixture.json').write_text(json.dumps(dict(status='TEST_ONLY_COMPONENT',rank=a.rank,arm=100,producer_issue=129,first_write=300,stop=400,actual_matrix=False,physical_or_global_adoption=False),indent=2)+'\n')
