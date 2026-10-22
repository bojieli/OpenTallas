#!/usr/bin/env python3
"""HBM-SUFIX (b) 10-19: Qwen FUSED.ROW_NORM sum of squares lowered onto the SU reducer PRE-TREE (HH-6 ot_hbm_su_red_pretree_s
x4 + ot_hbm_su_static_qcore_r5 PRETREE 1, closed as hbm_su_pretree_s_1018-p3-1dad69123) instead of the as-built one-operand-
per-edge ingress.  Stimulus for rtl/test/hbm_accel/generic/tb_hbm_su_red_pretree.sv (one quarter), lowering =
tools/hbm_static/su_pretree_lower.Schedule (golden csum8 + aligned pairwise tree; asserted == hdc_golden_v41.csum).
Operands are real FP32 RNE squares mul(x, x) (hdc_golden.mul) of mixed-exponent x.
Cases (one quarter each; span = first tree_cmd edge -> scalar edge (EXPORT + SCL 11), serial-clock edges):
  d4096_q8   quarter-contiguous layout: the quarter's 1024 words (8 blocks) of a 4096 row -> its quarter root (an aligned
             node of the golden tree); the 4-root combine runs on reducer 0 after RF transit (composed, not here)
  d4096_q32  whole 4096 row in ONE quarter (32 blocks) -> row total, no cross-quarter join
  seg128_q2  q_norm: 8 heads x 128 over 4 quarters = 2 heads (2 independent blocks) per quarter, emitted on edges t, t+1
  seg128_k1  k_norm: 1 head (1 block) per quarter
usage: rownorm_pt_bench.py OUT CASE
"""
import json, sys
from pathlib import Path
import numpy as np
HB = Path(__file__).resolve().parents[2]          # tools/hbm_static
sys.path.insert(0, str(HB)); sys.path.insert(0, str(HB.parent))
import su_pretree_lower as L   # noqa: E402
from hdc_golden import mul      # noqa: E402

def squares(rng, n):
    # full-mantissa x of comparable magnitude (|x| ~ 2^-2..2^2): every add of the chunk chains and of the tree rounds, so
    # an order mutant (chunk x1<->x2, join pairing) changes the result instead of being absorbed by a few huge squares
    x = (rng.standard_normal(n).astype(np.float32) * np.exp2(rng.integers(-2, 3, n)).astype(np.float32)).astype(np.float32)
    return np.asarray(mul(x, x), dtype=np.float32).view(np.uint32)

def main():
    out, case = Path(sys.argv[1]), sys.argv[2]; out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(10191)
    S = L.Schedule(); t0 = 10; rows = []
    if case == 'd4096_q8':
        rows.append((S.lower('sum', squares(rng, 1024), 0x301, t0), 1024))
    elif case == 'd4096_q32':
        rows.append((S.lower('sum', squares(rng, 4096), 0x302, t0), 4096))
    elif case == 'seg128_q2':
        S.lower('sum', squares(rng, 128), 0x303, t0); S.lower('sum', squares(rng, 128), 0x304, t0 + 1)
    elif case == 'seg128_k1':
        S.lower('sum', squares(rng, 128), 0x305, t0)
    else:
        raise SystemExit('case')
    ne = max(max(S.red), max(S.tree)) + 40
    W = 48 + 74 + 128 + 4096
    with open(out / 'stim.mem', 'w') as f:
        for e in range(ne):
            v = 0
            if e in S.tree:
                mx, cnt, blk = S.tree[e]
                xs = [int(x) for x in blk] + [int(x) for x in rng.integers(0, 1 << 32, L.BLOCK - len(blk), dtype=np.uint64)]
                v |= L.tree_cmd_word(mx, cnt) << (W - 48)
                v |= ((1 << 128) - 1) << 4096
                for w, x in enumerate(xs): v |= (x & 0xffffffff) << (32 * w)
            else:
                for w in range(L.BLOCK): v |= int(rng.integers(0, 1 << 32, dtype=np.uint64)) << (32 * w)
            if e in S.red: v |= L.red_cmd_word(S.red[e]) << (4096 + 128)
            f.write(f'{v:0{W // 4}x}\n')
    with open(out / 'exps.mem', 'w') as f:
        for e, tag, val in S.exps: f.write(f'{e:08x}{tag:08x}{val:08x}\n')
    (out / 'plusargs.txt').write_text(f'+NE={ne} +NEXP={len(S.exps)}\n')
    first = min(S.tree); last_sc = max(e for e, _, _ in S.exps) + 11
    man = dict(case=case, blocks=len(S.tree), reducer_ops=len(S.red), first_tree_edge=first,
               exports=[dict(edge=e, scalar_edge=e + 11, tag=tag, value=f'{val:08x}') for e, tag, val in S.exps],
               span_serial=last_sc - first + 1, PT_RED=L.PT_RED, DEP=L.DEP)
    (out / 'case.json').write_text(json.dumps(man, indent=1) + '\n')
    print('ROWNORM_PT', json.dumps(man))

if __name__ == '__main__':
    main()
