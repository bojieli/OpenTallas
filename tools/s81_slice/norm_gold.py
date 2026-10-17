#!/usr/bin/env python3
"""S81-SLICE norm golden for the beat-leaf benches (DS1M golden row, results/rtl/hbm_norm_engine_view_20261006/gold).

Writes into OUT: bp.mem (80 beat partials = csum subtrees of 64 elements of the mixed x squared), rstd.mem (the golden
rstd), and checks that hdc_golden_v41.rmsnorm_bf16 reproduces ey.mem (so the beat partials come from the same mixed x).

    python3 tools/s81_slice/norm_gold.py OUT
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as V

F = np.float32
G = Path(__file__).resolve().parents[2] / "results/rtl/hbm_norm_engine_view_20261006/gold"


def rd(name):
    return np.array([int(l, 16) for l in open(G / name) if l.strip()], dtype=np.uint32)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    V.set_arith("chunk8")
    D = 5120
    h = rd("x.mem").view(F).reshape(4, D)
    w = rd("w.mem").view(F)
    cfg = rd("cfg.mem")
    pre = cfg[:4].view(F); eps = cfg[5:6].view(F)[0]
    assert cfg[4].view(F) == F(D)
    x = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(4)]))
    y = V.rmsnorm_bf16(x, w, eps)
    ey = rd("ey.mem")
    assert np.array_equal(y.view(np.uint32), ey), "golden rmsnorm does not reproduce ey.mem"
    sq = V.mul(x, x)
    bp = np.array([V.csum(sq[64 * b:64 * b + 64]) for b in range(D // 64)], dtype=F)
    tot = V.csum(sq)
    # the beat partials are aligned subtrees: the golden total is their pairwise tree (80 -> padded 128)
    acc = list(bp) + [F(0)] * (128 - len(bp))
    while len(acc) > 1:
        acc = [V.add(acc[i], acc[i + 1]) for i in range(0, len(acc), 2)]
    assert acc[0].view(np.uint32) == F(tot).view(np.uint32), "beat partials are not subtrees of the golden csum"
    r = V.rsqrt(V.add(V.div(F(tot), F(D)), F(eps)))
    np.savetxt(out / "bp.mem", bp.view(np.uint32), fmt="%08x")
    open(out / "rstd.mem", "w").write("%08x\n" % F(r).view(np.uint32))
    print("NORM_GOLD beats=%d total=%08x rstd=%08x" % (len(bp), F(tot).view(np.uint32), F(r).view(np.uint32)))


if __name__ == "__main__":
    main()
