#!/usr/bin/env python3
"""Verify the exact real-RTL NL banked oracle / negative controls before physical job adoption (r13 NL helper)."""
from pathlib import Path
import json,hashlib,random
root=Path(__file__).resolve().parents[2];b=root/'results/rtl/qwen_compute_native_glue_1014/parent_nl_banked_v1'
h=json.loads((b/'source_hashes.json').read_text());r=random.Random(198);mh={}
for bank in range(5):
 for col in range(2):mh[f'masks/qtile_t0_b{bank}_c{col}.viamap.hex']=hashlib.sha256(''.join(f'{r.getrandbits(2128):0532x}\n'for _ in range(512)).encode()).hexdigest()
for p,want in h.items():
 got=mh[p] if p.startswith('masks/') else hashlib.sha256((root/p).read_bytes()).hexdigest()
 assert got==want,('NL parent source/mask changed',p)
L=lambda n:(b/n).read_text()
assert 'PASS actual full old-NL staged-reference vs53bank TX198 ALLB0 FAULT0 checks3499' in L('run_m0_a0_f0.log')
assert 'ACTUAL_BANK_READS 64 120 96 104 64' in L('run_m0_a1_f0.log') and 'ALLB1 FAULT0 checks5959' in L('run_m0_a1_f0.log')
assert 'ALLB0 FAULT1 checks3499' in L('run_m0_a0_f1.log') and 'ALLB1 FAULT1 checks5959' in L('run_m0_a1_f1.log')
for m in range(1,5):assert 'FAIL parent' in L(f'run_m{m}_a0_f0.log'),('negative control missing',m)
print('PASS exact real NL parent numerical receipt: source/mask hashes, 3499+5959 words (no-fault and split-fault), 4 mutants FAIL; physical qualification OPEN')
