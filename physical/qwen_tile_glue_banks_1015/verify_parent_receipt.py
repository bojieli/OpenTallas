#!/usr/bin/env python3
"""Verify exact real-RTL oracle/negative controls before physical job adoption."""
from pathlib import Path
import json,hashlib,random,re
root=Path(__file__).resolve().parents[2];b=root/'results/rtl/qwen_compute_native_glue_1014/parent_banked_v1'
h=json.loads((b/'source_hashes.json').read_text());maskhash={};r=random.Random(198)
for bank in range(5):
 for col in range(2):maskhash[f'masks/qtile_t0_b{bank}_c{col}.viamap.hex']=hashlib.sha256(''.join(f'{r.getrandbits(2128):0532x}\n'for _ in range(512)).encode()).hexdigest()
for p,want in h.items():
 got=maskhash[p]if p.startswith('masks/')else hashlib.sha256((root/p).read_bytes()).hexdigest()
 assert got==want,('actual parent source/mask changed',p)
assert 'PASS actual full old-parent' in (b/'run_m0.log').read_text()
for mut in range(1,4):
 assert 'FAIL parent tile complete word' in (b/f'run_m{mut}.log').read_text(),('negative control missing',mut)
 assert 'Verilator: Built from' in (b/f'build_m{mut}.log').read_text()
assert 'ACTUAL_BANK_READS 64 120 96 104 64' in (b/'run_allbanks.log').read_text()
assert 'checks5959 output448 node745 nonzero448' in (b/'run_allbanks.log').read_text()
print('PASS exact real-parent numerical receipt44 source/mask hashes,3499wholewords/3mutants/5959all5bank+boot16checks; physicalqualificationOPEN')
