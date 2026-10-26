#!/usr/bin/env python3
"""HBM-COLLQ/X (10-18): vectors for tb_hgi_xload_preq (x-load PRE-QUANTISED mode, fmt 3, vs FP8 fmt 1).

For each case: P FP32 vectors of K elements -> image A (FP32, fmt 1: element address baseA + p strideA + i) and image B
(PRE-QUANTISED VM FORMAT v1 from hdc_golden_v41.quant_fp8: S segments of Bs blocks, record at word wB + p strideB/8 +
s ss: Bs code words then Es exponent words, byte = e + 127).  Writes <out>/case<i>.memh (65,536 32-bit lanes: A at
[0,32768), B at [32768,65536)) and <out>/cases.txt (one line per case: K P Bs ss baseA strideA baseB strideB xb kind).

    PYTHONPATH=tools python3 tools/hgi_sim/xload_preq_vectors_1018.py OUT
"""
import sys, os
import numpy as np
import hdc_golden_v41 as G
from hdc_golden import F, to_bf16

CASES = [  # K, P, Bs, ss, kind
    (2304, 1, 18, 24, 0), (2304, 2, 18, 24, 1), (1024, 3, 8, 16, 2), (1024, 1, 8, 16, 3),
    (6144, 2, 48, 56, 4), (6144, 1, 48, 56, 5), (512, 4, 16, 24, 0), (2304, 1, 18, 24, 6),
]


def vec(n, rng, k):
    if k == 0:
        x = rng.standard_normal(n)
    elif k == 1:
        x = rng.standard_t(1.5, n) * 10.0 ** rng.integers(-6, 4)
    elif k == 2:
        x = np.zeros(n); x[rng.integers(0, n, 7)] = rng.standard_normal(7) * 1e-6      # amax-floor blocks
        x[: n // 2] += rng.standard_normal(n // 2) * 1e-7
    elif k == 3:
        x = rng.standard_normal(n) * 3e4
    elif k == 4:
        x = to_bf16(rng.standard_normal(n).astype(F))
    elif k == 5:
        e = rng.integers(-8, 8, n)
        x = np.ldexp(1.0 + (rng.integers(0, 16, n) * 2 + 1) / 32.0, e) * rng.choice([-1, 1], n)
    else:
        x = rng.standard_normal(n); x[rng.integers(0, n, n // 4)] = 0.0; x[: 64] = -1e-30  # zeros + tiny negatives
    return np.asarray(x, dtype=F)


def e4m3_byte(q):
    lut = {}
    for c in range(256):
        v = G.E4M3[c]
        if np.isnan(v) or v == 0:
            continue
        lut[float(v)] = c
    out = np.zeros(q.shape, dtype=np.uint32)
    for i, v in enumerate(q):
        if v == 0:
            out[i] = 0x80 if np.signbit(v) else 0
        else:
            out[i] = lut[float(v)]
    return out


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(20261018)
    lines = []
    for ci, (K, P, Bs, ss, kind) in enumerate(CASES):
        nb = K // 32
        S = -(-nb // Bs)
        Es = -(-Bs // 32)
        assert S <= 4 and Bs % 2 == 0 and P * S * Es <= 16
        stA = 8 * (-(-K // 8) + int(rng.integers(0, 3)))
        baseA = 8 * int(rng.integers(0, 20))
        stB = 8 * (S * ss + 8 * int(rng.integers(0, 2)))
        baseB = 8 * (8 * int(rng.integers(0, 8)))
        assert baseA + P * stA <= 32768 and baseB + P * stB <= 32768
        mem = np.zeros(65536, dtype=np.uint32)
        for p in range(P):
            x = vec(K, rng, kind)
            mem[baseA + p * stA: baseA + p * stA + K] = x.view(np.uint32)
            q, e = G.quant_fp8(x)
            codes = e4m3_byte(np.asarray(q, dtype=np.float64)).reshape(nb, 32)
            e = np.asarray(e, dtype=np.int64)
            assert e.min() >= -22 and e.max() <= 120
            for s in range(S):
                rec = (baseB + p * stB) // 8 + s * ss                     # word address
                for r in range(min(Bs, nb - s * Bs)):
                    b = s * Bs + r
                    w = codes[b]
                    lanes = [int(w[4 * l]) | int(w[4 * l + 1]) << 8 | int(w[4 * l + 2]) << 16 | int(w[4 * l + 3]) << 24 for l in range(8)]
                    mem[32768 + 8 * (rec + r): 32768 + 8 * (rec + r) + 8] = lanes
                for g in range(Es):
                    by = [0] * 32
                    for kk in range(32):
                        r = 32 * g + kk
                        if r < Bs and s * Bs + r < nb:
                            by[kk] = int(e[s * Bs + r]) + 127
                    lanes = [by[4 * l] | by[4 * l + 1] << 8 | by[4 * l + 2] << 16 | by[4 * l + 3] << 24 for l in range(8)]
                    mem[32768 + 8 * (rec + Bs + g): 32768 + 8 * (rec + Bs + g) + 8] = lanes
        with open(f"{out}/case{ci}.memh", "w") as f:
            f.write("\n".join(f"{v:08x}" for v in mem) + "\n")
        xb = int(rng.integers(0, 128))
        lines.append(f"{K} {P} {Bs} {ss} {baseA} {stA} {baseB} {stB} {xb} {kind}")
    with open(f"{out}/cases.txt", "w") as f:
        f.write(f"{len(lines)}\n" + "\n".join(lines) + "\n")
    print(f"XLOAD_PREQ_VECTORS {len(lines)} cases -> {out}")


if __name__ == "__main__":
    main()
