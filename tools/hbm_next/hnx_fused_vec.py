#!/usr/bin/env python3
"""HBM-NEXT-UNITS-FUSED (2026-10-19): bench vectors for ot_hnx_fused_top (tb_hnx_fused), one N-row record a case.

    hnx_fused_vec.py --op pre|post --n N [--rgap G] [--seed S] --out DIR

Golden = tools/hdc_golden_v41 under R-ARITH chunk8 (the order the LL engine and this engine implement):
  HC_PRE_NORM row p: x = bf16(seqsum_j pre_p[j] h_p[j]); y = rmsnorm_bf16(x, w, eps)  (gain w shared by all rows)
  HC_POST     row p: out_p[k] = bf16(post_p[k] y_p + seqsum_j comb_p[j, k] res_p[j]),  k = 0..3
Writes DIR/{vmi.mem, vme.mem, job.mem, plus.txt, case.json}: vmi / vme lines = {word address 20 b, value 32 b} hex;
job.mem = the 217-b job word (see ot_hnx_fused_top); plus.txt = the plusargs of the run.
Layout (VM FP32 words, every operand at bank phase 0, row strides multiples of 256 words; C sector aligned):
  PRE  A h  0 + p 20,480 | B gain 131,072 (broadcast, rs_B 0) | C pre 196,608 + 8 p | O y 163,840 + 5,120 p
  POST A y  0 + p 5,120  | B res 32,768 + p 20,480            | C 327,680 + 24 p   | O 196,608 + p 20,480
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as GV  # noqa: E402

GV.set_arith("chunk8")
D = 5120


def f32w(x):
    return np.asarray(x, dtype=np.float32).view(np.uint32)


def job_word(post, nm1, a, b, c, o, rsa, rsb, rsc, rso, rgap, eps):
    m24 = (1 << 24) - 1
    w = post | nm1 << 1 | a << 5 | b << 24 | c << 43 | o << 62
    w |= (rsa & m24) << 81 | (rsb & m24) << 105 | (rsc & m24) << 129 | (rso & m24) << 153
    w |= rgap << 177 | int(np.float32(eps).view(np.uint32)) << 185
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--op", choices=("pre", "post"), required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--rgap", type=int, default=0)
    ap.add_argument("--seed", type=int, default=19)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    assert 1 <= a.n <= 8 and 0 <= a.rgap <= 255, "N 1..8 (NMAX), rgap is an 8-b field"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed + 100 * a.n + (0 if a.op == "pre" else 7))
    n = a.n
    vin, vout = {}, {}
    eps = np.float32(1e-6)
    if a.op == "pre":
        A, B, C, O = 0, 131072, 196608, 163840
        rsa, rsb, rsc, rso = 4 * D, 0, 8, D
        assert A + n * rsa <= B and O + n * rso <= C
        w = GV.to_bf16((1 + 0.1 * rng.standard_normal(D)).astype(np.float32))
        vin.update({B + i: int(v) for i, v in enumerate(f32w(w))})
        for p in range(n):
            h = (rng.standard_normal((4, D)) * 2).astype(np.float32)
            pre = (rng.random(4) * 1.5).astype(np.float32)
            x = GV.to_bf16(GV.seqsum([GV.mul(pre[j], h[j]) for j in range(4)]))
            y = GV.rmsnorm_bf16(x, w, eps)
            vin.update({A + p * rsa + i: int(v) for i, v in enumerate(f32w(h.reshape(-1)))})
            vin.update({C + p * rsc + j: int(v) for j, v in enumerate(f32w(pre))})
            vout.update({O + p * rso + i: int(v) for i, v in enumerate(f32w(y))})
        job = job_word(0, n - 1, A, B, C, O, rsa, rsb, rsc, rso, a.rgap, eps)
    else:
        A, B, C, O = 0, 32768, 327680, 196608
        rsa, rsb, rsc, rso = D, 4 * D, 24, 4 * D
        assert A + n * rsa <= B and B + n * rsb <= O and O + n * rso <= C and C + n * rsc < (1 << 19)
        for p in range(n):
            yv = (rng.standard_normal(D) * 2).astype(np.float32)
            res = (rng.standard_normal((4, D)) * 2).astype(np.float32)
            post = (rng.random(4) * 2).astype(np.float32)
            comb = (rng.random((4, 4)) * 0.5).astype(np.float32)
            mix = [GV.seqsum([GV.mul(comb[j, k], res[j]) for j in range(4)]) for k in range(4)]
            hout = GV.to_bf16(np.stack([GV.add(GV.mul(post[k], yv), mix[k]) for k in range(4)]))
            vin.update({A + p * rsa + i: int(v) for i, v in enumerate(f32w(yv))})
            vin.update({B + p * rsb + i: int(v) for i, v in enumerate(f32w(res.reshape(-1)))})
            sc = np.concatenate([post, comb.reshape(-1)])          # word 4 + 4 j + k = comb[j, k]
            vin.update({C + p * rsc + j: int(v) for j, v in enumerate(f32w(sc))})
            vout.update({O + p * rso + i: int(v) for i, v in enumerate(f32w(hout.reshape(-1)))})
        job = job_word(1, n - 1, A, B, C, O, rsa, rsb, rsc, rso, a.rgap, eps)
    (out / "vmi.mem").write_text("".join(f"{k:05X}{v:08X}\n" for k, v in sorted(vin.items())))
    (out / "vme.mem").write_text("".join(f"{k:05X}{v:08X}\n" for k, v in sorted(vout.items())))
    (out / "job.mem").write_text(f"{job:055X}\n")
    (out / "plus.txt").write_text(f"+NVMI={len(vin)} +NVME={len(vout)} +OP={a.op} +N={n} +RGAP={a.rgap}\n")
    (out / "case.json").write_text(json.dumps(dict(op=a.op, n=n, rgap=a.rgap, seed=a.seed, nvmi=len(vin),
                                                    nvme=len(vout), job=f"{job:055X}"), indent=1) + "\n")
    print(f"{a.op} N={n} rgap={a.rgap}: vmi {len(vin)} vme {len(vout)}")


if __name__ == "__main__":
    main()
