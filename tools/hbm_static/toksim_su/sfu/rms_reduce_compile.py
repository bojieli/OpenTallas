#!/usr/bin/env python3
"""TOKSIM-HBM-su 10-19: Qwen FUSED.ROW_NORM sum-of-squares on the SU quarter reducer ot_hbm_su_reduce_static (the reducer
inside the die-bound ot_hbm_su_static_qcore), compiled exactly as tools/hbm_static/su_reduce_compile.Program does (LAT 9,
RAW distance 10, eight-chunk sample-major csum8 + pairwise tree, one operand per edge) -- sum pass only (RMSNorm has no
max pass).  Golden = hgi_sim lib.row_norm's s = csum(mul(x, x)) (hdc_golden_v41.csum), fed with real FP32 squares.
Cases (one command stream each, cycles printed per row):
  d4096: quarter 0's 128 csum8 chunks of a 4096-wide row (1024 squares) -> quarter root; then the cross-quarter combine
         ((q0 + q1) + (q2 + q3)) on reducer 0 with the other quarters' roots as operands (they arrive through the RF / stree
         network on the die; that transport is NOT in this bench) -> total, checked = csum of all 4096 squares.
  seg128_q2: two 128-wide heads on one quarter (q_norm: 8 heads over 4 quarters); seg128_k1: one 128-wide head (k_norm).
usage: rms_reduce_compile.py OUT CASE
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2])); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import su_reduce_compile as R          # noqa: E402  (Program, LAT, bits)
from hdc_golden_v41 import csum        # noqa: E402

def squares(n, rng):
    x = (rng.integers(-4096, 4097, n).astype(np.float32) * np.exp2(rng.integers(-14, 6, n)).astype(np.float32))
    return (x.astype(np.float32) * x.astype(np.float32)).astype(np.float32)      # FP32 RNE products (lane mul)

def sum_rows(p, v, tag):
    """one csum row: LOAD 0 into the padded chunks, sample-major ADD_EXT, pairwise ADD_TREE, EXPORT."""
    start = p.c; n = len(v); nc = (n+7)//8; npad = 1 << (nc-1).bit_length()
    for k in range(npad): p.emit(0, d=k)
    for off in range(8):
        for ch in range(nc):
            k = ch*8+off
            p.emit(1, a=ch, d=ch, x=R.bits(v[k]) if k < n else 0)
    s = 1
    while s < npad:
        for k in range(0, npad, s*2): p.emit(2, a=k, b=k+s, d=k)
        s *= 2
    p.export(0, tag, R.bits(csum(v)))
    p.rows.append(dict(n=n, tag=tag, first_cmd=start, export_cmd=p.commands[-1][0], scalar_cycle=p.commands[-1][0]+R.LAT,
                       span=p.commands[-1][0]+R.LAT-start+1))

def main():
    out, case = Path(sys.argv[1]), sys.argv[2]
    rng = np.random.default_rng(1019); p = R.Program()
    if case == 'd4096':
        v = squares(4096, rng)
        q = [v[j*1024:(j+1)*1024] for j in range(4)]     # quarter j = csum8 chunks [128 j, 128 j + 128) (contiguous words)
        sum_rows(p, q[0], 1)
        roots = [R.bits(csum(x)) for x in q]
        assert roots[0] == p.outputs[-1][2]
        c0 = p.c
        p.emit(0, d=200, x=roots[0]); p.emit(1, a=200, d=200, x=roots[1])
        p.emit(0, d=201, x=roots[2]); p.emit(1, a=201, d=201, x=roots[3])
        p.emit(2, a=200, b=201, d=200)
        p.export(200, 2, R.bits(csum(v)))
        assert R.bits(csum(v)) == R.bits(np.float32(np.float32(csum(q[0])+csum(q[1])) + np.float32(csum(q[2])+csum(q[3]))))
        p.rows.append(dict(n=4, tag=2, combine=True, first_cmd=c0, export_cmd=p.commands[-1][0],
                           scalar_cycle=p.commands[-1][0]+R.LAT, span=p.commands[-1][0]+R.LAT-c0+1))
    elif case == 'seg128_q2':
        for h in range(2): sum_rows(p, squares(128, rng), h+1)
    elif case == 'seg128_k1':
        sum_rows(p, squares(128, rng), 1)
    else:
        raise SystemExit('case')
    p.write(out)
    print('RMS_REDUCE', case, json.dumps(p.rows))

if __name__ == '__main__':
    main()
