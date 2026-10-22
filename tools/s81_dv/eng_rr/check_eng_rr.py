#!/usr/bin/env python3
"""S81-RTLGAP/RG-ENG: bit-exact check of tb_dsdv_eng_rr's XQ trains against hdc_golden_v41.
For every window: the lookup row beats (OB w col beat d264: [255:0] 32 E4M3 codes, [263:256] UE8M0 scale byte) are
decoded as decode_engram_rows (E4M3 x 2^(scale - 127) -> to_bf16) and quantised as linear_q's input (quant_fp8, 32-blocks);
x beat idx = 4 col + m holds blocks (beat 2m, 2m + 1).  Every XQ train (XQ dir w idx payload532 = {e1 10, q1 256, e0 10,
q0 256}) must match by value (E4M3 value of every code, signed exponent), exactly once per (dir, idx), both directions.
Usage: check_eng_rr.py <run.log> <repo root (tools/hdc_golden_v41.py)>   prints ENG_RR_PY PASS / FAIL"""
import sys, re
from collections import defaultdict
import numpy as np
sys.path.insert(0, sys.argv[2] + '/tools')
import hdc_golden_v41 as V
ob = defaultdict(dict); xq = defaultdict(list)
for ln in open(sys.argv[1]):
    m = re.match(r'OB (\d+) (\d+) (\d+) ([0-9a-f]+)', ln)
    if m: ob[int(m[1])][(int(m[2]), int(m[3]))] = int(m[4], 16); continue
    m = re.match(r'XQ (\d) (\d+) (\d+) ([0-9a-f]+)', ln)
    if m: xq[int(m[2])].append((int(m[1]), int(m[3]), int(m[4], 16)))
errs = 0; nchk = 0
def sx10(v): return v - 1024 if v & 512 else v
for w in sorted(ob):
    beats = ob[w]
    cols = sorted({c for c, _ in beats})
    exp = {}
    for c in cols:
        for mm in range(4):
            blk = []
            for k in (2 * mm, 2 * mm + 1):
                d = beats[(c, k)]
                codes = np.array([(d >> (8 * i)) & 255 for i in range(32)])
                sc = (d >> 256) & 255
                x = V.to_bf16((V.E4M3[codes] * np.exp2(sc - 127.0)).astype(V.F))
                q, e = V.quant_fp8(x)
                blk.append((q, int(e[0])))
            exp[4 * c + mm] = blk
    got = defaultdict(list)
    for d, idx, p in xq[w]: got[(d, idx)].append(p)
    for d in (0, 1):
        for idx, blk in exp.items():
            ps = got.get((d, idx), [])
            if len(ps) != 1:
                errs += 1; print(f'ENG_RR_PY w{w} dir{d} idx{idx}: {len(ps)} trains'); continue
            p = ps[0]
            for b, (q, e) in enumerate(blk):
                qc = np.array([(p >> (266 * b + 8 * i)) & 255 for i in range(32)])
                ee = sx10((p >> (266 * b + 256)) & 1023)
                if ee != e or not np.array_equal(V.E4M3[qc], q):
                    errs += 1
                    if errs <= 6: print(f'ENG_RR_PY w{w} dir{d} idx{idx} block{b}: e {ee}/{e} codes differ {int(np.sum(V.E4M3[qc] != q))}')
            nchk += 1
    extra = [k for k in got if k[1] not in exp]
    if extra: errs += 1; print(f'ENG_RR_PY w{w}: trains with unexpected idx {extra[:4]}')
print(f'ENG_RR_PY windows {len(ob)} checked {nchk} errs {errs}')
print('ENG_RR_PY PASS' if errs == 0 and nchk > 0 else 'ENG_RR_PY FAIL')
